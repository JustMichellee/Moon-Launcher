@echo off
chcp 65001 >nul
title Moon Launcher Studio
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

:: 1. Prioritaskan Python dari Local AppData (Python 3.x user install)
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" "%~dp0launcher.py" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

:: 2. Cek Python dari Programs folder
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" "%~dp0launcher.py" %*
        if %ERRORLEVEL% NEQ 0 (
            echo.
            pause
        )
        goto :end
    )
)

:: 3. Cek py launcher
py -3 --version >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0launcher.py" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

:: 4. Cek python di PATH (pastikan bukan Microsoft Store stub yang error)
python -c "import sys" >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%~dp0launcher.py" %*
    if %ERRORLEVEL% NEQ 0 (
        echo.
        pause
    )
    goto :end
)

echo ======================================================================
echo [Moon Launcher] Python tidak ditemukan atau belum terpasang dengan benar!
echo.
echo Silakan install Python dari https://python.org
echo Pastikan untuk mencentang opsi "Add python.exe to PATH" saat menginstall.
echo ======================================================================
pause

:end
