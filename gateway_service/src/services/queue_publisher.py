def publish_job(job_id: str, image_bytes: bytes, user_prompt: str, filename: str):
    
    print("="*50)
    print(f"✅ NEW JOB CREATED: {job_id}")
    print(f"📁 File: {filename} ({len(image_bytes)} bytes)")
    print(f"📝 User Prompt: '{user_prompt}'")
    print("🚀 Pushing to OCR Worker Queue...")
    print("="*50)
    #TBD
    return True