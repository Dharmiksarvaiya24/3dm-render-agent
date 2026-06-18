@echo off
echo ==========================================
echo  RenderAgent Build Script
echo ==========================================
echo.

REM Step 1: Install controller dependencies
echo [1/6] Installing controller Python dependencies...
pip install -r requirements-controller.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install controller dependencies
    exit /b 1
)

REM Step 2: Install worker dependencies
echo [2/6] Installing worker Python dependencies...
pip install -r requirements-worker.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install worker dependencies
    exit /b 1
)

REM Step 3: Install Playwright Chromium
echo [3/6] Installing Playwright Chromium browser...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Playwright Chromium
    exit /b 1
)

REM Step 4: Build React dashboard
echo [4/6] Building React dashboard...
cd ..\controller\dashboard
npm install
npm run build
cd ..\..\build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build dashboard
    exit /b 1
)

REM Step 5: Package controller with PyInstaller
echo [5/6] Packaging controller.exe...
pyinstaller --onefile --name controller --add-data "..\controller\dashboard\dist;dashboard\dist" ..\controller\main.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build controller.exe
    exit /b 1
)

REM Step 6: Package worker with PyInstaller
echo [6/6] Packaging worker.exe...
pyinstaller --onefile --name worker ..\worker\agent.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build worker.exe
    exit /b 1
)

echo.
echo Copying executables to dist/...
mkdir dist 2>nul
copy dist\controller\controller.exe dist\controller.exe
copy dist\worker\worker.exe dist\worker.exe

echo.
echo ==========================================
echo  Build complete!
echo  Output:
echo    dist\controller.exe
echo    dist\worker.exe
echo ==========================================