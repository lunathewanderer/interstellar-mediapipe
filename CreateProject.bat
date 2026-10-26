@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run Install.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" tools\prepare_touchdesigner.py
if errorlevel 1 (
    echo.
    echo Could not copy the setup command. Read the error above.
    pause
    exit /b 1
)
echo.
echo 1. Open TouchDesigner and choose Dialogs - Textport.
echo 2. Press Ctrl+V to paste the command, then press Enter.
echo 3. The display window should open after the network is built.
echo 4. Choose File - Save As and save GalaxyHands.toe in this folder.
echo.
echo Then open Run.bat. Future launches only require Run.bat or python main.py.
pause
