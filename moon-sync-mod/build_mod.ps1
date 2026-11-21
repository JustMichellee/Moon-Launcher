<#
.SYNOPSIS
    Compiles multi-loader moon-sync-1.0.0.jar (Fabric, Quilt, Forge 1.13-1.21+, NeoForge)
    and moon-sync-forge-legacy-1.0.0.jar (Forge 1.8-1.12.2) targeting Java 8 bytecode.
#>
$ErrorActionPreference = "Stop"
$ModRoot = $PSScriptRoot
$BinRoot = Join-Path $ModRoot "bin"
if (Test-Path $BinRoot) { Remove-Item $BinRoot -Recurse -Force }

$ModernStubClasses = Join-Path $BinRoot "stubs-modern"
$ModernClasses     = Join-Path $BinRoot "classes-modern"
$LegacyStubClasses = Join-Path $BinRoot "stubs-legacy"
$LegacyClasses     = Join-Path $BinRoot "classes-legacy"

New-Item -ItemType Directory -Force -Path $ModernStubClasses, $ModernClasses, $LegacyStubClasses, $LegacyClasses | Out-Null

# 1. Compile modern stubs (compile-only, excluded from final JAR)
$modernStubFiles = Get-ChildItem -Recurse (Join-Path $ModRoot "compile-stubs\modern") -Filter *.java | ForEach-Object { $_.FullName }
& javac --release 8 -d $ModernStubClasses $modernStubFiles
if ($LASTEXITCODE -ne 0) { throw "Failed to compile modern stubs" }

# 2. Compile modern universal mod classes + copy resources
$modernSrcFiles = Get-ChildItem -Recurse (Join-Path $ModRoot "src\main\java") -Filter *.java | ForEach-Object { $_.FullName }
& javac --release 8 -cp $ModernStubClasses -d $ModernClasses $modernSrcFiles
if ($LASTEXITCODE -ne 0) { throw "Failed to compile modern Moon Sync mod" }

Copy-Item (Join-Path $ModRoot "src\main\resources\*") $ModernClasses -Recurse -Force

$ModernJar = Join-Path $ModRoot "moon-sync-1.0.0.jar"
$ModernManifest = Join-Path $ModernClasses "META-INF\MANIFEST.MF"
& jar cfm $ModernJar $ModernManifest -C $ModernClasses .
if ($LASTEXITCODE -ne 0) { throw "Failed to package moon-sync-1.0.0.jar" }

# 3. Compile legacy Forge stubs (compile-only)
$legacyStubFiles = Get-ChildItem -Recurse (Join-Path $ModRoot "compile-stubs\legacy") -Filter *.java | ForEach-Object { $_.FullName }
& javac --release 8 -d $LegacyStubClasses $legacyStubFiles
if ($LASTEXITCODE -ne 0) { throw "Failed to compile legacy stubs" }

# 4. Compile legacy Forge mod classes (shared core + legacy entrypoint) + copy resources
$coreSrcFiles = Get-ChildItem (Join-Path $ModRoot "src\main\java\dev\moonlauncher\sync") -Filter *.java | ForEach-Object { $_.FullName }
$legacyEntryFiles = Get-ChildItem -Recurse (Join-Path $ModRoot "src\legacy\java") -Filter *.java | ForEach-Object { $_.FullName }
& javac --release 8 -cp $LegacyStubClasses -d $LegacyClasses ($coreSrcFiles + $legacyEntryFiles)
if ($LASTEXITCODE -ne 0) { throw "Failed to compile legacy Moon Sync mod" }

Copy-Item (Join-Path $ModRoot "src\legacy\resources\*") $LegacyClasses -Recurse -Force

$LegacyJar = Join-Path $ModRoot "moon-sync-forge-legacy-1.0.0.jar"
$LegacyManifest = Join-Path $LegacyClasses "META-INF\MANIFEST.MF"
& jar cfm $LegacyJar $LegacyManifest -C $LegacyClasses .
if ($LASTEXITCODE -ne 0) { throw "Failed to package moon-sync-forge-legacy-1.0.0.jar" }

Write-Host "==> Built:" -ForegroundColor Green
Write-Host "    $ModernJar"
Write-Host "    $LegacyJar"

