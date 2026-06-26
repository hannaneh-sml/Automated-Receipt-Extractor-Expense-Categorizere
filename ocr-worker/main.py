import pika
import json
import time
import easyocr
import boto3
import os
from dotenv import load_dotenv

QUEUE_NAME = "ocr_task_queue"
NEXT_QUEUE = "llm_task_queue"
load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

s3_client = boto3.client(
    's3',
    endpoint_url='MINIO_ENDPOINT',
    aws_access_key_id='admin',
    aws_secret_access_key='password123'
)

print("⏳ Initializing EasyOCR Engine...")
reader = easyocr.Reader(['fa', 'en']) 
print("✅ EasyOCR Engine Ready!")

def process_and_forward(ch, method, properties, body):
    payload = json.loads(body)
    job_id = payload.get("job_id")
    object_name = payload.get("object_name") 
    user_prompt = payload.get("user_prompt")
    
    print(f"\n⚙️ [WORKER] Processing Job: {job_id}")
    
    try:
        start_time = time.time()
        
        print(f"☁️ Downloading {object_name} from MinIO...")
        response = s3_client.get_object(Bucket='receipts', Key=object_name)
        image_bytes = response['Body'].read()
        
        print("🔍 Running OCR AI...")
        results = reader.readtext(image_bytes, detail=0)
        extracted_text = "\n".join(results)
        
        execution_time = round(time.time() - start_time, 2)
        print(f"✅ OCR Finished in {execution_time}s!")
        print(f"--- Extracted Text ---\n{extracted_text}\n----------------------")
        
        llm_payload = {
            "job_id": job_id,
            "extracted_text": extracted_text,
            "user_prompt": user_prompt
        }
        
        ch.queue_declare(queue=NEXT_QUEUE, durable=True)
        ch.basic_publish(
            exchange='',
            routing_key=NEXT_QUEUE,
            body=json.dumps(llm_payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        print(f"➡️ Successfully pushed data to '{NEXT_QUEUE}' for Service C!")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
    channel = connection.channel()
    
    # Ensure queue exists
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    
    channel.basic_qos(prefetch_count=1)
    
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_and_forward)
    
    print(f"🎧 RabbitMQ Worker started. Listening to '{QUEUE_NAME}'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_worker()