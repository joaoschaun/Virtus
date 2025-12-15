@echo off
cd /d C:\Users\Administrator\Desktop\Virtus\brain\dashboard\backend
C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
