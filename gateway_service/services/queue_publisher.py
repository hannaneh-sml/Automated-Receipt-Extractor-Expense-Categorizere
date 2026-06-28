import pika
import json
from config import settings

def publish_job(job_id: str, object_name: str, user_prompt: str, filename: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=settings.rabbitmq_host))
    channel = connection.channel()

    channel.queue_declare(queue='ocr_task_queue', durable=True)

    payload = {
        "job_id": job_id,
        "filename": filename,
        "user_prompt": user_prompt,
        "object_name": object_name,
        "status": "QUEUED"
    }
    
    # 4. Publish the message
    channel.basic_publish(
        exchange='',
        routing_key='ocr_task_queue',
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=2,  
    ))
    
    print(f"✅ Published Job {job_id} to RabbitMQ (Claim Check: {object_name})")
    
    connection.close()
    return True