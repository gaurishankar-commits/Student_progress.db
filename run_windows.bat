@echo off
title Student Academic Progression DBMS System
echo ======================================================================
echo Student Academic Progression and Portfolio Management System
echo DBMS Mini-Project Launch Script (Windows)
echo ======================================================================
echo.

REM Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH.
    echo Please install Python 3.9+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/3] Checking dependencies from requirements.txt...
pip install -r requirements.txt --quiet

echo [2/3] Initializing 3NF SQLite database and verifying sample records...
python -c "import database; database.init_db(); print('Database ready.')"

echo [3/3] Starting Flask Application Server...
echo.
echo Application running at: http://127.0.0.1:5000
echo Press Ctrl+C to stop the local server.
echo.

python app.py

pause
