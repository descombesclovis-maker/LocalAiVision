@echo off
REM Compile Installer-LocalAiStudio.exe (Inno Setup 6, gratuit). A lancer depuis le kit decompresse.
cd /d %~dp0
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo Installation d'Inno Setup 6...
  winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements
)
if not exist %ISCC% set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
%ISCC% LocalAiStudio.iss
if errorlevel 1 ( echo La compilation a echoue. & pause & exit /b 1 )
echo.
echo Installateur pret : %~dp0Output\Installer-LocalAiStudio.exe
explorer Output
pause
