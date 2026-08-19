<#
.SYNOPSIS
    Geliştirme ortamını başlatır (backend + frontend dev sunucusu).

.DESCRIPTION
    Backend'i uvicorn --reload ile, frontend'i Vite dev sunucusuyla başlatır.
    Her ikisi de ayrı pencerelerde çalışır ve kod değişikliklerinde otomatik yenilenir.

.EXAMPLE
    .\scripts\dev.ps1
    .\scripts\dev.ps1 -BackendOnly
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

Write-Host ''
Write-Host '  ==============================================================' -ForegroundColor Cyan
Write-Host '    AKILLI YUZME OKULU - GELISTIRME ORTAMI' -ForegroundColor Cyan
Write-Host '  ==============================================================' -ForegroundColor Cyan
Write-Host ''

if (-not (Test-Path $python)) {
    Write-Host '  [X] Sanal ortam bulunamadi. Once START_SWIMMING_SCHOOL.bat calistirin.' -ForegroundColor Red
    exit 1
}

if (-not $FrontendOnly) {
    Write-Host "  [*] Backend baslatiliyor (port $BackendPort)..." -ForegroundColor Yellow
    $backendArgs = @(
        '-m', 'uvicorn', 'app.main:app',
        '--host', '127.0.0.1',
        '--port', "$BackendPort",
        '--reload'
    )
    Start-Process -FilePath $python -ArgumentList $backendArgs `
        -WorkingDirectory (Join-Path $root 'backend')
    Write-Host "  [+] Backend  : http://127.0.0.1:$BackendPort" -ForegroundColor Green
    Write-Host "  [+] API docs : http://127.0.0.1:$BackendPort/docs" -ForegroundColor Green
}

if (-not $BackendOnly) {
    $frontendPath = Join-Path $root 'frontend'
    if (-not (Test-Path (Join-Path $frontendPath 'node_modules'))) {
        Write-Host '  [*] Frontend bagimliliklari kuruluyor...' -ForegroundColor Yellow
        Push-Location $frontendPath
        npm install --no-audit --no-fund
        Pop-Location
    }
    Write-Host '  [*] Frontend dev sunucusu baslatiliyor...' -ForegroundColor Yellow
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' -WorkingDirectory $frontendPath
    Write-Host '  [+] Arayuz   : http://localhost:5173' -ForegroundColor Green
}

Write-Host ''
Write-Host '  Kapatmak icin acilan pencereleri kapatin.' -ForegroundColor DarkGray
Write-Host ''
