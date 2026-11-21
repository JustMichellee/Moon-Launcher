<#
.SYNOPSIS
    Deploys Moon Launcher Cloudflare Worker + D1 database.
    Usage: .\deploy.ps1
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$npx = "npx"
Write-Host "==> Checking Cloudflare authentication (Wrangler)..." -ForegroundColor Cyan
$who = & $npx --yes wrangler whoami 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $who -match "not authenticated") {
    Write-Host "You are not logged in to Cloudflare yet. Opening browser login..." -ForegroundColor Yellow
    & $npx --yes wrangler login
    if ($LASTEXITCODE -ne 0) { throw "Cloudflare login failed" }
}

$wranglerToml = Get-Content "wrangler.toml" -Raw
if ($wranglerToml -match "REPLACE_WITH_YOUR_D1_DATABASE_ID") {
    Write-Host "==> Checking or creating D1 database 'moon_launcher_db'..." -ForegroundColor Cyan
    $d1ListRaw = & $npx --yes wrangler d1 list --json 2>$null | Out-String
    $dbId = $null
    if ($d1ListRaw) {
        try {
            $parsed = $d1ListRaw | ConvertFrom-Json
            $existing = $parsed | Where-Object { $_.name -eq "moon_launcher_db" } | Select-Object -First 1
            if ($existing) { $dbId = $existing.uuid }
        } catch {}
    }
    if (-not $dbId) {
        $createOut = & $npx --yes wrangler d1 create moon_launcher_db 2>&1 | Out-String
        Write-Host $createOut
        if ($createOut -match 'database_id\s*=\s*"([0-9a-fA-F-]+)"') {
            $dbId = $Matches[1]
        }
    }
    if (-not $dbId) { throw "Could not determine D1 database_id" }
    $wranglerToml = $wranglerToml -replace "REPLACE_WITH_YOUR_D1_DATABASE_ID", $dbId
    Set-Content -Path "wrangler.toml" -Value $wranglerToml -Encoding UTF8
    Write-Host "==> Bound D1 database_id: $dbId" -ForegroundColor Green
}

Write-Host "==> Applying schema.sql to Cloudflare D1 (remote)..." -ForegroundColor Cyan
& $npx --yes wrangler d1 execute moon_launcher_db --remote --file=schema.sql --yes
if ($LASTEXITCODE -ne 0) { throw "D1 schema execution failed" }

Write-Host "==> Deploying Cloudflare Worker..." -ForegroundColor Cyan
& $npx --yes wrangler deploy
if ($LASTEXITCODE -ne 0) { throw "Worker deploy failed" }

