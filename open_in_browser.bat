@echo off
title WordPress Auto-Updater Web Dashboard
cd /d "%~dp0"

echo ===================================================
echo   Opening WordPress Auto-Updater in your Browser...
echo ===================================================

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python web_app.py
) else (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" web_app.py
)
pause

