# LocalAiStudio — installation Windows (une seule fois)
# -Unattended : appele par l'installateur .exe (outils deja installes, aucune question)
# -SkipTextModel : ne telecharge pas le modele de texte Ollama
param([switch]$Unattended, [switch]$SkipTextModel)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "== LocalAiStudio : installation ==" -ForegroundColor Magenta

function Need($id, $cmd) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Host "Installation de $id..." -ForegroundColor Cyan
    winget install --id $id -e --accept-source-agreements --accept-package-agreements
  } else { Write-Host "$cmd deja present" -ForegroundColor DarkGray }
}

if (-not $Unattended) {
  Need "Python.Python.3.11" "python"
  Need "OpenJS.NodeJS.LTS" "node"
  Need "Git.Git" "git"
  Need "Ollama.Ollama" "ollama"
  if (-not (Get-Service -Name MongoDB -ErrorAction SilentlyContinue)) {
    Write-Host "Installation de MongoDB Community..." -ForegroundColor Cyan
    winget install --id MongoDB.Server -e --accept-source-agreements --accept-package-agreements
  }
}

# Refresh PATH for this session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User") + ";$env:LOCALAPPDATA\Programs\Ollama;$env:ProgramFiles\nodejs"

Write-Host "Backend : environnement Python..." -ForegroundColor Cyan
python -m venv backend\.venv
& backend\.venv\Scripts\python.exe -m pip install --upgrade pip
& backend\.venv\Scripts\python.exe -m pip install -r requirements-local.txt
# Moteurs payants de secours (facultatif) — ignore en cas d'echec
& backend\.venv\Scripts\python.exe -m pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ 2>$null

Write-Host "Interface : dependances..." -ForegroundColor Cyan
corepack enable
Set-Location frontend
yarn install
Set-Location ..

Write-Host "Modele de texte local (qwen2.5-coder:14b, ~9 Go)..." -ForegroundColor Cyan
if (-not $SkipTextModel) {
  Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  ollama pull qwen2.5-coder:14b
}

Write-Host ""
Write-Host "Installation terminee." -ForegroundColor Green
Write-Host "1) Installez ComfyUI Desktop : https://www.comfy.org/download"
Write-Host "2) Lancez download-models.ps1 pour les modeles photo/video"
Write-Host "3) Double-cliquez sur start-localaistudio.bat"
if (-not $Unattended) { Read-Host "Appuyez sur Entree pour fermer" }

# Raccourci "LocalAiStudio" sur le Bureau (lance start-localaistudio.bat)
try {
  $desk = [Environment]::GetFolderPath("Desktop")
  $ws = New-Object -ComObject WScript.Shell
  $lnk = $ws.CreateShortcut((Join-Path $desk "LocalAiStudio.lnk"))
  $lnk.TargetPath = Join-Path $PSScriptRoot "start-localaistudio.bat"
  $lnk.WorkingDirectory = $PSScriptRoot
  $lnk.IconLocation = "shell32.dll,13"
  $lnk.Save()
  Write-Host "Raccourci LocalAiStudio cree sur le Bureau." -ForegroundColor Green
} catch { Write-Host "Raccourci non cree : faites clic droit sur start-localaistudio.bat > Envoyer vers > Bureau." -ForegroundColor Yellow }
