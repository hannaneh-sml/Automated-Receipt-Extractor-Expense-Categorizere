import redis
import json
import base64

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def publish_job(job_id: str, image_bytes: bytes, user_prompt: str, filename: str):
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "job_id": job_id,
        "filename": filename,
        "user_prompt": user_prompt,
        "image_data": image_b64,
        "status": "QUEUED"
    }
    
    redis_client.lpush("ocr_task_queue", json.dumps(payload))
    
    print(f"✅ Successfully published Job {job_id} to Redis queue 'ocr_task_queue'")
    return True