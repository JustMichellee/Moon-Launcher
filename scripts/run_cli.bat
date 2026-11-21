@echo off
chcp 65001 >nul
title Moon Launcher Studio (CLI)
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "TARGET_PY=%ROOT_DIR%\src\cli.py"

:: 1. Virtual environment if present
if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
    "%ROOT_DIR%\.venv\Scripts\python.exe" "%TARGET_PY%" %*
    goto :check_err
)

:: 2. Python from Local AppData
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" "%TARGET_PY%" %*
    goto :check_err
)

:: 3. Python from Programs directory
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" "%TARGET_PY%" %*
        goto :check_err
    )
)

:: 4. Windows py launcher
py -3 --version >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%TARGET_PY%" %*
    goto :check_err
)

:: 5. Python in PATH
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%TARGET_PY%" %*
    goto :check_err
)

:: 6. Fallback to built CLI executable
if exist "%ROOT_DIR%\dist\Moon-Launcher-CLI.exe" (
    "%ROOT_DIR%\dist\Moon-Launcher-CLI.exe" %*
    goto :check_err
)

echo ======================================================================
echo [Moon Launcher] Python 3.10+ was not found on this system!
echo Install Python from https://python.org and check "Add python.exe to PATH".
echo ======================================================================
pause
exit /b 1

:check_err
if %ERRORLEVEL% NEQ 0 (
    echo.
    pause
)
endlocal

