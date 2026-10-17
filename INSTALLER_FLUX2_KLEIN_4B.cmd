@echo off
setlocal
title LocalAiWeb - FLUX.2 Klein 4B
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_flux_klein_4b.ps1"
if errorlevel 1 (
  echo.
  echo Installation inachevee. Lis le message ci-dessus et relance si necessaire.
)
pause
