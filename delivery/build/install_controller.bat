@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
:: RenderAgent Controller — One-Click Installer
:: ============================================================
title RenderAgent Controller Setup
color 0F
echo.
echo   ================================================
echo    RenderAgent Controller - Installation
echo   ================================================
echo.

set "INSTALL_DIR=C:\RenderAgent"
set "APP_DIR=%INSTALL_DIR%\app"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "NODE_URL=https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
set "NODE_INSTALLER=%TEMP%\node_installer.msi"

:: Determine script location (where installer was launched from)
set "SOURCE_DIR=%~dp0.."
for %%I in ("%SOURCE_DIR%") do set "SOURCE_DIR=%%~fI"

:: ---- Step 1: Check / Install Python ----
echo [1/7] Checking Python installation...
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
    echo         Python installed successfully.
) else (
    echo         Python is already installed.
)

:: ---- Step 2: Check / Install Node.js ----
echo [2/7] Checking Node.js installation...
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo         Node.js not found. Downloading Node.js v20...
    powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%NODE_URL%' -OutFile '%NODE_INSTALLER%' -UseBasicParsing}"
    if not exist "%NODE_INSTALLER%" (
        echo [ERROR] Failed to download Node.js. Please check your internet connection.
        pause
        exit /b 1
    )
    echo         Installing Node.js silently...
    start /wait msiexec /i "%NODE_INSTALLER%" /quiet /norestart
    del "%NODE_INSTALLER%" >nul 2>&1
    echo         Node.js installed successfully.
) else (
    echo         Node.js is already installed.
)

:: Refresh PATH so python and npm are available in this session
for /f "tokens=*" %%a in ('where python 2^>nul') do set "PYTHON_CMD=%%a"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

:: ---- Step 3: Copy Application Files ----
echo [3/7] Copying application files...
if not exist "%APP_DIR%" mkdir "%APP_DIR%"
xcopy /E /I /Y /Q "%SOURCE_DIR%\*" "%APP_DIR%\" >nul 2>&1
echo         Files copied to %APP_DIR%

:: ---- Step 4: Install Python Dependencies ----
echo [4/7] Installing Python packages (this may take a few minutes)...
"%PYTHON_CMD%" -m pip install --upgrade pip -q
if exist "%APP_DIR%\build\requirements-controller.txt" (
    "%PYTHON_CMD%" -m pip install -r "%APP_DIR%\build\requirements-controller.txt" -q
)
if exist "%APP_DIR%\build\requirements-worker.txt" (
    "%PYTHON_CMD%" -m pip install -r "%APP_DIR%\build\requirements-worker.txt" -q
)
echo         Python packages installed.

:: ---- Step 5: Install Playwright Chromium ----
echo [5/7] Installing Playwright browser (this may take a few minutes)...
"%PYTHON_CMD%" -m playwright install chromium >nul 2>&1
echo         Playwright browser ready.

:: ---- Step 6: Build React Dashboard ----
echo [6/7] Building dashboard interface...
if exist "%APP_DIR%\controller\dashboard" (
    cd /d "%APP_DIR%\controller\dashboard"
    if exist "package.json" (
        call npm install --silent >nul 2>&1
        call npm run build 2>nul >nul
    )
)
echo         Dashboard built.

:: ---- Step 7: Create Folders and Shortcuts ----
echo [7/7] Creating folders and shortcuts...

:: Create input/output folders
mkdir "%INSTALL_DIR%\input" 2>nul
mkdir "%INSTALL_DIR%\output" 2>nul

:: Create start scripts in install dir
echo @echo off > "%INSTALL_DIR%\Start_Controller.bat"
echo cd /d "%APP_DIR%" >> "%INSTALL_DIR%\Start_Controller.bat"
echo python -m controller.main ^>^> "%INSTALL_DIR%\logs\controller.log" 2^>^&1 >> "%INSTALL_DIR%\Start_Controller.bat"

echo @echo off > "%INSTALL_DIR%\Start_Worker.bat"
echo cd /d "%APP_DIR%" >> "%INSTALL_DIR%\Start_Worker.bat"
echo python -m worker.agent ^>^> "%INSTALL_DIR%\logs\worker.log" 2^>^&1 >> "%INSTALL_DIR%\Start_Worker.bat"

mkdir "%INSTALL_DIR%\logs" 2>nul

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
