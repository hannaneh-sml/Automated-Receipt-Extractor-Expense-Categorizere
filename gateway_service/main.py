from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uuid
import boto3
import pika
import json
import threading
from services.queue_publisher import publish_job
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError
from config import settings

s3_client = boto3.client(
    's3',
    endpoint_url=settings.minio_endpoint,
    aws_access_key_id=settings.minio_access_key,
    aws_secret_access_key=settings.minio_secret_key
)

live_jobs = {}

def listen_for_results():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(settings.rabbitmq_host))
        channel = connection.channel()
        channel.queue_declare(queue='results_queue', durable=True)

        def callback(ch, method, properties, body):
            try:
                payload = json.loads(body)
                job_id = payload.get("job_id")
                if job_id:
                    live_jobs[job_id] = payload
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"❌ Error processing result message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(queue='results_queue', on_message_callback=callback)
        print("🎧 Gateway Result Thread Online. Monitoring 'results_queue'...")
        channel.start_consuming()
    except Exception as e:
        print(f"❌ RabbitMQ Listener crashed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        s3_client.head_bucket(Bucket='receipts')
        print("✅ MinIO Bucket 'receipts' found.")
    except ClientError:
        print("⚠️ Bucket 'receipts' not found. Creating it now...")
        s3_client.create_bucket(Bucket='receipts')
        print("🪣 Successfully created 'receipts' bucket!")

    result_thread = threading.Thread(target=listen_for_results, daemon=True)
    result_thread.start()
        
    yield 
    
    print("🛑 Gateway shutting down...")

app = FastAPI(title="Persian Finance API Gateway", lifespan=lifespan)

@app.post("/api/v1/process-receipt")
async def process_receipt(file: UploadFile = File(...), user_prompt: str = Form(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG/PNG allowed.")

    job_id = str(uuid.uuid4())
    image_bytes = await file.read()
    
    object_name = f"{job_id}_{file.filename}"
    
    try:
        s3_client.put_object(Bucket='receipts', Key=object_name, Body=image_bytes)
        print(f"☁️ Uploaded {object_name} to MinIO Storage")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage Error: {str(e)}")

    live_jobs[job_id] = {"job_id": job_id, "status": "processing"}

    publish_job(job_id, object_name, user_prompt, file.filename)

    return JSONResponse(
        status_code=202,
        content={"message": "Receipt accepted.", "job_id": job_id}
    )

@app.get("/api/v1/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in live_jobs:
        raise HTTPException(status_code=404, detail="Job ID not found or expired.")
        
    return live_jobs[job_id]