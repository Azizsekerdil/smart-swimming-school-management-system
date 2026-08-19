@echo off
REM ===========================================================================
REM  Akilli Yuzme Okulu Yonetim Sistemi - Baslatici
REM  Smart Swimming School Management System - Launcher
REM
REM  Bu dosyaya cift tiklayarak programi baslatabilirsiniz.
REM ===========================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Akilli Yuzme Okulu Yonetim Sistemi
REM UTF-8 kod sayfasi: Turkce karakterlerin dogru gorunmesi icin
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

echo.
echo  ==============================================================
echo    AKILLI YUZME OKULU YONETIM SISTEMI
echo    Smart Swimming School Management System
echo  ==============================================================
echo.

REM --- Python kontrolu ---
set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
    echo  [!] Sanal ortam bulunamadi.
    echo  [*] Ilk kurulum baslatiliyor, bu birkac dakika surebilir...
    echo.

    where python >nul 2>&1
    if errorlevel 1 (
        echo  [X] Python bulunamadi.
        echo      https://www.python.org/downloads/ adresinden Python 3.11+
        echo      kurun ve "Add Python to PATH" secenegini isaretleyin.
        echo.
        pause
        exit /b 1
    )

    python -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo  [X] Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )

    echo  [*] Bagimliliklar kuruluyor...
    "%PYEXE%" -m pip install --upgrade pip --quiet
    "%PYEXE%" -m pip install -r "%~dp0backend\requirements.txt" --quiet
    if errorlevel 1 (
        echo  [X] Bagimliliklar kurulamadi.
        pause
        exit /b 1
    )
    "%PYEXE%" -m pip install pywebview --quiet
    echo  [+] Kurulum tamamlandi.
    echo.
)

REM --- .env kontrolu ---
if not exist "%~dp0.env" (
    echo  [*] Yapilandirma dosyasi olusturuluyor (.env)...
    copy /Y "%~dp0.env.example" "%~dp0.env" >nul
    "%PYEXE%" -c "import secrets,pathlib; p=pathlib.Path(r'%~dp0.env'); t=p.read_text(encoding='utf-8'); t=t.replace('CHANGE_ME_GENERATE_A_LONG_RANDOM_SECRET', secrets.token_urlsafe(64)); p.write_text(t, encoding='utf-8')"
    echo  [+] .env olusturuldu. Yonetici parolasini degistirmeyi unutmayin.
    echo.
)

REM --- Veritabani migration ---
echo  [*] Veritabani kontrol ediliyor...
pushd "%~dp0backend"
"%PYEXE%" -m alembic upgrade head >nul 2>&1
if errorlevel 1 (
    echo  [!] Migration uygulanamadi, program yine de baslatiliyor.
) else (
    echo  [+] Veritabani guncel.
)
popd
echo.

REM --- Arayuz derlemesi kontrolu ---
if not exist "%~dp0frontend\dist\index.html" (
    echo  [!] Arayuz derlemesi bulunamadi.
    echo      Derlemek icin: BUILD_FRONTEND.bat dosyasini calistirin.
    echo      Program simdilik API dokumantasyonu ile acilacak.
    echo.
)

REM --- Baslat ---
echo  [*] Program baslatiliyor...
echo.
"%PYEXE%" "%~dp0desktop\launcher.py"

if errorlevel 1 (
    echo.
    echo  [X] Program beklenmedik sekilde kapandi.
    echo      Ayrinti icin logs\application.log dosyasina bakin.
    pause
)

endlocal
