# Create a NEW, independent Windows edition from the reviewed source manifest.
# Never updates an existing edition, reads its environments, downloads models, or migrates data.
# Prerequisites: Windows x64, Python 3.11 x64, Node >=20.19 / >=22.12, npm; MongoDB for first launch.
# Example: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-parallel-edition.ps1
param(
    [string]$Target = "$env:LOCALAPPDATA\LocalAiStudio-Editions\NextGen-V2F",
    [int]$BackendPort = 8012,
    [int]$FrontendPort = 3012
)

$ErrorActionPreference = "Stop"
$Src = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Target = [IO.Path]::GetFullPath($Target)
if ($BackendPort -lt 1 -or $BackendPort -gt 65535 -or $FrontendPort -lt 1 -or $FrontendPort -gt 65535 -or $BackendPort -eq $FrontendPort) {
    throw "Ports invalides ou identiques."
}

function Invoke-Checked([string]$Program, [string[]]$ArgumentList) {
    & $Program @ArgumentList
    if ($LASTEXITCODE -ne 0) { throw "Echec de $Program (code $LASTEXITCODE). Le dossier partiel est conserve." }
}

$pyLauncher = (Get-Command py.exe -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
Invoke-Checked $pyLauncher @("-3.11", "-c", "import sys,struct; assert sys.version_info[:2] == (3,11) and struct.calcsize('P') == 8")
$nodeText = (& $node --version).Trim()
if ($LASTEXITCODE -ne 0) { throw "Impossible de lire la version de Node.js." }
$version = [Version]($nodeText.TrimStart('v'))
$nodeOK = ($version.Major -eq 20 -and $version.Minor -ge 19) -or ($version.Major -eq 22 -and $version.Minor -ge 12) -or ($version.Major -ge 23)
if (-not $nodeOK) { throw "Node.js 20.19+ ou 22.12+ requis (actuel : $nodeText)." }

Write-Host "== Cible neuve : $Target"
# materialize_kit refuses existing targets, links/junctions and source/edition overlap.
Invoke-Checked $pyLauncher @("-3.11", (Join-Path $Src "scripts\materialize_kit.py"), $Src, $Target)

Write-Host "== Creation d'un environnement Python propre"
Invoke-Checked $pyLauncher @("-3.11", "-m", "venv", (Join-Path $Target "backend\.venv"))
$py = Join-Path $Target "backend\.venv\Scripts\python.exe"
Invoke-Checked $py @("-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", (Join-Path $Target "requirements-windows-py311.lock"))
Invoke-Checked $py @("-m", "pip", "check")

Write-Host "== Yarn local verrouille et installation frontend propre"
Push-Location (Join-Path $Target "installer\tooling")
try { Invoke-Checked $npm @("ci", "--ignore-scripts", "--no-audit", "--no-fund") } finally { Pop-Location }
$yarn = Join-Path $Target "installer\tooling\node_modules\yarn\bin\yarn.js"
if (-not (Test-Path -LiteralPath $yarn -PathType Leaf)) { throw "Yarn local absent." }
$env:DISABLE_VISUAL_EDITS = "true"
$env:DISABLE_EMERGENT_OVERLAY = "true"
$env:DISABLE_HOT_RELOAD = "true"
$env:LAS_VITE_EXPOSE = $null
Push-Location (Join-Path $Target "frontend")
try {
    Invoke-Checked $node @($yarn, "install", "--frozen-lockfile", "--non-interactive")
    Invoke-Checked $node @($yarn, "build")
} finally { Pop-Location }

# A random name is claimed only on first launch after checking that it does not exist.
$nonce = (& $py -c "import secrets; print(secrets.token_hex(10))").Trim()
if ($LASTEXITCODE -ne 0 -or $nonce -notmatch '^[0-9a-f]{20}$') { throw "Impossible de creer l'identifiant de l'edition." }
$dbName = "las_v2f_$nonce"
$cookie = "las_session_v2f_$nonce"
$origins = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort"
@(
    "MONGO_URL=mongodb://127.0.0.1:27017",
    "DB_NAME=$dbName",
    "CORS_ORIGINS=$origins",
    "APP_TZ=Europe/Paris"
) | Set-Content -Encoding ASCII -Path (Join-Path $Target "backend\.env")

# Launch never starts or changes shared Ollama/ComfyUI/MongoDB services.
$launcher = Join-Path $Target "start-localaistudio-v2f.bat"
@"
@echo off
setlocal
title LocalAiStudio NextGen V2-F
cd /d "%~dp0"
echo == LocalAiStudio V2-F : backend $BackendPort, interface $FrontendPort ==
set "MONGO_URL=mongodb://127.0.0.1:27017"
set "DB_NAME=$dbName"
set "CORS_ORIGINS=$origins"
set "LAS_SESSION_COOKIE=$cookie"
set "LAS_API_TARGET=http://127.0.0.1:$BackendPort"
set "LAS_VITE_EXPOSE="
set "DISABLE_VISUAL_EDITS=true"
set "DISABLE_EMERGENT_OVERLAY=true"
set "DISABLE_HOT_RELOAD=true"
backend\.venv\Scripts\python.exe -c "import socket,sys; s=[socket.socket() for _ in sys.argv[1:]]; [x.bind(('127.0.0.1',int(p))) for x,p in zip(s,sys.argv[1:])]" $BackendPort $FrontendPort >nul 2>&1
if errorlevel 1 (echo Ports deja utilises. Aucune instance demarree. & exit /b 1)
backend\.venv\Scripts\python.exe scripts\check_new_db.py backend\.database-owner
if errorlevel 1 (echo Demarrez MongoDB et verifiez la configuration. Aucune base utilisateur ne sera adoptee. & exit /b 1)
set "LAS_BOOT_TOKEN="
for /f "delims=" %%t in ('backend\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"') do set LAS_BOOT_TOKEN=%%t
if not defined LAS_BOOT_TOKEN (echo Generation du jeton impossible. & exit /b 1)
start "LAS V2-F backend" /min cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port $BackendPort"
start "LAS V2-F interface" /min cmd /k "cd frontend && node ..\installer\tooling\node_modules\yarn\bin\yarn.js dev --host 127.0.0.1 --port $FrontendPort --strictPort"
backend\.venv\Scripts\python.exe scripts\wait_for_server.py $BackendPort $FrontendPort
if errorlevel 1 (echo Demarrage incomplet : verifiez les deux fenetres de service. & exit /b 1)
if not "%LAS_SKIP_BROWSER%"=="1" start "" "http://127.0.0.1:$FrontendPort/"
echo Interface : http://127.0.0.1:$FrontendPort. Lancez Ollama et ComfyUI separement.
"@ | Set-Content -Encoding ASCII -Path $launcher

$revision = "kit-sans-git"
$dirty = $null
if ((Get-Command git.exe -ErrorAction SilentlyContinue) -and (Test-Path (Join-Path $Src ".git"))) {
    $revision = (& git.exe -C $Src rev-parse HEAD).Trim()
    $dirty = [bool](@(& git.exe -C $Src status --porcelain).Count)
}
@{
    source = $revision; working_tree_dirty = $dirty; python = "3.11 x64"; node = $nodeText
    runtime_sha256 = (Get-FileHash (Join-Path $Target "requirements-windows-py311.lock") -Algorithm SHA256).Hash
    frontend_sha256 = (Get-FileHash (Join-Path $Target "frontend\yarn.lock") -Algorithm SHA256).Hash
    yarn_tool_sha256 = (Get-FileHash (Join-Path $Target "installer\tooling\package-lock.json") -Algorithm SHA256).Hash
    created_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Encoding UTF8 -Path (Join-Path $Target ".localai-edition-release.json")
Write-Host "== Termine : $Target"
Write-Host "== Base nouvelle : $dbName (aucune migration)"
Write-Host "== Lanceur : $launcher"
