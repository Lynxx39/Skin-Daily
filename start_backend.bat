@echo off
set PYTHONUNBUFFERED=1
cd /d "%~dp0"
".venv\Scripts\python.exe" -u -m uvicorn backend.main:app --reload --port 8000
