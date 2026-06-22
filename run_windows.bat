@echo off

REM ============================================================
REM  Fraud Detection Dashboard - Windows x64 launcher
REM  Lan dau: tu dong cai dat (2-5 phut). Lan sau: mo ngay.
REM  Yeu cau: Python 3.11 hoac 3.12 (x64) tai python.org
REM ============================================================
setlocal
cd /d "%~dp0"
chcp 65001 >nul

REM --- Chon Python launcher ---
where py >nul 2>nul && (set "PY=py") || (set "PY=python")


REM --- Kiem tra Python ton tai ---
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [loi] Khong tim thay Python. Tai va cai Python 3.11/3.12 x64 tu python.org
  pause & exit /b 1
)

REM --- Tao virtual environment lan dau ---
if not exist ".venv\Scripts\activate.bat" (
  echo [cai dat] Tao moi truong ao...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [loi] Khong tao duoc venv. Kiem tra Python 3.11/3.12 x64.
    pause & exit /b 1
  )
  REM Xoa marker de bat buoc cai thu vien lan dau
  if exist ".installed" del ".installed"
)

call ".venv\Scripts\activate.bat"

REM --- Cai thu vien chi lan dau (hoac khi requirements.txt thay doi) ---
if not exist ".installed" (
  echo [cai dat] Cai thu vien lan dau [2-5 phut, can Internet]...
  python -m pip install --upgrade pip --quiet
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [loi] pip install that bai. Kiem tra ket noi mang.
    pause & exit /b 1
  )
  echo done > .installed
  echo [cai dat] Hoan tat.
)

REM --- Khoi dong dashboard ---
echo [chay] Mo trinh duyet tai http://localhost:8501 ...
start "" http://localhost:8501
streamlit run app\Home.py --server.port 8501

pause
endlocal
