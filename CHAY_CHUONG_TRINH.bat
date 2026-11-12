@echo off
chcp 65001 >nul
cd /d "%~dp0"
title He thong nhan dien bien so xe
set "PYTHONUTF8=1"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] May nay chua duoc cai thu vien.
    echo Hay bam dup CAI_DAT_LAN_DAU.bat truoc.
    pause
    exit /b 1
)

if not exist "models\best.pt" (
    echo [LOI] Thieu mo hinh models\best.pt
    echo Hay chep day du thu muc models cung voi du an.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo Chuong trinh da dung do co loi. Hay chup man hinh nay de kiem tra.
    pause
)
