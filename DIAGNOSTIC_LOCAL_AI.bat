@echo off
setlocal
cd /d "%~dp0"
title LocalVisionAI - Diagnostic
echo ===== LocalVisionAI diagnostic =====
echo.
echo Python systeme:
where py
where python
echo.
echo Recherche Python embarque ComfyUI:
powershell -NoProfile -ExecutionPolicy Bypass -Command "$roots=@('%~dp0','%~dp0..','%USERPROFILE%\ComfyUI','D:\IA LOCAL'); foreach($r in $roots){if(Test-Path $r){Get-ChildItem -LiteralPath $r -Filter python.exe -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match 'python_embeded' } | Select-Object -First 5 -ExpandProperty FullName}}"
echo.
echo ComfyUI:
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8188/system_stats -TimeoutSec 3).Content}catch{echo ComfyUI non joignable}"
echo.
echo Interface:
powershell -NoProfile -ExecutionPolicy Bypass -Command "try{(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/api/health -TimeoutSec 3).Content}catch{echo LocalVisionAI non joignable}"
echo.
pause
