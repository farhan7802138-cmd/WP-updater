@echo off
title WordPress Auto-Updater (Playwright)
cd /d "%~dp0"

echo ===================================================
echo   WordPress Plugin & Theme Updater with Health Check
echo ===================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python main.py
) else (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py
    ) else (
        echo Python 3.12 path not found. Please ensure Python is in your PATH.
        pause
    )
)
