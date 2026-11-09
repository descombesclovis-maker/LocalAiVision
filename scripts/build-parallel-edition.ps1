# Builds a SEPARATE, corrected LocalAiStudio edition next to the installed one. Never overwrites the installed edition.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-parallel-edition.ps1
#
# - Copies only git-tracked files of this repository (no .env, .api_key, .boot_token, bench_runs, venv...).
# - Writes backend\.env once (existing user files in the target are never overwritten).
# - Python: copies an existing complete venv read-only (-CopyVenvFrom), then syncs requirements.txt.
# - Frontend: links the existing node_modules read-only (-CopyNodeModulesFrom), else runs yarn install.
# - Own launcher (start-localaistudio-v2e.bat) on loopback and on ports distinct from the installed edition.

param(
    [string]$Target = "$env:LOCALAPPDATA\LocalAiStudio-Editions\NextGen-V2E",
    [string]$DbName = "localaistudio_nextgen_original",
    [int]$BackendPort = 8011,
    [int]$FrontendPort = 3011,
    [string]$CopyVenvFrom = "$env:LOCALAPPDATA\LocalAiStudio-Editions\NextGen-Avant-Fusion\backend\.venv",
    [string]$CopyNodeModulesFrom = "$env:LOCALAPPDATA\LocalAiStudio-Editions\NextGen-Avant-Fusion\frontend\node_modules"
)

$ErrorActionPreference = "Stop"
$Src = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Target = [IO.Path]::GetFullPath($Target)
$Installed = [IO.Path]::GetFullPath("$env:LOCALAPPDATA\LocalAiStudio-Editions\NextGen-Avant-Fusion")

if ($Target.TrimEnd('\') -ieq $Installed.TrimEnd('\') -or $Target.TrimEnd('\') -ieq $Src.TrimEnd('\')) {
    throw "Refus : la cible doit etre distincte de l'edition installee et du depot."
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Write-Host "== Cible : $Target"

# 1. Tracked files only
$files = git -C $Src ls-files
$copied = 0
foreach ($f in $files) {
    $from = Join-Path $Src $f
    if (-not (Test-Path -LiteralPath $from -PathType Leaf)) { continue }
    $to = Join-Path $Target $f
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $to) | Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
    $copied++
}
Write-Host "== Fichiers suivis copies : $copied"

# 2. Backend configuration (created once, then preserved)
$envFile = Join-Path $Target "backend\.env"
if (-not (Test-Path $envFile)) {
    @(
        "MONGO_URL=mongodb://127.0.0.1:27017",
        "DB_NAME=$DbName",
        "CORS_ORIGINS=http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort",
        "APP_TZ=Europe/Paris"
    ) | Set-Content -Encoding ASCII -Path $envFile
    Write-Host "== backend\.env cree (DB_NAME=$DbName, CORS limite a la cible)"
} else {
    Write-Host "== backend\.env existant conserve"
}

# 3. Python environment
$py = Join-Path $Target "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    if (Test-Path "$CopyVenvFrom\Scripts\python.exe") {
        Write-Host "== Copie (lecture seule de la source) du venv existant"
        robocopy $CopyVenvFrom (Join-Path $Target "backend\.venv") /E /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy a echoue ($LASTEXITCODE)" }
    } else {
        py -3.11 -m venv (Join-Path $Target "backend\.venv")
    }
}
Write-Host "== Synchronisation de backend\requirements.txt"
& $py -m pip install -q -r (Join-Path $Target "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install a echoue ($LASTEXITCODE)" }

# 4. Frontend dependencies
$nm = Join-Path $Target "frontend\node_modules"
if (-not (Test-Path $nm)) {
    if (Test-Path $CopyNodeModulesFrom) {
        New-Item -ItemType Junction -Path $nm -Target $CopyNodeModulesFrom | Out-Null
        Write-Host "== node_modules : jonction vers l'existant (pas de telechargement)"
    } else {
        Push-Location (Join-Path $Target "frontend")
        try { yarn install --frozen-lockfile } finally { Pop-Location }
    }
}

# 5. Own launcher: loopback only, distinct ports, explicit API target for Vite
$launcher = Join-Path $Target "start-localaistudio-v2e.bat"
@"
@echo off
title LocalAiStudio NextGen V2-E
cd /d %~dp0
echo == LocalAiStudio NextGen V2-E : demarrage (backend $BackendPort, interface $FrontendPort) ==
for /f "delims=" %%t in ('powershell -NoProfile -Command "[System.Guid]::NewGuid().ToString('N') + [System.Guid]::NewGuid().ToString('N')"') do set LAS_BOOT_TOKEN=%%t
net start MongoDB >nul 2>&1
set DISABLE_VISUAL_EDITS=true
set DISABLE_EMERGENT_OVERLAY=true
set DISABLE_HOT_RELOAD=true
set LAS_API_TARGET=http://127.0.0.1:$BackendPort
set LAS_SESSION_COOKIE=las_session_v2e
start "LAS V2-E backend" /min cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port $BackendPort"
start "LAS V2-E interface" /min cmd /k "cd frontend && yarn dev --host 127.0.0.1 --port $FrontendPort --strictPort"
timeout /t 8 >nul
start http://127.0.0.1:$FrontendPort/
echo Interface : http://127.0.0.1:$FrontendPort  (fermez les fenetres pour arreter)
"@ | Set-Content -Encoding ASCII -Path $launcher

# 6. Release marker
$rev = (git -C $Src rev-parse --short HEAD).Trim()
Set-Content -Encoding ASCII -Path (Join-Path $Target ".localai-edition-release") -Value "NextGen-V2E $rev $(Get-Date -Format s)"
Write-Host "== Build termine : $Target (commit $rev)"
Write-Host "== Lancer : $launcher"
