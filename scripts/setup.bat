@echo off
echo Setting up Plagiarism Detection System...

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Copy environment file
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration before running the application
)

echo Setup complete!
echo.
echo To start the application:
echo 1. Edit .env file with your database and MinIO configuration
echo 2. Run: python start.py
echo.
echo Or use Docker Compose:
echo docker-compose up -d
pause
