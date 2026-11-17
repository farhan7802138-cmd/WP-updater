@echo off
title Local Mock Test - WordPress Updater
cd /d "%~dp0"

echo ===================================================
echo     Starting Local Mock WordPress Test Server...
echo ===================================================

start "" /B "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" test_local_server.py
timeout /t 2 >nul

echo.
echo Running updater against local test site (Visible Browser)...
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" main.py --cli --file test_mock_url.txt

echo.
echo Test completed! Check the reports folder.
pause

