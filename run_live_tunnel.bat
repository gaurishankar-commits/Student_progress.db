@echo off
title StudentTrack DBMS - Public Live Host Launcher
echo ======================================================================
echo Student Academic Progression and Portfolio Management System
echo Public Live Tunnel Launcher (OpenSSH + localhost.run)
echo ======================================================================
echo.

echo Starting Flask application server...
start /b python app.py > app_server.log 2>&1
timeout /t 3 >nul

echo.
echo ======================================================================
echo Connecting secure public HTTPS tunnel...
echo Your public live URL will appear below:
echo ======================================================================
echo.

ssh -R 80:127.0.0.1:5000 -o StrictHostKeyChecking=no nokey@localhost.run

pause
