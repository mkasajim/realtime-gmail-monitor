@echo off
echo Starting GCP Setup for Gmail Monitor...
echo.

REM Check if PowerShell is available
powershell -Command "Write-Host 'PowerShell is available'" >nul 2>&1
if errorlevel 1 (
    echo Error: PowerShell is not available or not in PATH
    echo Please ensure PowerShell is installed and accessible
    pause
    exit /b 1
)

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0setup_gcp.ps1"

if errorlevel 1 (
    echo.
    echo Error: GCP setup failed. Please check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo GCP setup completed successfully!
    echo.
    echo You can now run the Gmail monitor with:
    echo python gmail_monitor.py
    echo.
)

pause
