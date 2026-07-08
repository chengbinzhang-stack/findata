@echo off
echo ============================================
echo   Transcript Downloader - Windows Deploy
echo ============================================
echo.

:: Install Git if not found
git --version 2>nul
if %errorlevel% neq 0 (
    echo Installing Git...
    winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
    echo NOTE: Please restart this script after Git installation completes.
    pause
    exit /b
)

:: Check if Python 3.13 is installed (use py launcher)
py -3.13 --version 2>nul >nul
if %errorlevel% neq 0 (
    echo.
    echo Python 3.13 not found. Installing...
    winget install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
    echo NOTE: Please restart this script after Python installation completes.
    pause
    exit /b
)

:: Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%findata

:: Clone or update repo
if exist "%PROJECT_DIR%" (
    echo.
    echo Updating existing code...
    cd /d "%PROJECT_DIR%"
    git pull origin master
) else (
    echo.
    echo Cloning repository...
    git clone https://github.com/chengbinzhang-stack/findata.git "%PROJECT_DIR%"
    cd /d "%PROJECT_DIR%"
)

:: Install dependencies
echo.
echo Installing Python dependencies...
py -3.13 -m pip install -r requirements.txt

:: Start server
echo.
echo ============================================
echo   Starting server at http://localhost:8000
echo ============================================
echo.
py -3.13 main.py
