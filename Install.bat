@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === INSTALL GALAXY HANDS ===
echo First-time setup requires 64-bit Python 3.12 and Internet access.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
    echo.
    echo Setup failed. Read the error above and the installation section in README.md.
    pause
    exit /b 1
)
echo.
echo Setup complete. Open Run.bat to start, or CreateProject.bat to prepare the full galaxy.
pause
