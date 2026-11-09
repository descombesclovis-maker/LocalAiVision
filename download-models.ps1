# Telecharge les modeles ComfyUI par defaut (FLUX dev fp8 + Wan 2.2 TI2V 5B). Reprise automatique si interrompu.
param([string]$ModelsDir = "", [switch]$Optional, [switch]$Unattended)
$ErrorActionPreference = "Stop"
$models = if ($ModelsDir) { $ModelsDir } else { Read-Host "Chemin du dossier 'models' de ComfyUI (ex. C:\Users\vous\Documents\ComfyUI\models)" }
if ($Unattended) { New-Item -ItemType Directory -Force -Path $models | Out-Null }
if (-not (Test-Path $models)) { Write-Host "Dossier introuvable" -ForegroundColor Red; exit 1 }

$files = @(
  @{ url = "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"; dir = "checkpoints" },
  @{ url = "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"; dir = "diffusion_models" },
  @{ url = "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"; dir = "text_encoders" },
  @{ url = "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors"; dir = "vae" }
)
$optional = @(
  @{ url = "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors"; dir = "checkpoints" },
  @{ url = "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.5.safetensors"; dir = "checkpoints" },
  @{ url = "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors"; dir = "text_encoders" }
)
if ($Optional -or (-not $Unattended -and (Read-Host "Telecharger aussi les modeles optionnels (FLUX schnell, LTX-Video) ? o/N") -eq "o")) { $files += $optional }

foreach ($f in $files) {
  $target = Join-Path $models $f.dir
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  $name = Split-Path $f.url -Leaf
  Write-Host "-> $name" -ForegroundColor Cyan
  curl.exe -L -C - -o (Join-Path $target $name) $f.url
}
Write-Host "Modeles installes. Relancez ComfyUI puis testez dans LocalAiStudio > Moteurs." -ForegroundColor Green
if (-not $Unattended) { Read-Host "Entree pour fermer" }
