# Script para iniciar o backend
Set-Location "c:\Users\Administrator\Desktop\Virtus\brain\dashboard\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
