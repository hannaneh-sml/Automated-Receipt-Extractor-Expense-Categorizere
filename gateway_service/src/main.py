from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uuid
import boto3
from .services.queue_publisher import publish_job
from contextlib import asynccontextmanager
from botocore.exceptions import ClientError

app = FastAPI(title="Persian Finance API Gateway")

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:1986',
    aws_access_key_id='admin',
    aws_secret_access_key='password123'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        s3_client.head_bucket(Bucket='receipts')
        print("✅ MinIO Bucket 'receipts' found.")
    except ClientError:
        print("⚠️ Bucket 'receipts' not found. Creating it now...")
        s3_client.create_bucket(Bucket='receipts')
        print("🪣 Successfully created 'receipts' bucket!")
        
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

    publish_job(job_id, object_name, user_prompt, file.filename)

    return JSONResponse(
        status_code=202,
        content={"message": "Receipt accepted.", "job_id": job_id}
    )