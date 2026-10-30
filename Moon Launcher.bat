@echo off
chcp 65001 >nul
title Moon Launcher Studio
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "TARGET_PY=%~dp0launcher.py"
if not exist "%TARGET_PY%" (
    set "TARGET_PY=%~dp0Moon-Launcher\launcher.py"
)
if not exist "%TARGET_PY%" (
    set "TARGET_PY=%~dp0Moon Launcher\launcher.py"
)

:: 1. Prioritize Python from Local AppData
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" "%TARGET_PY%" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

:: 2. Check Python from Programs directory
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" "%TARGET_PY%" %*
        if %ERRORLEVEL% NEQ 0 (
            echo.
            pause
        )
        goto :end
    )
)

:: 3. Check py launcher
py -3 --version >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%TARGET_PY%" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

:: 4. Check python in PATH
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%TARGET_PY%" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

echo ======================================================================
echo [Moon Launcher] Python was not found or is not installed properly!
echo.
echo Please install Python 3.10+ from https://python.org
echo Make sure to check the option "Add python.exe to PATH" during installation.
echo ======================================================================
pause

:end
