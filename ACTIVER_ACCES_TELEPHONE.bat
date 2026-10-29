@echo off
setlocal EnableExtensions
title LocalAiWeb - Acces prive iPhone
echo.
echo ==========================================================
echo   LOCAL AIWEB - INSTALLATION PRIVEE IPHONE / ANDROID
echo ==========================================================
echo.
echo Votre PC doit rester allume, connecte a Internet, avec LocalAiVision ouvert.
echo Connexion HTTPS reservee a votre reseau prive Tailscale.
echo AUCUN port public, AUCUN Tailscale Funnel.
echo.
set "TS="
for /f "delims=" %%I in ('where tailscale.exe 2^>nul') do if not defined TS set "TS=%%I"
if not defined TS if exist "%ProgramFiles%\Tailscale\tailscale.exe" set "TS=%ProgramFiles%\Tailscale\tailscale.exe"
if not defined TS if exist "%ProgramFiles(x86)%\Tailscale\tailscale.exe" set "TS=%ProgramFiles(x86)%\Tailscale\tailscale.exe"
if not defined TS (
  echo [A INSTALLER] Tailscale pour Windows : https://tailscale.com/download/windows
  echo Installez-le, connectez-vous, puis relancez ce script.
  pause
  exit /b 1
)
powershell -NoProfile -Command "try { $r=Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/ping' -TimeoutSec 5; if($r.app -ne 'LocalVisionAI'){ exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo [ERREUR] Lancez LocalAiVision sur ce PC et laissez sa fenetre ouverte.
  echo Verification locale : http://127.0.0.1:3000/api/ping
  pause
  exit /b 1
)
"%TS%" status >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Connectez Tailscale sur ce PC avec votre compte.
  pause
  exit /b 1
)
echo.
echo IMPORTANT : les autres appareils autorises de votre reseau Tailscale
echo pourront acceder aux conversations, projets et fichiers de ce logiciel.
echo Utilisez un compte Tailscale prive avec des appareils de confiance.
echo.
choice /C ON /M "Activer HTTPS uniquement dans votre reseau prive (O/N)"
if errorlevel 2 exit /b 0
"%TS%" serve --bg 3000
if errorlevel 1 (
  echo.
  echo [ERREUR] Tailscale Serve ne s'est pas active.
  echo Autorisez les certificats HTTPS dans le panneau Tailscale si demande.
  echo Ne lancez jamais la commande "tailscale funnel" pour ce logiciel.
  pause
  exit /b 1
)
echo.
echo ================ VOTRE URL PRIVEE =======================
"%TS%" serve status
echo ==========================================================
echo.
echo SUR IPHONE :
echo 1. Installer Tailscale depuis l'App Store, connecter le meme compte.
echo 2. Activer Tailscale sur l'iPhone.
echo 3. Dans Safari, ouvrir l'URL HTTPS affichee ci-dessus
echo    en ajoutant /localaiweb a la fin.
echo 4. Partager ^> Sur l'ecran d'accueil ^> Ouvrir comme app web ^> Ajouter.
echo.
echo Au prochain lancement, LocalAiWeb charge automatiquement les
echo modifications de la version PC. Pas d'installation mobile a refaire.
echo.
echo Pour couper cet acces : "%TS%" serve reset
echo Pour continuer a distance : ne laissez pas Windows se mettre en veille.
pause
