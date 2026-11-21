<#
.SYNOPSIS
    Builds Moon Launcher CLI & GUI executables and Windows Setup Installer (.exe).
#>
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$ModBuild = Join-Path $RootDir "moon-sync-mod\build_mod.ps1"
if ((Test-Path $ModBuild) -and (Get-Command "javac" -ErrorAction SilentlyContinue)) {
    Write-Host "==> Building Moon Sync multi-loader mod JARs..." -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ModBuild
}

Write-Host "==> Checking Python & PyInstaller..." -ForegroundColor Cyan
python -c "import PyInstaller, webview, PIL, psutil" | Out-Null

$WorkDir = Join-Path $RootDir "build\work"
$DistDir = Join-Path $RootDir "dist"
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistDir "releases") | Out-Null

Write-Host "==> Building Moon-Launcher-CLI.exe..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean --workpath "$WorkDir\cli" --distpath "$DistDir" "$RootDir\build\Moon-Launcher-CLI.spec"

Write-Host "==> Building Moon-Launcher-GUI.exe..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean --workpath "$WorkDir\gui" --distpath "$DistDir" "$RootDir\build\Moon-Launcher-GUI.spec"

if (-not $SkipInstaller) {
    $isccCmd = Get-Command "iscc" -ErrorAction SilentlyContinue
    $iscc = if ($isccCmd) { $isccCmd.Source } else { $null }

    if (-not $iscc) {
        $candidates = @(
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
        )
        $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }

    if (-not $iscc) {
        throw "Inno Setup 6 (ISCC.exe) not found. Install Inno Setup 6 or pass -SkipInstaller."
    }

    Write-Host "==> Building Windows Setup Installer with Inno Setup ($iscc)..." -ForegroundColor Cyan
    & $iscc "$RootDir\build\Moon-Launcher-Setup.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE"
    }
}

Write-Host "==> Build complete! Outputs in: $DistDir" -ForegroundColor Green
