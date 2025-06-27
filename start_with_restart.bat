@echo off
REM Gmail Monitor Auto-Restart Launcher
REM This batch file starts the Gmail monitor with automatic restart functionality

cd /d "%~dp0"
echo Starting Gmail Monitor with Auto-Restart...
echo Current directory: %cd%
echo.

REM Parse command line arguments
set "DEBUG_MODE="
set "MAX_RESTARTS="
set "RESTART_DELAY=5"
set "LOG_FILE="

:parse_args
if "%1"=="" goto :run_monitor
if /i "%1"=="--debug" set "DEBUG_MODE=--debug"
if /i "%1"=="--max-restarts" (
    set "MAX_RESTARTS=--max-restarts %2"
    shift
)
if /i "%1"=="--restart-delay" (
    set "RESTART_DELAY=%2"
    shift
)
if /i "%1"=="--log-file" (
    set "LOG_FILE=--log-file %2"
    shift
)
shift
goto :parse_args

:run_monitor
echo Command: python auto_restart_monitor.py %DEBUG_MODE% %MAX_RESTARTS% --restart-delay %RESTART_DELAY% %LOG_FILE%
echo.
python auto_restart_monitor.py %DEBUG_MODE% %MAX_RESTARTS% --restart-delay %RESTART_DELAY% %LOG_FILE%

echo.
echo Auto-restart monitor has stopped.
pause
