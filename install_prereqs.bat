@echo off
setlocal

:: This batch file runs the PowerShell prerequisite installer as administrator
:: It will launch the install_prereqs.ps1 script with elevated privileges

echo [INFO] Starting Gmail Watcher prerequisite setup...
echo [INFO] This will run the PowerShell script as administrator.
echo.

:: Check if PowerShell script exists
if not exist "%~dp0install_prereqs.ps1" (
    echo [ERROR] install_prereqs.ps1 not found in the current directory.
    echo [ERROR] Please ensure the PowerShell script is in the same folder as this batch file.
    pause
    exit /b 1
)

:: Run PowerShell script as administrator
echo [INFO] Launching PowerShell script as administrator...
echo [INFO] You may see a UAC prompt - please click "Yes" to continue.
echo.

powershell -Command "Start-Process PowerShell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0install_prereqs.ps1\"' -Wait"

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] PowerShell script execution completed.
) else (
    echo.
    echo [ERROR] PowerShell script execution failed or was cancelled.
)

echo.
pause