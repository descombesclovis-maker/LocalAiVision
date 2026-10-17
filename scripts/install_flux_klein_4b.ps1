param([string]$ComfyUIFolder = "")
$ErrorActionPreference = "Stop"
Write-Host "=== LocalAiWeb - Installation facultative FLUX.2 Klein 4B (FP8) ===" -ForegroundColor Cyan
Write-Host "Source : Black Forest Labs / Comfy-Org. Licence Apache 2.0."
Write-Host "Environ 12 Go a telecharger. La RTX 3060 12 Go peut necessiter du dechargement en RAM."
if (-not $ComfyUIFolder) {
  $ComfyUIFolder = Read-Host "Saisis le chemin du dossier ComfyUI existant (celui qui contient models)"
}
$ComfyUIFolder = $ComfyUIFolder.Trim('"').Trim()
$root = [IO.Path]::GetFullPath($ComfyUIFolder)
if (-not (Test-Path (Join-Path $root "models") -PathType Container)) {
  throw "Dossier ComfyUI invalide : le sous-dossier models est introuvable. Rien n'a ete modifie."
}
$confirmation = Read-Host "Installer 3 fichiers volumineux dans $root ? (taper OUI)"
if ($confirmation -ne "OUI") { Write-Host "Installation annulee."; exit 0 }
$files = @(
  @{
    Folder = "text_encoders"; Name = "qwen_3_4b.safetensors";
    Url = "https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors";
    MinBytes = 1000000000; Hash = ""
  },
  @{
    Folder = "diffusion_models"; Name = "flux-2-klein-4b-fp8.safetensors";
    Url = "https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/resolve/main/flux-2-klein-4b-fp8.safetensors";
    MinBytes = 3500000000; Hash = "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6"
  },
  @{
    Folder = "vae"; Name = "flux2-vae.safetensors";
    Url = "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors";
    MinBytes = 200000000; Hash = ""
  }
)
foreach ($item in $files) {
  $destFolder = Join-Path (Join-Path $root "models") $item.Folder
  New-Item -ItemType Directory -Force -Path $destFolder | Out-Null
  $dest = Join-Path $destFolder $item.Name
  if (Test-Path $dest) {
    $bytes = (Get-Item $dest).Length
    if ($bytes -ge $item.MinBytes) {
      if ($item.Hash) {
        $hash = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $item.Hash) { throw "Empreinte incorrecte pour $dest. Le fichier existant n'a pas ete remplace." }
      }
      Write-Host "Deja installe : $($item.Name)"
      continue
    }
  }
  $partial = "$dest.part"
  Write-Host "Telechargement : $($item.Name)" -ForegroundColor Yellow
  $args = @("-f", "-L", "--retry", "4", "--retry-delay", "5", "-C", "-", "-o", $partial, $item.Url)
  & curl.exe @args
  if ($LASTEXITCODE -ne 0) { throw "Telechargement interrompu. Le fichier .part est conserve pour reprise." }
  if ((Get-Item $partial).Length -lt $item.MinBytes) { throw "Fichier incomplet : $partial" }
  if ($item.Hash) {
    $hash = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $item.Hash) { throw "Empreinte SHA256 incorrecte pour $($item.Name). Refaire le telechargement." }
  }
  Move-Item -LiteralPath $partial -Destination $dest -Force
  Write-Host "Installe : $($item.Name)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Poids installes. Mets ComfyUI a jour, puis importe le workflow officiel Flux.2 Klein 4B Text to Image."
Write-Host "https://docs.comfy.org/tutorials/flux/flux-2-klein"
Write-Host "Exporte ensuite le workflow API et importe-le dans LocalAiVision avec un nom contenant Flux2 Klein T2I."
Write-Host "LocalAiWeb le detectera automatiquement au prochain demarrage (sinon SDXL reste utilise)."
