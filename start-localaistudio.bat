@echo off
title LocalAiStudio
cd /d %~dp0
echo == LocalAiStudio : demarrage ==
REM Generate one-time bootstrap token for secure session initialization (V1-B.2)
for /f "delims=" %%t in ('powershell -NoProfile -Command "[System.Guid]::NewGuid().ToString('N') + [System.Guid]::NewGuid().ToString('N')"') do set LAS_BOOT_TOKEN=%%t
net start MongoDB >nul 2>&1
start "Ollama" /min cmd /c "ollama serve"
set DISABLE_VISUAL_EDITS=true
set DISABLE_EMERGENT_OVERLAY=true
set DISABLE_HOT_RELOAD=true
start "LocalAiStudio backend" /min cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001"
start "LocalAiStudio interface" /min cmd /k "cd frontend && yarn dev --host 127.0.0.1 --port 3000"
timeout /t 8 >nul
start http://localhost:3000
echo LocalAiStudio tourne sur http://localhost:3000 (fermez les fenetres pour l'arreter).
echo Pensez a lancer ComfyUI pour les photos et videos.
