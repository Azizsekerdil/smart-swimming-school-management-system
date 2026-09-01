<#
.SYNOPSIS
    Masaüstü uygulamasını (tek klasör, kurulum gerektirmeyen) paketler.

.DESCRIPTION
    Sırasıyla: paketleme bağımlılıklarını doğrular, arayüz derlemesini kontrol
    eder (istenirse derler), PyInstaller ile paketler ve sonucu bildirir.
    Çıktı: dist\YuzmeOkulu\YuzmeOkulu.exe

.PARAMETER ArayuzuDerle
    Paketlemeden önce arayüzü yeniden derler (npm run build).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\masaustu_paketle.ps1
    powershell -ExecutionPolicy Bypass -File scripts\masaustu_paketle.ps1 -ArayuzuDerle
#>
[CmdletBinding()]
param(
    [switch]$ArayuzuDerle
)

$ErrorActionPreference = 'Stop'
$KOK = Split-Path -Parent $PSScriptRoot
$VENV_PY = Join-Path $KOK '.venv\Scripts\python.exe'

function Baslik($metin) {
    Write-Host ''
    Write-Host "  $metin" -ForegroundColor Cyan
    Write-Host ('  ' + ('-' * $metin.Length)) -ForegroundColor DarkGray
}

if (-not (Test-Path $VENV_PY)) {
    throw "Sanal ortam bulunamadi: $VENV_PY`nOnce START_SWIMMING_SCHOOL.bat calistirin."
}

# --------------------------------------------------------------- 1. bağımlılık
Baslik '1 - Paketleme bagimliliklari'

# `pip show` paket yoksa stderr'e yazar; $ErrorActionPreference='Stop' altında
# bu ölümcül hataya dönüşür. Bunun yerine sessiz bir içe aktarma denemesi yapılır.
function Modul-Var([string]$ad) {
    & $VENV_PY -c "import importlib.util as u, sys; sys.exit(0 if u.find_spec('$ad') else 1)"
    return $LASTEXITCODE -eq 0
}

function Modulu-Sagla([string]$paket, [string]$modul) {
    if (Modul-Var $modul) {
        Write-Host "  [+] $paket kurulu" -ForegroundColor Green
        return
    }
    Write-Host "  [*] $paket kuruluyor..." -ForegroundColor Yellow
    & $VENV_PY -m pip install $paket
    if ($LASTEXITCODE -ne 0) { throw "$paket kurulamadi." }
    Write-Host "  [+] $paket kuruldu" -ForegroundColor Green
}

Modulu-Sagla 'pyinstaller' 'PyInstaller'
Modulu-Sagla 'pywebview' 'webview'

# ----------------------------------------------------------------- 2. arayüz
if ($ArayuzuDerle) {
    Baslik '2 - Arayuz derlemesi'
    Push-Location (Join-Path $KOK 'frontend')
    try {
        if (-not (Test-Path 'node_modules')) {
            Write-Host '  [*] Bagimliliklar kuruluyor...' -ForegroundColor Yellow
            & npm install --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'npm install basarisiz.' }
        }
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Arayuz derlemesi basarisiz.' }
    }
    finally { Pop-Location }
    Write-Host '  [+] Derlendi' -ForegroundColor Green
}
else {
    Baslik '2 - Arayuz derlemesi (mevcut dist kullaniliyor)'
}

$indexYolu = Join-Path $KOK 'frontend\dist\index.html'
if (-not (Test-Path $indexYolu)) {
    throw "Arayuz derlenmemis: $indexYolu`nOnce derleyin veya -ArayuzuDerle kullanin."
}

# ------------------------------------------------------------- 3. paketleme
Baslik '3 - PyInstaller'

Push-Location $KOK
try {
    $env:PYTHONPATH = Join-Path $KOK 'backend'
    & $VENV_PY -m PyInstaller --noconfirm --clean 'desktop\yuzme_okulu.spec'
    if ($LASTEXITCODE -ne 0) { throw 'Paketleme basarisiz.' }
}
finally {
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    Pop-Location
}

# ------------------------------------------------------------------ 4. sonuç
Baslik '4 - Sonuc'

$exe = Join-Path $KOK 'dist\YuzmeOkulu\YuzmeOkulu.exe'
if (-not (Test-Path $exe)) {
    throw "Beklenen cikti uretilmedi: $exe"
}

$klasor = Join-Path $KOK 'dist\YuzmeOkulu'

# Paket denendiğinde uygulama kendi data\ ve logs\ klasörlerini exe'nin
# yanında oluşturur. Bunlar ÇALIŞMA verisidir; bir sonraki paketlemede veya
# dağıtıma dahil edilirse kullanıcıya başkasının veritabanı gider. Temizlenir.
foreach ($artik in @('data', 'logs', 'backups', '.env.example')) {
    $yol = Join-Path $klasor $artik
    if (Test-Path $yol) {
        Remove-Item $yol -Recurse -Force
        Write-Host "  [-] Calisma verisi temizlendi: $artik" -ForegroundColor DarkGray
    }
}

$boyut = (Get-ChildItem $klasor -Recurse -File | Measure-Object -Property Length -Sum).Sum

Write-Host ''
Write-Host '  [+] Paket hazir' -ForegroundColor Green
Write-Host "      Konum   : $klasor"
Write-Host ("      Boyut   : {0:N0} MB" -f ($boyut / 1MB))
Write-Host "      Calistir: $exe"
Write-Host ''
Write-Host '  Not: Veritabani, gunlukler ve yedekler exe''nin yanindaki data\,' -ForegroundColor DarkGray
Write-Host '  logs\ ve backups\ klasorlerinde tutulur. Klasoru tasirken' -ForegroundColor DarkGray
Write-Host '  bunlari da birlikte tasiyin.' -ForegroundColor DarkGray
Write-Host ''
