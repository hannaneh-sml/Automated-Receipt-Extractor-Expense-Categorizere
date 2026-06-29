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
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

resource = Resource(attributes={"service.name": "gateway_service"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

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

app = FastAPI(title="Receipt keeper API Gateway", lifespan=lifespan)

@app.post("/api/v1/process-receipt")
async def process_receipt(file: UploadFile = File(...), user_prompt: str = Form(...)):
    # Wrap the entire endpoint execution in a master span
    with tracer.start_as_current_span("Ingest_New_Receipt") as span:
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Only JPEG/PNG allowed.")

        job_id = str(uuid.uuid4())
        span.set_attribute("job.id", job_id)
        span.set_attribute("file.name", file.filename)
        
        image_bytes = await file.read()
        object_name = f"{job_id}_{file.filename}"
        
        # Isolate the MinIO network call latency
        with tracer.start_as_current_span("Upload_To_MinIO"):
            try:
                s3_client.put_object(Bucket='receipts', Key=object_name, Body=image_bytes)
                print(f"☁️ Uploaded {object_name} to MinIO Storage")
            except Exception as e:
                span.record_exception(e)
                raise HTTPException(status_code=500, detail=f"Storage Error: {str(e)}")

        live_jobs[job_id] = {"job_id": job_id, "status": "processing"}

        # Inject Trace Context for RabbitMQ
        headers = {}
        TraceContextTextMapPropagator().inject(carrier=headers)
        
        # Pass headers to your publisher (Requires update to publish_job function signature)
        publish_job(job_id, object_name, user_prompt, file.filename, headers=headers)
        span.add_event("Job published to queue")

        return JSONResponse(
            status_code=202,
            content={"message": "Receipt accepted.", "job_id": job_id}
        )

@app.get("/api/v1/status/{job_id}")
async def get_job_status(job_id: str):
    # Track status check frequency and latency
    with tracer.start_as_current_span("Check_Job_Status") as span:
        span.set_attribute("job.id", job_id)
        
        if job_id not in live_jobs:
            span.set_attribute("job.status", "not_found")
            raise HTTPException(status_code=404, detail="Job ID not found or expired.")
            
        current_status = live_jobs[job_id].get("status", "unknown")
        span.set_attribute("job.status", current_status)
        
        if current_status == "completed":
            print(f"✅ Status check: Job {job_id} is COMPLETED. Returning data.")
        elif current_status == "failed":
            print(f"❌ Status check: Job {job_id} FAILED. Returning error.")
        else:
            print(f"⏳ Status check: Job {job_id} is still {current_status.upper()}.")
            
        return live_jobs[job_id]