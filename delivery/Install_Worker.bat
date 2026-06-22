@echo off
chcp 65001 >nul
echo.
echo   ================================================
echo    RenderAgent Worker - Installation
echo   ================================================
echo.
echo  Installing... Please wait.
echo.
call ".\build\install_worker.bat"
pause
