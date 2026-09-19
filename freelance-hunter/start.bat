@echo off
REM Freelance Hunter - Windows Startup Script

echo ========================================
echo Freelance Hunter - Multi-Agent Job Hunter
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo Python found: 
python --version

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Install Playwright browsers
echo Installing Playwright browsers...
playwright install chromium
if %errorlevel% neq 0 (
    echo WARNING: Playwright install failed (optional for API-only mode)
)

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "exports" mkdir exports

REM Initialize database
echo Initializing database...
python main.py init-db

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo To run a scan:
echo   python main.py scan
echo.
echo To run continuous scheduler:
echo   python main.py scheduler
echo.
echo To start dashboard API:
echo   python -m core.api.main
echo.
echo Then open http://localhost:8000/dashboard
echo.
pause