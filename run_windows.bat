@echo off
REM ============================================================
REM  Fraud Detection Dashboard - Windows x64 launcher
REM  Double-click this file to set up and run the app.
REM  Requires: Python 3.11 or 3.12 (x64) installed.
REM ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul

REM --- Pick a Python launcher (py -3 preferred, else python) ---
where py >nul 2>nul && (set "PY=py -3") || (set "PY=python")

REM --- Create virtual environment on first run ---
if not exist ".venv\Scripts\activate.bat" (
  echo [setup] Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [error] Could not create venv. Install Python 3.11/3.12 x64 first.
    pause & exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

REM --- Install dependencies (first run downloads ~1-2 min) ---
echo [setup] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo [error] pip install failed. Check your internet connection.
  pause & exit /b 1
)

REM --- Launch the dashboard (opens in your browser) ---
echo [run] Starting Streamlit at http://localhost:8501 ...
streamlit run app\Home.py

pause
endlocal
