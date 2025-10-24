@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM ===============================================
REM Kids Story Maker — run.bat  (Python 3.11 version)
REM Starts backend (FastAPI) and frontend (Streamlit)
REM Usage:
REM   run.bat           -> just run
REM   run.bat install   -> install deps first
REM ===============================================

REM ---- Ports ----
set BACKEND_PORT=8000
set STREAMLIT_PORT=8501

REM ---- Use Python 3.11 explicitly ----
set PYTHON_EXE=py -3.11

REM ---- Detect or create virtual environment ----
set VENV_DIR=
if exist "venv\Scripts\activate.bat" set VENV_DIR=venv
if not defined VENV_DIR if exist "venev\Scripts\activate.bat" set VENV_DIR=venev

if not defined VENV_DIR (
  echo [INFO] No venv found. Creating one with Python 3.11 ...
  %PYTHON_EXE% -m venv venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv. Ensure Python 3.11 is installed and on PATH.
    exit /b 1
  )
  set VENV_DIR=venv
)

echo [OK] Using virtual environment: %VENV_DIR%
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Dependencies installed.

REM ---- Check for .env ----
if not exist ".env" (
  echo [WARN] .env not found. Create one with:
  echo GEMINI_API_KEY=your_api_key_here
  echo GEMINI_MODEL_ID=gemini-2.0-flash
) else (
  echo [OK] .env found.
)

call venv\Scripts\activate

start "fastapi backend" uvicorn backend.main:app --reload --port 8000
start "streamlit frontend" streamlit run frontend/streamlit_app.py 

echo ======================================
echo [INFO] Both backend and frontend started.
pause
