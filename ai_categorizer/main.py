import pika
import json
import time
import sys
from supabase_client import SupabaseClient
from agent_brain import AgentBrain
from config import settings

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import SpanKind

# Initialize manual OpenTelemetry pipeline
resource = Resource(attributes={"service.name": "ai_categorizer"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

sys.stdout.reconfigure(line_buffering=True)

QUEUE_NAME = "llm_task_queue"
RESULTS_QUEUE = "results_queue"

print("⏳ Initializing Database and AI Agent Brain...")
db_client = SupabaseClient()
brain = AgentBrain(db_client)
print("✅ Agent Brain Ready!")

def process_agent_workflow(ch, method, properties, body):
    # 1. Extract context from incoming RabbitMQ headers to maintain trace continuity
    headers = properties.headers or {}
    parent_context = TraceContextTextMapPropagator().extract(carrier=headers)
    
    # 2. Start a master workflow block tracking span
    with tracer.start_as_current_span("Categorize_Expense_Workflow", context=parent_context, kind=SpanKind.CONSUMER) as main_span:
        payload = json.loads(body)
        job_id = payload.get("job_id")
        extracted_text = payload.get("extracted_text")
        user_prompt = payload.get("user_prompt")
        
        main_span.set_attribute("job.id", job_id)
        print(f"\n⚡ [AGENT ENGINE] Ingesting Job: {job_id}")

        # 3. Explicit sub-span for the LLM receipt extraction step
        with tracer.start_as_current_span("LLM_Metadata_Extraction") as extract_span:
            metadata = brain.extract_receipt_metadata(extracted_text)
        
        if not metadata or not metadata.get("amount"):
            print("❌ [ABORTED] Model failed to safely isolate financial fields from raw text.")
            main_span.set_attribute("workflow.status", "failed_extraction")
            ch.basic_publish(
                exchange='',
                routing_key=RESULTS_QUEUE,
                body=json.dumps({"job_id": job_id, "status": "failed", "error": "Extraction failed"})
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        merchant = metadata.get("merchant", "Unknown Merchant")
        amount = float(metadata.get("amount"))
        date = metadata.get("date") or time.strftime("%Y-%m-%d")
        implied_cat = metadata.get("implied_category")

        main_span.set_attribute("receipt.merchant", merchant)
        main_span.set_attribute("receipt.amount", amount)

        print(f"🔍 Extracted Data -> Merchant: {merchant} | Amount: {amount} | Date: {date}")

        user_cat = None
        if user_prompt:
            if "groceries" in user_prompt.lower(): user_cat = "Groceries"
            elif "transport" in user_prompt.lower(): user_cat = "Transport"

        # 4. Explicit sub-span for the category context inference matching
        with tracer.start_as_current_span("LLM_Category_Inference"):
            final_category = brain.infer_category_or_abort(merchant, user_cat, implied_cat)
        
        if final_category is None:
            print(f"❌ [ABORTED] Categorization remains completely ambiguous for '{merchant}'. Blocking record insertion.")
            main_span.set_attribute("workflow.status", "failed_categorization")
            ch.basic_publish(
                exchange='',
                routing_key=RESULTS_QUEUE,
                body=json.dumps({"job_id": job_id, "status": "failed", "error": "Categorization ambiguous"})
            )
        else:
            main_span.set_attribute("receipt.category", final_category)
            print(f"💾 Saving to Supabase DB: {final_category}...")
            
            # 5. Explicit sub-span tracking Supabase DB insertion network footprint
            with tracer.start_as_current_span("Supabase_Insert_Operation"):
                db_client.add_expense(job_id, date, merchant, amount, final_category)
            
            answer = None
            if user_prompt and any(keyword in user_prompt.lower() for keyword in ["how much", "spent", "total", "calculate"]):
                print("📊 Running transactional dynamic lookup query...")
                # 6. Explicit sub-span tracking conversational analyzer tool queries
                with tracer.start_as_current_span("LLM_Financial_Analysis"):
                    answer = brain.answer_financial_question(user_prompt)
                print(f"\n💬 [AI Response]:\n{answer}\n")
                
            result_payload = {
                "job_id": job_id,
                "status": "completed",
                "data": {
                    "merchant": merchant,
                    "amount": amount,
                    "date": date,
                    "category": final_category,
                    "ai_answer": answer
                }
            }
            
            ch.basic_publish(
                exchange='',
                routing_key=RESULTS_QUEUE,
                body=json.dumps(result_payload)
            )
            print("➡️ Successfully pushed final results to Gateway!")
            main_span.set_attribute("workflow.status", "completed")

        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_services():
    print(f"DEBUG: Attempting to connect to RabbitMQ at {settings.rabbitmq_host}...")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.rabbitmq_host))
        print("DEBUG: Connection established!")
        channel = connection.channel()
        
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_declare(queue=RESULTS_QUEUE, durable=True)
        
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_agent_workflow)
        
        print(f"🎧 AI Agent Online. Monitoring queue: '{QUEUE_NAME}'...")
        channel.start_consuming()
    except Exception as e:
        print(f"CRITICAL ERROR connecting to RabbitMQ: {e}")

if __name__ == "__main__":
    start_services()