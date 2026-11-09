@echo off
REM Rend Ollama et ComfyUI joignables depuis la preview en ligne de LocalAiStudio (tunnels Cloudflare gratuits, sans compte).
REM Copiez les deux adresses https://....trycloudflare.com affichees dans Moteurs > Configurer.
where cloudflared >nul 2>nul || winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
start "Tunnel Ollama" cmd /k cloudflared tunnel --url http://localhost:11434 --http-host-header localhost:11434
start "Tunnel ComfyUI" cmd /k cloudflared tunnel --url http://localhost:8188
echo Deux fenetres se sont ouvertes : recopiez l'adresse https://....trycloudflare.com de chacune.
pause
