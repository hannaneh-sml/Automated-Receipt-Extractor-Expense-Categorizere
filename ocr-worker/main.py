import redis
import json
import time

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
QUEUE_NAME = "ocr_task_queue"

def process_receipt(payload):
    #TBD with actual model
    job_id = payload.get("job_id")
    filename = payload.get("filename")
    
    print(f"\n⚙️ [WORKER] Processing Job: {job_id}")
    print(f"📄 Target File: {filename}")
    
    time.sleep(3) 
    
    mock_extracted_text = "فروشگاه افق کوروش - مبلغ: 150,000 تومان - تاریخ: 1402/08/15"
    print(f"🔍 [WORKER] OCR Extraction Complete: {mock_extracted_text}")
    print("-" * 50)

def start_worker():
    print(f"🎧 OCR Worker started. Listening to Redis queue '{QUEUE_NAME}'...")
    
    while True:
        try:
            result = redis_client.brpop(QUEUE_NAME, 0)
            
            if result:
                queue_name, message = result
                payload = json.loads(message)
                process_receipt(payload)
                
        except json.JSONDecodeError:
            print("❌ Failed to decode message payload.")
        except Exception as e:
            print(f"⚠️ Worker Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()