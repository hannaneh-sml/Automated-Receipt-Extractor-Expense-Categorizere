import redis
import json
import time
import easyocr
import boto3

redis_client = redis.Redis(host='localhost', port=6379, db=0, 
                           decode_responses=True, health_check_interval=30)
QUEUE_NAME = "ocr_task_queue"

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='password123'
)

print("⏳ Initializing EasyOCR Engine...")
reader = easyocr.Reader(['fa', 'en']) 
print("✅ EasyOCR Engine Ready!")

def process_receipt(payload):
    job_id = payload.get("job_id")
    object_name = payload.get("object_name") 
    
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
        print(f"\n--- Extracted Text ---\n{extracted_text}\n----------------------")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")

def start_worker():
    print(f"🎧 OCR Worker started. Listening to Redis...")
    while True:
        try:
            result = redis_client.brpop(QUEUE_NAME, timeout = 5)
            if result:
                _, message = result
                payload = json.loads(message)
                process_receipt(payload)
        except Exception as e:
            print(f"⚠️ Worker Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()