# Test script to start servers and check status
Write-Host "Starting backend server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\04_Development\Codebase_Explainer; python -m uvicorn app.main:app --reload --host localhost --port 8000"

Start-Sleep -Seconds 3

Write-Host "Starting Streamlit server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd D:\04_Development\Codebase_Explainer; python -m streamlit run streamlit_app.py --server.port 8501 --server.address localhost"

Start-Sleep -Seconds 5

Write-Host "Checking servers..."
try {
    $backend = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2
    Write-Host "Backend: OK" -ForegroundColor Green
} catch {
    Write-Host "Backend: Not responding" -ForegroundColor Red
}

try {
    $frontend = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 2
    Write-Host "Frontend: OK" -ForegroundColor Green
} catch {
    Write-Host "Frontend: Not responding" -ForegroundColor Red
}

Write-Host "`nServers should be starting. Check the PowerShell windows that opened."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:8501"

