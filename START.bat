@echo off
title Financial Audit System - Setup and Launcher
color 0A

echo.
echo ========================================================
echo   Financial Oversight ^& Audit System
echo   One-Click Setup ^& Launcher
echo ========================================================
echo.

:: Check for Python
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Python found.

:: Install requirements (system-wide, skip if already installed)
echo [2/3] Checking dependencies...
py -m pip install -r requirements.txt --quiet 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies (this may take a few minutes on first run)...
    py -m pip install streamlit pandas numpy scipy
)

echo [3/3] Launching dashboard...
echo.
echo ========================================================
echo   Dashboard will open in your default browser.
echo   Press Ctrl+C in this window to stop the server.
echo ========================================================
echo.

:: Launch Streamlit
py -m streamlit run app.py --server.headless=true --browser.gatherUsageStats=false

pause
