@echo off
chcp 65001 >nul
title RenderAgent Worker
color 0F

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo.
echo   ================================================
echo    RenderAgent Worker
echo   ================================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please run the installer first:
    echo   build\install_worker.bat
    echo.
    echo If the problem continues, please contact support.
    echo.
    pause
    exit /b 1
)

:: Check if config exists
if not exist "config.json" (
    echo First time setup detected...
    echo Opening setup wizard...
    echo.
)

:: Run the worker
python -m worker.agent

:: If we get here, something went wrong
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The Worker could not start.
    echo.
    echo Please try the following:
    echo   1. Make sure the Controller is running
    echo   2. Check your network connection
    echo   3. Restart your computer and try again
    echo   4. Contact support for help
    echo.
    echo Log file: C:\RenderAgent\logs\worker.log
    echo.
    pause
)
