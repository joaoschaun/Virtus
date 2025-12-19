# Start VIRTUS Dashboard Backend
$ErrorActionPreference = "Stop"

# Navigate to backend directory
Set-Location $PSScriptRoot

# Start uvicorn
Write-Host "Starting VIRTUS Dashboard Backend..." -ForegroundColor Green
python -m uvicorn main:app --host 0.0.0.0 --port 8000
