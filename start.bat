@echo off
REM Change to the script's directory
cd /d "%~dp0"
echo Starting Gmail Monitor Launcher...
echo Current directory: %cd%
python launcher.py
pause
