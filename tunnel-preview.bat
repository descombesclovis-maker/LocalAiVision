@echo off
REM ======================================================================
REM  tunnel-preview.bat  —  SECURISE (V1-B)
REM
REM  AVERTISSEMENT DE SECURITE
REM  ------------------------
REM  Les versions precedentes de ce script ouvraient des tunnels Cloudflare
REM  publics SANS authentification, exposant directement Ollama et ComfyUI a
REM  quiconque sur Internet.  Ce comportement a ete retire.
REM
REM  Rappel : Ollama et ComfyUI n'ont pas d'authentification integree.
REM  Les exposer via un tunnel public = acces complet a vos modeles IA, a
REM  votre GPU et potentiellement a vos fichiers.  Ne rouvrez jamais un tunnel
REM  public sans ajouter une couche d'authentification (reverse proxy avec
REM  authentification, Cloudflare Access, etc.).
REM
REM  Ce script ne fait plus rien de dangereux.  Il explique la procedure
REM  securisee si vous avez vraiment besoin d'un acces distant.
REM ======================================================================

echo.
echo  ================================================================
echo   tunnel-preview.bat  —  acces distant SECURISE
echo  ================================================================
echo.
echo  Les moteurs locaux (Ollama, ComfyUI) n'ont pas d'authentification.
echo  Les exposer sur Internet sans protection est un risque de securite
echo  majeur : quiconque connait l'URL peut utiliser vos modeles IA et
echo  votre GPU, voire acceder a vos fichiers.
echo.
echo  Ce script a ete neutralise.  Les tunnels publics non authentifies
echo  ne sont plus ouverts automatiquement.
echo.
echo  --- Si vous avez reellement besoin d'un acces distant ---
echo.
echo  1.  Installez un reverse proxy (Caddy, nginx) avec authentification
echo      devant chaque moteur, OU configurez Cloudflare Access (Zero Trust)
echo      pour exiger une connexion authentifiee.
echo.
echo  2.  Ne jamais exposer un port directement (cloudflared tunnel --url
echo      http://localhost:11434) : cela contourne toute authentification.
echo.
echo  3.  L'application LocalAiStudio reste concue pour un usage 100 %% local.
echo      L'acces distant n'est ni teste ni supporte.
echo.
echo  --- moteurs locaux (interface loopback uniquement) ---
echo.
echo    Ollama  : http://127.0.0.1:11434
echo    ComfyUI : http://127.0.0.1:8188
echo.
pause
