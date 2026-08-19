@echo off
REM ===========================================================================
REM  Arayuz derleme / Frontend build
REM ===========================================================================
cd /d "%~dp0frontend"
title Arayuz Derleniyor

echo.
echo  [*] Node.js kontrol ediliyor...
where npm >nul 2>&1
if errorlevel 1 (
    echo  [X] Node.js/npm bulunamadi.
    echo      https://nodejs.org adresinden Node.js 18+ kurun.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo  [*] Bagimliliklar kuruluyor (birkac dakika surebilir)...
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo  [X] npm install basarisiz.
        pause
        exit /b 1
    )
)

echo  [*] Arayuz derleniyor...
call npm run build
if errorlevel 1 (
    echo.
    echo  [X] Derleme basarisiz.
    pause
    exit /b 1
)

echo.
echo  [+] Derleme tamamlandi: frontend\dist
echo  [*] Artik START_SWIMMING_SCHOOL.bat ile programi acabilirsiniz.
echo.
pause
