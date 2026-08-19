<#
.SYNOPSIS
    Demo (örnek) veri oluşturur. YALNIZCA GELİŞTİRME ORTAMI İÇİNDİR.

.DESCRIPTION
    50 öğrenci, 10 eğitmen, 2 havuz, dersler, yoklamalar, ödemeler ve performans
    kayıtları üretir. Tüm kayıtlar `is_demo = true` ile işaretlenir.

.EXAMPLE
    .\scripts\seed_demo.ps1
    .\scripts\seed_demo.ps1 -Reset -Students 100
#>
[CmdletBinding()]
param(
    [switch]$Reset,
    [int]$Students = 50,
    [int]$Instructors = 10
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Host '  [X] Sanal ortam bulunamadi.' -ForegroundColor Red
    exit 1
}

$arguments = @('-m', 'app.db.seed', '--students', "$Students", '--instructors', "$Instructors")
if ($Reset) { $arguments += '--reset' }

Push-Location (Join-Path $root 'backend')
try {
    & $python $arguments
    if ($LASTEXITCODE -ne 0) { throw "Demo verisi olusturulamadi (cikis kodu $LASTEXITCODE)" }
} finally {
    Pop-Location
}
