@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build LocalVisionAI

where py >nul 2>&1
if errorlevel 1 (
  echo Python 3.11+ est requis pour construire LocalVisionAI.
  pause
  exit /b 1
)

py -3.11 -m pip install --upgrade pyinstaller pywebview
if errorlevel 1 goto FAIL

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --name LocalVisionAI ^
  --collect-all webview ^
  --hidden-import local_app ^
  --hidden-import local_app.bootstrap_windows ^
  --hidden-import local_app.server ^
  --hidden-import local_app.llm ^
  --hidden-import local_app.workflows ^
  --add-data "local_app\web;local_app\web" ^
  --add-data "local_app\bootstrap_windows.py;local_app" ^
  --add-data "local_app\server.py;local_app" ^
  --add-data "local_app\llm.py;local_app" ^
  --add-data "local_app\__init__.py;local_app" ^
  --add-data "Text to image flux.json;." ^
  --add-data "text to image sdxl.json;." ^
  --add-data "Image to video wan.json;." ^
  --add-data "Text_to_Video_LTX.json;." ^
  --add-data "Retouche SDXL masque.json;." ^
  --add-data "Video Wan texte.json;." ^
  local_app\launcher.py

if errorlevel 1 goto FAIL

if not exist "dist\LocalVisionAI.exe" goto FAIL

echo.
echo ==========================================
echo BUILD TERMINE AVEC SUCCES
echo ==========================================
echo.
echo EXE cree :
echo %CD%\dist\LocalVisionAI.exe
echo.

rem Resolve the real Windows Desktop location (also works with OneDrive).
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"

if defined DESKTOP if exist "%DESKTOP%" (
  copy /y "dist\LocalVisionAI.exe" "%DESKTOP%\LocalVisionAI.exe" >nul
  if not errorlevel 1 (
    echo Copie sur le Bureau :
    echo %DESKTOP%\LocalVisionAI.exe
  ) else (
    echo Copie Bureau impossible.
    echo Utilise directement :
    echo %CD%\dist\LocalVisionAI.exe
  )
) else (
  echo Bureau Windows introuvable.
  echo Utilise directement :
  echo %CD%\dist\LocalVisionAI.exe
)

echo.
echo ATTENTION : lance uniquement LocalVisionAI.exe.
echo Aucun navigateur ne doit etre necessaire.
echo.
pause
exit /b 0

:FAIL
echo.
echo ==========================================
echo ECHEC DE CONSTRUCTION
echo ==========================================
echo.
echo Consulte les messages ci-dessus.
pause
exit /b 1
