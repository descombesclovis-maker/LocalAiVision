@echo off
setlocal
cd /d "%~dp0"
rem Optional: source launcher also works in a browser without this package.
py -3.11 -m pip install pywebview
if errorlevel 1 (
    echo Installation non terminee. Le mode navigateur reste utilisable.
    echo Si tu utilises une autre version de Python, installe pywebview dans cette version.
    pause
    exit /b 1
)
echo Installation terminee. Lance START_LOCAL_AI.bat.
pause
