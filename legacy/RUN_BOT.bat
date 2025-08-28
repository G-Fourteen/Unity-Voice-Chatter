@echo off
cd /d "%~dp0"
python --version | findstr "3.8 3.9 3.10 3.11" >nul
if errorlevel 1 (
    echo ERROR: Python 3.8-3.11 required. Please install a compatible version.
    pause
    exit /b 1
)
python bot.py
pause