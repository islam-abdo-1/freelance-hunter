@echo off
REM Freelance Hunter - Windows Deployment Launcher
REM Run this file directly (double-click or from cmd)

echo ========================================
echo Freelance Hunter - Windows Deployment
echo ========================================
echo.

REM Check if PowerShell script exists
if not exist "auto-deploy.ps1" (
    echo ERROR: auto-deploy.ps1 not found!
    pause
    exit /b 1
)

echo Starting automated deployment...
echo.

REM Run PowerShell script with execution policy bypass
powershell -ExecutionPolicy Bypass -File "auto-deploy.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Deployment failed with error code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Deployment completed successfully!
pause