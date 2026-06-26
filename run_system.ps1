# Ensure Docker Infra is spinning smoothly
Write-Host "🚀 Spawning Docker Infrastructure..." -ForegroundColor Cyan
docker-compose up -d

# Verify Ollama Background App is Awake
Write-Host "🧠 Checking local AI Model Engine..." -ForegroundColor Cyan
Start-Process "ollama" -ArgumentList "run phi3" -WindowStyle Minimized

# Wait for infrastructure dependencies to fully settle
Start-Sleep -Seconds 5

# Start Microservices into native background running terminal sessions
Write-Host "📡 Launching Service A: Gateway API..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd gateway_service; .\venv\Scripts\activate; uvicorn main:app --reload --port 8000"

Write-Host "👁️ Launching Service B: OCR Compute Worker..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ocr_worker; .\venv\Scripts\activate; python main.py"

Write-Host "🧠 Launching Service C: AI Brain Agent..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ai_categorizer; .\venv\Scripts\activate; python main.py"

Write-Host "✅ Entire microservice ecosystem initialized successfully!" -ForegroundColor Magenta