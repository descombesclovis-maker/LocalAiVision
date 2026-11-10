@echo off
cd /d "%~dp0"
echo Installation isolee LocalAiStudio V2-F : aucun modele ne sera telecharge.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build-parallel-edition.ps1" %*
set "RESULT=%ERRORLEVEL%"
if not "%LAS_NONINTERACTIVE%"=="1" pause
exit /b %RESULT%
