@echo off
setlocal
title LocalAiVision - Acces prive telephone
echo.
echo ============================================
echo  LOCAL AIVISION - ACCES TELEPHONE PRIVE
echo ============================================
echo.
echo Ce script rend LocalAiVision accessible SEULEMENT aux appareils
echo autorises de votre reseau prive Tailscale, via HTTPS.
echo Il ne publie PAS le service sur Internet (pas de Funnel).
echo.
where tailscale >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Installez d'abord Tailscale pour Windows :
  echo https://tailscale.com/download/windows
  pause
  exit /b 1
)
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:3000/api/ping' -TimeoutSec 4; if($r.StatusCode -ne 200){ exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo [ERREUR] Demarrez LocalAiVision sur ce PC avant d'activer l'acces.
  pause
  exit /b 1
)
tailscale status >nul
if errorlevel 1 (
  echo [ERREUR] Connectez Tailscale sur ce PC et sur le telephone.
  pause
  exit /b 1
)
echo.
echo Ce service donne acces aux conversations, projets et generations
echo sur ce PC. Ne le partagez qu'avec des appareils de confiance.
choice /C ON /M "Activer l'acces prive HTTPS maintenant ? (O=oui, N=non)"
if errorlevel 2 exit /b 0
tailscale serve --bg 3000
if errorlevel 1 (
  echo [ERREUR] La configuration a echoue.
  echo Verifiez votre connexion et l'activation HTTPS Tailscale.
  pause
  exit /b 1
)
echo.
echo Sur le telephone : connectez le MEME compte Tailscale,
echo ouvrez l'URL HTTPS affichee ci-dessous dans Safari ou Chrome.
echo Puis installer : Safari Partager ^> Sur l'ecran d'accueil.
tailscale serve status
echo.
echo Pour arreter l'acces : tailscale serve reset
pause
