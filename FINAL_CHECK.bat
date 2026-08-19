@echo off
REM ===========================================================================
REM  Yayin oncesi kapsamli kalite kontrolu
REM  Pre-release quality gate
REM ===========================================================================
cd /d "%~dp0"
title Kalite Kontrolu

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\final_check.ps1" %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% NEQ 0 (
    echo  Kontroller basarisiz oldu. Yukaridaki hatalari giderin.
) else (
    echo  Kontroller tamamlandi.
)
echo.
pause
exit /b %EXITCODE%
