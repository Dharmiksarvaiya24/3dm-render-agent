@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
:: RenderAgent — Create Client Delivery Package
:: ============================================================
title RenderAgent Packaging
color 0F

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
set "DELIVERY_DIR=%PROJECT_ROOT%\delivery"
set "TEMP_DIR=%TEMP%\renderagent_package"

echo.
echo   ================================================
echo    RenderAgent — Packaging for Client Delivery
echo   ================================================
echo.

:: Clean and recreate delivery folder
if exist "%DELIVERY_DIR%" (
    echo Cleaning old delivery folder...
    rmdir /S /Q "%DELIVERY_DIR%"
)
mkdir "%DELIVERY_DIR%"
echo.

:: Copy all source files
set "EXCLUDES=--exclude=.git --exclude=.DS_Store --exclude=venv --exclude=node_modules --exclude=__pycache__ --exclude=.pytest_cache --exclude=*.log --exclude=*.db --exclude=config.json --exclude=.key"

xcopy /E /I /Y /Q "%PROJECT_ROOT%\controller" "%DELIVERY_DIR%\controller\" >nul 2>&1
xcopy /E /I /Y /Q "%PROJECT_ROOT%\worker" "%DELIVERY_DIR%\worker\" >nul 2>&1
xcopy /E /I /Y /Q "%PROJECT_ROOT%\shared" "%DELIVERY_DIR%\shared\" >nul 2>&1
xcopy /E /I /Y /Q "%PROJECT_ROOT%\build" "%DELIVERY_DIR%\build\" >nul 2>&1

:: Copy start scripts
copy /Y "%PROJECT_ROOT%\start_controller.bat" "%DELIVERY_DIR%\" >nul 2>&1
copy /Y "%PROJECT_ROOT%\start_worker.bat" "%DELIVERY_DIR%\" >nul 2>&1

:: Copy README if it exists
if exist "%PROJECT_ROOT%\README.md" (
    copy /Y "%PROJECT_ROOT%\README.md" "%DELIVERY_DIR%\" >nul 2>&1
)

:: Create HOW_TO_USE.txt
echo RenderAgent — How to Use> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo ======================================= >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo 1.  PLUG IN THE USB DRIVE >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     Open the delivery folder on this USB drive. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo 2.  RUN THE INSTALLER >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     Double-click one of these files: >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo       - Install_Controller.bat   (for the main computer) >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo       - Install_Worker.bat       (for helper computers) >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     Wait for it to finish. It will install everything automatically. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo 3.  FIRST RUN SETUP >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     The first time you run the Controller or Worker, >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     a beautiful setup wizard will appear. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     Fill in your details and click SAVE. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo 4.  DAILY USE >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     After setup, just double-click the desktop shortcut every day. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo     That's it! RenderAgent will do the rest. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo ======================================= >> "%DELIVERY_DIR%\HOW_TO_USE.txt"
echo Need help? Contact support. >> "%DELIVERY_DIR%\HOW_TO_USE.txt"

:: Clean up temp
if exist "%TEMP_DIR%" rmdir /S /Q "%TEMP_DIR%"

echo.
echo   ================================================
echo    Packaging Complete!
echo   ================================================
echo.
echo    Delivery folder created at:
echo    %DELIVERY_DIR%
echo.
echo    Contents:
echo      - start_controller.bat
echo      - start_worker.bat
echo      - build/install_controller.bat
echo      - build/install_worker.bat
echo      - controller/
echo      - worker/
echo      - shared/
echo      - HOW_TO_USE.txt
echo.
echo    Give the 'delivery' folder to your client on USB.
echo.
pause
