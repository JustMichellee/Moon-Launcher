@echo off
chcp 65001 >nul
title Moon Launcher Studio GUI
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

:: 1. Prioritize Python from PATH (runs latest live code with full progress HUD & no flickering)
python -c "import webview" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw "%~dp0gui_app.py" %*
    exit /b
)

:: 2. Check Python from Local AppData
if exist "%LOCALAPPDATA%\Pythonin\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Pythonin\pythonw.exe" "%~dp0gui_app.py" %*
    exit /b
)

:: 3. Check Python from Programs directory
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\pythonw.exe" (
        start "" "%%D\pythonw.exe" "%~dp0gui_app.py" %*
        exit /b
    )
)

:: 4. Fallback to compiled executable if Python environment is missing
if exist "%~dp0Moon Launcher.exe" (
    start "" "%~dp0Moon Launcher.exe" %*
    exit /b
)

echo [Moon Launcher] Neither Python with pywebview nor Moon Launcher.exe was found!
pause
