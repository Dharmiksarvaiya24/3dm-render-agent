@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
:: RenderAgent Worker — One-Click Installer
:: ============================================================
title RenderAgent Worker Setup
color 0F
echo.
echo   ================================================
echo    RenderAgent Worker - Installation
echo   ================================================
echo.

set "INSTALL_DIR=C:\RenderAgent"
set "APP_DIR=%INSTALL_DIR%\app"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"

:: Determine script location (where installer was launched from)
set "SOURCE_DIR=%~dp0.."
for %%I in ("%SOURCE_DIR%") do set "SOURCE_DIR=%%~fI"

:: ---- Step 1: Check / Install Python ----
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo         Python not found. Downloading Python 3.11...
    powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing}"
    if not exist "%PYTHON_INSTALLER%" (
        echo [ERROR] Failed to download Python. Please check your internet connection.
        pause
        exit /b 1
    )
    echo         Installing Python silently...
    start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    del "%PYTHON_INSTALLER%" >nul 2>&1
    echo         Python installed.
) else (
    echo         Python is already installed.
)

:: Refresh PATH so python is available in this session
for /f "tokens=*" %%a in ('where python 2^>nul') do set "PYTHON_CMD=%%a"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

:: ---- Step 2: Copy Application Files ----
echo [2/4] Copying application files...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
xcopy /E /I /Y /Q "%SOURCE_DIR%\*" "%APP_DIR%\" >nul 2>&1
echo         Files copied to %APP_DIR%

:: ---- Step 3: Install Python Dependencies ----
echo [3/4] Installing Python packages (this may take a few minutes)...
"%PYTHON_CMD%" -m pip install --upgrade pip -q
if exist "%APP_DIR%\build\requirements-worker.txt" (
    "%PYTHON_CMD%" -m pip install -r "%APP_DIR%\build\requirements-worker.txt" -q
)
if exist "%APP_DIR%\build\requirements-controller.txt" (
    "%PYTHON_CMD%" -m pip install -r "%APP_DIR%\build\requirements-controller.txt" -q
)
echo         Python packages installed.

:: ---- Step 4: Install Playwright Chromium ----
echo [4/4] Installing Playwright browser (this may take a few minutes)...
"%PYTHON_CMD%" -m playwright install chromium >nul 2>&1
echo         Playwright browser ready.

:: ---- Create Folders and Shortcuts ----
echo.
echo   Creating folders and shortcuts...

mkdir "%INSTALL_DIR%\input" 2>nul
mkdir "%INSTALL_DIR%\output" 2>nul
mkdir "%INSTALL_DIR%\logs" 2>nul

:: Create start scripts in install dir
echo @echo off > "%INSTALL_DIR%\Start_Controller.bat"
echo cd /d "%APP_DIR%" >> "%INSTALL_DIR%\Start_Controller.bat"
echo python -m controller.main ^>^> "%INSTALL_DIR%\logs\controller.log" 2^>^&1 >> "%INSTALL_DIR%\Start_Controller.bat"

echo @echo off > "%INSTALL_DIR%\Start_Worker.bat"
echo cd /d "%APP_DIR%" >> "%INSTALL_DIR%\Start_Worker.bat"
echo python -m worker.agent ^>^> "%INSTALL_DIR%\logs\worker.log" 2^>^&1 >> "%INSTALL_DIR%\Start_Worker.bat"

:: Create Desktop shortcuts using PowerShell
powershell -NoProfile -Command "& {$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\RenderAgent Controller.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\Start_Controller.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Start RenderAgent Controller'; $Shortcut.IconLocation = 'shell32.dll, 22'; $Shortcut.Save()}" >nul 2>&1
powershell -NoProfile -Command "& {$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\RenderAgent Worker.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\Start_Worker.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Start RenderAgent Worker'; $Shortcut.IconLocation = 'shell32.dll, 22'; $Shortcut.Save()}" >nul 2>&1

echo.
echo   ================================================
echo    Setup Complete!
echo   ================================================
echo.
echo    Your shortcuts are on the Desktop:
echo      - RenderAgent Controller
echo      - RenderAgent Worker
echo.
echo    For any issues, please contact support.
echo.
pause
