param(
    [ValidateSet("api", "mock")]
    [string]$Mode = "api"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend-web"

if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    Write-Host "Installing web frontend dependencies..." -ForegroundColor Cyan
    & npm.cmd install --prefix $frontendRoot
}

$env:NEXT_PUBLIC_DATA_MODE = $Mode
Write-Host "Starting SeoulMate web frontend at http://localhost:3000 in $Mode mode" -ForegroundColor Green
& npm.cmd run dev --prefix $frontendRoot
