@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Cai dat he thong nhan dien bien so xe

echo ============================================================
echo   CAI DAT HE THONG NHAN DIEN BIEN SO XE - LAN DAU
echo ============================================================
echo.

set "PYTHON_CMD="
py -3.12 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.12"
if not defined PYTHON_CMD (
    py -3.11 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
    py -3.10 -c "import sys" >nul 2>&1 && set "PYTHON_CMD=py -3.10"
)
if not defined PYTHON_CMD (
    python -c "import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 12)" >nul 2>&1 && set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [LOI] Chua tim thay Python 3.10, 3.11 hoac 3.12.
    echo Hay cai Python 3.12 64-bit tu https://www.python.org/downloads/
    echo Khi cai, nho chon "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Dang tao moi truong ao .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/4] Moi truong .venv da ton tai.
)

echo [2/4] Dang cap nhat pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error

echo [3/4] Dang cai cac thu vien. Buoc nay co the mat vai phut...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [4/4] Dang tai san mo hinh OCR cho lan chay dau...
".venv\Scripts\python.exe" -c "from fast_plate_ocr import LicensePlateRecognizer; LicensePlateRecognizer('cct-s-v2-global-model'); print('Da san sang mo hinh OCR')"
if errorlevel 1 goto :error

".venv\Scripts\python.exe" KIEM_TRA_HE_THONG.py
if errorlevel 1 goto :error

echo.
echo ============================================================
echo   CAI DAT THANH CONG
echo   Lan sau chi can bam dup CHAY_CHUONG_TRINH.bat
echo ============================================================
pause
exit /b 0

:error
echo.
echo [LOI] Cai dat chua hoan tat. Hay chup man hinh dong loi gui de kiem tra.
pause
exit /b 1
