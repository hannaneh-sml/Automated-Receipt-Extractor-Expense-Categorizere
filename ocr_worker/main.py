import pika
import json
import time
import easyocr
import boto3
import sys
from config import settings

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import SpanKind

# 1. Initialize manual OpenTelemetry pipeline
resource = Resource(attributes={"service.name": "ocr_worker"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

sys.stdout.reconfigure(line_buffering=True)

QUEUE_NAME = "ocr_task_queue"
NEXT_QUEUE = "llm_task_queue"

s3_client = boto3.client(
    's3',
    endpoint_url=settings.minio_endpoint,
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key
)

print("⏳ Initializing EasyOCR Engine...")
reader = easyocr.Reader(['fa', 'en']) 
print("✅ EasyOCR Engine Ready!")

def process_and_forward(ch, method, properties, body):
    # 2. Extract parent trace context from incoming RabbitMQ headers
    headers = properties.headers or {}
    parent_context = TraceContextTextMapPropagator().extract(carrier=headers)
    
    # 3. Start a master workflow span linked to the Gateway's trace
    with tracer.start_as_current_span("OCR_Processing_Workflow", context=parent_context, kind=SpanKind.CONSUMER) as main_span:
        payload = json.loads(body)
        job_id = payload.get("job_id")
        object_name = payload.get("object_name") 
        user_prompt = payload.get("user_prompt")
        
        main_span.set_attribute("job.id", job_id)
        main_span.set_attribute("file.name", object_name)
        print(f"\n⚙️ [WORKER] Processing Job: {job_id}")
        
        try:
            start_time = time.time()
            
            # 4. Explicit sub-span for MinIO network latency
            with tracer.start_as_current_span("MinIO_Image_Download"):
                print(f"☁️ Downloading {object_name} from MinIO...")
                response = s3_client.get_object(Bucket='receipts', Key=object_name)
                image_bytes = response['Body'].read()
            
            # 5. Explicit sub-span for AI compute time
            with tracer.start_as_current_span("EasyOCR_Text_Extraction") as ocr_span:
                print("🔍 Running OCR AI...")
                results = reader.readtext(image_bytes, detail=0, workers=0)
                extracted_text = "\n".join(results)
                ocr_span.set_attribute("ocr.character_count", len(extracted_text))
            
            execution_time = round(time.time() - start_time, 2)
            print(f"✅ OCR Finished in {execution_time}s!")
            print(f"--- Extracted Text ---\n{extracted_text}\n----------------------")
            
            llm_payload = {
                "job_id": job_id,
                "extracted_text": extracted_text,
                "user_prompt": user_prompt
            }
            
            # 6. Inject updated context into new headers for the Categorizer
            next_headers = {}
            TraceContextTextMapPropagator().inject(carrier=next_headers)
            
            ch.queue_declare(queue=NEXT_QUEUE, durable=True)
            ch.basic_publish(
                exchange='',
                routing_key=NEXT_QUEUE,
                body=json.dumps(llm_payload),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers=next_headers  # Forwarding the trace ID!
                )
            )
            print(f"➡️ Successfully pushed data to '{NEXT_QUEUE}' for Service C!")
            main_span.set_attribute("workflow.status", "completed")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            main_span.record_exception(e)
            main_span.set_attribute("workflow.status", "failed")
            print(f"❌ Error during execution: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    print(f"DEBUG: Attempting to connect to RabbitMQ at {settings.rabbitmq_host}...")
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.rabbitmq_host))
        print("DEBUG: Connection established!")
        channel = connection.channel()
        
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_and_forward)
        
        print(f"🎧 RabbitMQ Worker started. Listening to '{QUEUE_NAME}'...")
        channel.start_consuming()
    except Exception as e:
        print(f"CRITICAL ERROR connecting to RabbitMQ: {e}")

if __name__ == "__main__":
    start_worker()