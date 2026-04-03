@echo off
title Financial Audit System - Setup and Launcher
color 0A

:: 1. Force the batch script to register its own root directory
cd /d "%~dp0"
echo [System] Working directory locked to: %CD%
echo.

echo ========================================================
echo   Financial Oversight ^& Audit System
echo   Client-Proof Engine Startup
echo ========================================================
echo.

:: We completely abandon activate.bat and global PATH variables because they break on client machines.
:: We use explicit, direct paths inside the virtual environment.
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VENV_STREAMLIT=%CD%\.venv\Scripts\streamlit.exe"

:: 2. If the virtual environment exists, skip straight to it using absolute paths.
if exist "%VENV_PYTHON%" (
    echo [1/3] Isolated environment located.
    goto :run_app
)

:: 3. If no isolated environment exists, gracefully find ANY Python to spawn one.
echo [1/3] No local environment found. Searching machine...
set "SYS_PYTHON="

python --version >nul 2>&1
if %errorlevel% equ 0 set "SYS_PYTHON=python"

if not defined SYS_PYTHON (
    py -0 >nul 2>&1
    if %errorlevel% equ 0 set "SYS_PYTHON=py"
)

if not defined SYS_PYTHON (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%D\python.exe" set "SYS_PYTHON=%%D\python.exe"
    )
)

if not defined SYS_PYTHON (
    echo [ERROR] CRITICAL: Python 3.9+ is completely missing from this machine.
    echo Please install Python (and check "Add to PATH" during installation) to continue.
    pause
    exit /b 1
)

:: 4. Build the isolated environment
echo [2/3] Python cluster found. Building isolated environment...
%SYS_PYTHON% -m venv "%CD%\.venv"
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Failed to compile isolated environment. Contact support.
    pause
    exit /b 1
)

:run_app
echo [2/3] Validating system dependencies...
:: Directly pip install WITHOUT calling activate.bat using the absolute executable!
"%VENV_PYTHON%" -m pip install -r requirements.txt --quiet 2>nul
if %errorlevel% neq 0 (
    echo Bootstrapping core modules...
    "%VENV_PYTHON%" -m pip install streamlit pandas numpy scipy pytest pytest-cov
)

echo [3/3] Initiating Server...
echo.
echo ========================================================
echo   Dashboard will open in your default browser.
echo   Press Ctrl+C in this window to safely stop the node.
echo ========================================================
echo.

:: 5. Launch using the direct absolute executable!
if exist "%VENV_STREAMLIT%" (
    "%VENV_STREAMLIT%" run "%CD%\app.py" --server.headless=true --browser.gatherUsageStats=false
) else (
    "%VENV_PYTHON%" -m streamlit run "%CD%\app.py" --server.headless=true --browser.gatherUsageStats=false
)

if %errorlevel% neq 0 (
    echo.
    echo [FATAL ERROR] The application crashed unexpectedly.
    pause
    exit /b 1
)

pause
