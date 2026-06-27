# Ensure Docker Infra is spinning smoothly
Write-Host "Spawning Docker Infrastructure..." -ForegroundColor Cyan
docker-compose up -d

# Verify Ollama Background App is Awake
Write-Host "Checking local AI Model Engine..." -ForegroundColor Cyan
$ollama = Start-Process "ollama" -ArgumentList "run phi3" -WindowStyle Minimized -PassThru

# Wait for infrastructure dependencies to fully settle
Start-Sleep -Seconds 10

# Start Microservices into native background running terminal sessions
Write-Host "Launching Service A: Gateway API..." -ForegroundColor Green
$gateway = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd gateway_service; .\venv\Scripts\activate; uvicorn main:app --reload --port 8000" -PassThru

Write-Host "Launching Service B: OCR Compute Worker..." -ForegroundColor Green
$ocr = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ocr_worker; .\venv\Scripts\activate; python main.py" -PassThru

Write-Host "Launching Service C: AI Brain Agent..." -ForegroundColor Green
$ai = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ai_categorizer; .\venv\Scripts\activate; python main.py" -PassThru

Write-Host "Entire microservice ecosystem initialized successfully!" -ForegroundColor Magenta

Write-Host "------------------------------------------------"
Write-Host "🛑 PRESS 'Q' TO SHUTDOWN ALL SYSTEM SERVICES 🛑" -ForegroundColor Yellow
Write-Host "------------------------------------------------"

# Listen for the Q key
while ($true) {
    if ([console]::KeyAvailable) {
        $key = [system.console]::ReadKey($true)
        if ($key.Key -eq 'Q') {
            break
        }
    }
    Start-Sleep -Milliseconds 100
}

Write-Host "`n🛑 Terminating process trees..." -ForegroundColor Red

# Kill the Python terminals and the minimized Ollama window
taskkill /PID $($gateway.Id) /T /F 2>$null
taskkill /PID $($ocr.Id) /T /F 2>$null
taskkill /PID $($ai.Id) /T /F 2>$null
taskkill /PID $($ollama.Id) /T /F 2>$null

Write-Host "Pausing Docker Infrastructure..." -ForegroundColor Cyan
docker-compose stop

Write-Host "✅ Clean shutdown complete." -ForegroundColor Green