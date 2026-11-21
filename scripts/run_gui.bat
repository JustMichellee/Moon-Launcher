@echo off
chcp 65001 >nul
title Moon Launcher Studio (GUI)
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TARGET_PY=%ROOT_DIR%\src\gui_app.py"

:: 1. Virtual environment if present
if exist "%ROOT_DIR%\.venv\Scripts\pythonw.exe" (
    "%ROOT_DIR%\.venv\Scripts\python.exe" -c "import webview" >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        start "" "%ROOT_DIR%\.venv\Scripts\pythonw.exe" "%TARGET_PY%" %*
        exit /b
    )
)

:: 2. Python in PATH with pywebview
python -c "import webview" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw "%TARGET_PY%" %*
    exit /b
)

:: 3. Python from Local AppData
if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\bin\pythonw.exe" "%TARGET_PY%" %*
    exit /b
)

:: 4. Python from Programs directory
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\pythonw.exe" (
        "%%D\python.exe" -c "import webview" >nul 2>nul
        if not errorlevel 1 (
            start "" "%%D\pythonw.exe" "%TARGET_PY%" %*
            exit /b
        )
    )
)

:: 5. Fallback to built GUI executable
if exist "%ROOT_DIR%\dist\Moon-Launcher-GUI.exe" (
    start "" "%ROOT_DIR%\dist\Moon-Launcher-GUI.exe" %*
    exit /b
)
if exist "%ROOT_DIR%\Moon-Launcher-GUI.exe" (
    start "" "%ROOT_DIR%\Moon-Launcher-GUI.exe" %*
    exit /b
)

echo [Moon Launcher] Neither Python with pywebview nor Moon-Launcher-GUI.exe was found!
echo Run: pip install -r requirements.txt
pause
endlocal

