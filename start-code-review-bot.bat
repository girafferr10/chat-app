@echo off
title Code Review Bot Launcher

cd /d "%~dp0"

echo =====================================
echo       Code Review Bot Launcher
echo =====================================

echo.
echo Checking Node.js...

node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is missing.
    echo Install Node.js 20+ and try again.
    pause
    exit /b 1
)

echo Node found:
node --version

echo.
echo Checking dependencies...

if not exist "node_modules\" (
    echo Installing packages...
    call npm install
) else (
    echo Packages already installed.
)

echo.
echo Starting Code Review Bot...
start "Code Review Bot" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo Waiting for server startup...
timeout /t 8 /nobreak >nul

echo Opening browser...
start http://localhost:5000

echo.
echo =====================================
echo Running at:
echo http://localhost:5000
echo =====================================

pause