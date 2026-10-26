@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run Install.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" tools\prepare_touchdesigner.py --update
if errorlevel 1 (
    pause
    exit /b 1
)
echo.
echo 1. Open the saved GalaxyHands.toe in this folder.
echo 2. In TouchDesigner: Dialogs - Textport - Ctrl+V - Enter.
echo 3. After the update completes, press Ctrl+S to save.
echo 4. Open Run.bat. Snap or press C to change lighting.
echo.
echo Later updates load automatically when this saved project opens.
pause
