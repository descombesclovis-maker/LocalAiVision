@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title LocalVisionAI 2.1

rem Reuse Python when available. No administrator permissions are needed.
py -3.11 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
    set "LVA_PY=py -3.11"
    goto :ready
)
py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
    set "LVA_PY=py -3"
    goto :ready
)
python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
    set "LVA_PY=python"
    goto :ready
)
if not defined LOCALVISIONAI_DATA set "LOCALVISIONAI_DATA=%LOCALAPPDATA%\LocalVisionAI"
if exist "%LOCALVISIONAI_DATA%\ComfyUI\python_embeded\python.exe" (
    "%LOCALVISIONAI_DATA%\ComfyUI\python_embeded\python.exe" "%~dp0local_app\launcher.py"
    goto :end
)
if exist "D:\IA LOCAL\ComfyUI\python_embeded\python.exe" (
    "D:\IA LOCAL\ComfyUI\python_embeded\python.exe" "%~dp0local_app\launcher.py"
    goto :end
)
echo Python 3.10 ou plus recent est necessaire pour cette version source.
echo Installe Python depuis https://www.python.org/downloads/windows/
echo puis relance ce fichier. Les anciens modeles sont conserves.
pause
exit /b 1

:ready
echo Ouverture de LocalVisionAI...
echo Les moteurs se preparent en arriere-plan, dans l'interface.
echo Si pywebview est absent, le navigateur local sert d'interface.
%LVA_PY% "%~dp0local_app\launcher.py"
:end
if errorlevel 1 (
    echo Consulte %%LOCALAPPDATA%%\LocalVisionAI\logs\startup.log
    pause
    exit /b 1
)
exit /b 0
