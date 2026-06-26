from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uuid
from .services.queue_publisher import publish_job

app = FastAPI(
    title="Persian Finance API Gateway",
    description="Ingests receipts and routes them to the ML pipeline.",
    version="1.0.0"
)

@app.post("/api/v1/process-receipt")
async def process_receipt(
    file: UploadFile = File(...),
    user_prompt: str = Form(...)
):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG or PNG images are allowed.")

    job_id = str(uuid.uuid4())

    image_bytes = await file.read()

    publish_job(job_id, image_bytes, user_prompt, file.filename)

    return JSONResponse(
        status_code=202,
        content={
            "message": "Receipt accepted and queued for processing.",
            "job_id": job_id,
            "filename": file.filename,
            "prompt_received": user_prompt
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}