import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def publish_job(job_id: str, object_name: str, user_prompt: str, filename: str):
    payload = {
        "job_id": job_id,
        "filename": filename,
        "user_prompt": user_prompt,
        "object_name": object_name, 
        "status": "QUEUED"
    }
    
    redis_client.lpush("ocr_task_queue", json.dumps(payload))
    print(f"✅ Published Job {job_id} to Redis (Claim Check: {object_name})")
    return True