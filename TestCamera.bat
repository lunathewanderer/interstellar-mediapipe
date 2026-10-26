@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run Install.bat first.
    pause
    exit /b 1
)
if not exist "models\hand_landmarker.task" (
    echo The MediaPipe model is missing. Run Install.bat first.
    pause
    exit /b 1
)
echo === MEDIAPIPE WEBCAM TEST ===
echo Click the webcam window. Press D for landmarks and Q to quit.
".venv\Scripts\python.exe" main.py --tracker-only --quality medium
if errorlevel 1 (
    echo.
    echo The application could not start. Read the error above.
    pause
    exit /b 1
)
