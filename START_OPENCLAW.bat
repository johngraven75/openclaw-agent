@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv || python -m venv .venv
)
if not exist ".deps-installed" (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 pause & exit /b 1
  type nul > ".deps-installed"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:7865/api/health' -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:7865'; exit 0 } catch { exit 1 }"
if %errorlevel%==0 exit /b 0
start "" http://127.0.0.1:7865
".venv\Scripts\python.exe" app.py
