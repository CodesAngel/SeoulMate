$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend-web"

if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    Write-Host "Installing web frontend dependencies..." -ForegroundColor Cyan
    & npm.cmd install --prefix $frontendRoot
}

Write-Host "Starting SeoulMate web frontend at http://localhost:3000" -ForegroundColor Green
& npm.cmd run dev --prefix $frontendRoot
