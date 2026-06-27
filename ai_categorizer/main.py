import pika
import json
import time
from supabase_client import SupabaseClient
from agent_brain import AgentBrain
from config import settings

QUEUE_NAME = "llm_task_queue"
RESULTS_QUEUE = "results_queue"

db_client = SupabaseClient()
brain = AgentBrain(db_client)

def process_agent_workflow(ch, method, properties, body):
    payload = json.loads(body)
    job_id = payload.get("job_id")
    extracted_text = payload.get("extracted_text")
    user_prompt = payload.get("user_prompt")
    
    print(f"\n⚡ [AGENT ENGINE] Ingesting Job: {job_id}")
    time.sleep(5)

    metadata = brain.extract_receipt_metadata(extracted_text)
    
    if not metadata or not metadata.get("amount"):
        print("❌ [ABORTED] Phi-3:mini failed to safely isolate financial fields from raw text.")
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

    print(f"🔍 Extracted Data -> Merchant: {merchant} | Amount: {amount} | Date: {date}")

    user_cat = None
    if "groceries" in user_prompt.lower(): user_cat = "Groceries"
    elif "transport" in user_prompt.lower(): user_cat = "Transport"

    final_category = brain.infer_category_or_abort(merchant, user_cat, implied_cat)
    
    if final_category is None:
        print(f"❌ [ABORTED] Categorization remains completely ambiguous for '{merchant}'. Blocking record insertion.")
        ch.basic_publish(
            exchange='',
            routing_key=RESULTS_QUEUE,
            body=json.dumps({"job_id": job_id, "status": "failed", "error": "Categorization ambiguous"})
        )
    else:
        db_client.add_expense(job_id, date, merchant, amount, final_category)
        
        answer = None
        if any(keyword in user_prompt.lower() for keyword in ["how much", "spent", "total", "calculate"]):
            print("📊 Running transactional dynamic lookup query...")
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

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_services():
    connection = pika.BlockingConnection(pika.ConnectionParameters(settings.rabbitmq_host))
    channel = connection.channel()
    
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_declare(queue=RESULTS_QUEUE, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_agent_workflow)
    
    print(f"🎧 AI Agent Online. Monitoring queue: '{QUEUE_NAME}'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_services()