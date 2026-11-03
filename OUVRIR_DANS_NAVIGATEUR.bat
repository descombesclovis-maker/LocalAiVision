@echo off
setlocal
title LocalAI Studio - Mode navigateur
if not exist "%~dp0LocalVisionAI.exe" (
  echo Erreur : LocalVisionAI.exe est absent du dossier extrait.
  echo Extrais tout le ZIP avant de relancer ce fichier.
  pause
  exit /b 1
)
set "LOCALVISIONAI_BROWSER_ONLY=1"
echo Lancement de LocalAI Studio dans ton navigateur...
echo Adresse locale : http://127.0.0.1:3000/studio
echo.
echo Si rien ne s'ouvre, consulte :
echo %%LOCALAPPDATA%%\LocalVisionAI\logs\startup.log
echo.
start "" /wait "%~dp0LocalVisionAI.exe"
echo.
echo Le programme s'est termine. Consulte le journal si le navigateur ne s'est pas ouvert.
pause
