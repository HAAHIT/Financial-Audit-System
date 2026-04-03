@echo off
title Financial Audit System - Test Runner
color 0B

echo.
echo ========================================================
echo   Financial Audit System - Running Unit Tests
echo ========================================================
echo.

:: Activate virtual environment
if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Run START.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo Running all tests with coverage report...
echo.

python -m pytest tests/ -v --tb=short --cov=audit_rules --cov=data_ingestion --cov=database --cov-report=term-missing

echo.
echo ========================================================
echo   Tests Complete
echo ========================================================
pause
