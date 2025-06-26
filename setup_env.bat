@echo off
echo Setting up Gmail Monitor environment...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

echo.
echo Virtual environment is ready!
echo To activate it manually, run: venv\Scripts\activate.bat
echo To start the application, run: python launcher.py
echo.
pause
