import os, subprocess, urllib.request, urllib.error, json, zipfile, shutil, hashlib, sys, threading
from pathlib import Path

DATA = Path(os.environ.get("LOCALVISIONAI_DATA", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "LocalVisionAI")))
ENGINE = DATA / "ComfyUI"
LLAMA = DATA / "llama"
MODEL_DIR = DATA / "models"
COMFY_URL = "https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z"
LLAMA_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
LLAMA_RELEASES_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20"
MODEL_URL = "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf?download=true"
MODEL_NAME = "Qwen3-8B-Q4_K_M.gguf"
PROGRESS = None
_DOWNLOAD_LOCKS = {}
_DOWNLOAD_LOCKS_GUARD = threading.Lock()
OMNIWEAVING_COMFY_COMMIT = "a9fd2c7416c047566591b42663d64b8239456224"
OMNIWEAVING_COMFY_ARCHIVE = (
    "https://github.com/Shiba-2-shiba/hy_omniweaving_comfyui_unofficial/archive/"
    + OMNIWEAVING_COMFY_COMMIT + ".zip"
)


def _download_lock(dest):
    key = str(Path(dest).resolve()).lower()
    with _DOWNLOAD_LOCKS_GUARD:
        return _DOWNLOAD_LOCKS.setdefault(key, threading.Lock())


def _download_unlocked(url, dest, label, min_bytes=1024):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[LocalVisionAI] {label}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    offset = tmp.stat().st_size if tmp.exists() else 0
    headers = {"User-Agent": "LocalVisionAI/2.1"}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    req = urllib.request.Request(url, headers=headers)
    if PROGRESS:
        PROGRESS(label + " — connexion au serveur…")
    try:
        src = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code != 416 or not offset:
            raise
        # A stale partial file may exceed the remote size. Start fresh once.
        tmp.unlink()
        return _download_unlocked(url, dest, label, min_bytes)
    with src:
        append = offset > 0 and src.status == 206
        if append and not src.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
            raise RuntimeError('Le serveur a renvoyé une plage de téléchargement incorrecte.')
        if not append:
            offset = 0
        remaining = int(src.headers.get('Content-Length') or 0)
        if remaining and shutil.disk_usage(dest.parent).free < remaining + 512 * 1024**2:
            raise RuntimeError('Espace disque insuffisant pour télécharger ' + dest.name)
        done = 0
        with tmp.open('ab' if append else 'wb') as out:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if PROGRESS:
                    total = offset + remaining
                    PROGRESS(label + (f' — {(offset + done) * 100 // total} %' if total else f' — {(offset + done) // 1024**2} Mo'))
        if remaining and done != remaining:
            raise RuntimeError('Téléchargement interrompu ; Réessayer reprendra le fichier partiel.')
    if tmp.stat().st_size < min_bytes:
        raise RuntimeError('Téléchargement incomplet : ' + dest.name)
    tmp.replace(dest)


def _download(url, dest, label, min_bytes=1024):
    # Downloads may be triggered both by the startup model lab and by a user
    # selecting a workflow. Lock only the destination file so unrelated models
    # can still download independently without corrupting .part files.
    with _download_lock(dest):
        return _download_unlocked(url, dest, label, min_bytes)


def ensure_comfy():
    from local_app import server
    if any(server._comfy_command(root)[0] for root in server._candidate_comfy_roots()):
        return True
    DATA.mkdir(parents=True, exist_ok=True)
    archive = DATA / "ComfyUI_windows_portable_nvidia.7z"
    req = urllib.request.Request('https://api.github.com/repos/Comfy-Org/ComfyUI/releases/latest', headers={'User-Agent':'LocalVisionAI/2.1'})
    with urllib.request.urlopen(req, timeout=30) as response:
        release = json.load(response)
    choices = [a for a in release.get('assets', []) if 'windows_portable_nvidia' in a.get('name', '').lower() and a['name'].endswith('.7z')]
    if not choices:
        raise RuntimeError('Paquet portable NVIDIA introuvable dans la dernière version de ComfyUI.')
    # Prefer CUDA 12.6 when published, then the standard NVIDIA package.
    choices.sort(key=lambda a: (0 if 'cu126' in a['name'] else 1 if a['name']=='ComfyUI_windows_portable_nvidia.7z' else 2, a['name']))
    asset=choices[0]
    archive = DATA / asset['name']
    _download(asset['browser_download_url'], archive, "Téléchargement du moteur graphique ComfyUI…", min_bytes=int(asset.get('size') or 1024))
    target = DATA / "_extract_comfy"
    if target.exists(): shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    print("[LocalVisionAI] Extraction de ComfyUI…")
    commands = [["tar", "-xf", str(archive), "-C", str(target)]]
    seven = shutil.which("7z") or shutil.which("7za")
    if not seven:
        for candidate in (Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / '7-Zip/7z.exe', Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / '7-Zip/7z.exe'):
            if candidate.is_file():
                seven = str(candidate)
                break
    if seven:
        commands.insert(0, [seven, "x", "-y", f"-o{target}", str(archive)])
    errors = []
    ok = False
    for cmd in commands:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                ok = True; break
            errors.append((r.stderr or r.stdout or str(r.returncode))[-1200:])
        except Exception as exc:
            errors.append(str(exc))
    if not ok:
        raise RuntimeError("Impossible d'extraire ComfyUI automatiquement. " + " | ".join(errors))
    candidates = list(target.rglob("run_nvidia_gpu.bat"))
    if not candidates:
        raise RuntimeError("Le paquet ComfyUI téléchargé ne contient pas le lanceur NVIDIA attendu.")
    source = candidates[0].parent
    # Repair engine files without deleting existing models, inputs or outputs.
    shutil.copytree(source, ENGINE, dirs_exist_ok=True)
    try: archive.unlink()
    except Exception: pass
    shutil.rmtree(target, ignore_errors=True)
    return True


def _llama_bundle():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "LocalVisionAI/2.1"}

    def select(release):
        assets = release.get("assets") or []
        def asset_matching(test):
            return next((a for a in assets if test(a.get("name", "").lower()) and a.get("browser_download_url")), None)
        # NVIDIA first. The companion CUDART archive is published separately.
        main = asset_matching(lambda n: n.startswith("llama-") and "-bin-win-cuda-12.4-x64.zip" in n and not n.startswith("cudart-"))
        runtime = asset_matching(lambda n: n == "cudart-llama-bin-win-cuda-12.4-x64.zip")
        if main and runtime:
            return "cuda", [main, runtime]
        # Vulkan remains a GPU-accelerated fallback without an extra runtime.
        main = asset_matching(lambda n: n.startswith("llama-") and "-bin-win-vulkan-x64.zip" in n)
        if main:
            return "vulkan", [main]
        main = asset_matching(lambda n: n.startswith("llama-") and (n.endswith("bin-win-cpu-x64.zip") or n.endswith("win-cpu-x64.zip")))
        if main:
            return "cpu", [main]
        return None

    errors = []
    try:
        req = urllib.request.Request(LLAMA_RELEASES_API, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            releases = json.loads(r.read().decode("utf-8"))
        if isinstance(releases, list):
            # Prefer the first recent release that contains a complete GPU bundle.
            cpu_fallback = None
            for release in releases:
                if release.get("draft"):
                    continue
                picked = select(release)
                if not picked:
                    continue
                backend, bundle = picked
                if backend != "cpu":
                    print(f"[LocalVisionAI] llama.cpp sélectionné : {release.get('tag_name', '?')} / {backend.upper()}", flush=True)
                    return backend, bundle
                if cpu_fallback is None:
                    cpu_fallback = (backend, bundle, release.get('tag_name', '?'))
            if cpu_fallback:
                backend, bundle, tag = cpu_fallback
                print(f"[LocalVisionAI] llama.cpp sélectionné : {tag} / CPU", flush=True)
                return backend, bundle
    except Exception as exc:
        errors.append("liste des versions: " + str(exc))

    try:
        req = urllib.request.Request(LLAMA_API, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            release = json.loads(r.read().decode("utf-8"))
        picked = select(release) if isinstance(release, dict) else None
        if picked:
            return picked
    except Exception as exc:
        errors.append("dernière version stable: " + str(exc))

    detail = (" (" + " | ".join(errors) + ")") if errors else ""
    raise RuntimeError("Binaire llama.cpp Windows x64 introuvable dans les versions récentes de GitHub." + detail)


def _installed_llama_backend():
    if not LLAMA.exists() or not list(LLAMA.rglob("llama-server.exe")):
        return None
    if list(LLAMA.rglob("ggml-cuda.dll")):
        return "cuda"
    if list(LLAMA.rglob("ggml-vulkan.dll")):
        return "vulkan"
    return "cpu"


def ensure_llama():
    existing_backend = _installed_llama_backend()
    # A GPU backend is already suitable. CPU-only installs from older versions
    # are deliberately upgraded so the chat does not spend tens of seconds on
    # simple answers when an NVIDIA/Vulkan GPU is available.
    if existing_backend in ("cuda", "vulkan"):
        return True
    LLAMA.mkdir(parents=True, exist_ok=True)
    backend, assets = _llama_bundle()
    extract = DATA / "_extract_llama"
    if extract.exists(): shutil.rmtree(extract, ignore_errors=True)
    extract.mkdir(parents=True, exist_ok=True)
    archives = []
    for asset in assets:
        archive = DATA / asset["name"]
        _download(asset["browser_download_url"], archive, "Téléchargement de llama.cpp " + backend.upper() + " pour l'IA texte…", min_bytes=max(1024, int(asset.get("size") or 1024)))
        archives.append(archive)
        with zipfile.ZipFile(archive) as z:
            z.extractall(extract)
    server = next(extract.rglob("llama-server.exe"), None)
    if not server:
        raise RuntimeError("llama.cpp a été téléchargé mais llama-server.exe est introuvable.")
    # Build the replacement completely before touching the working installation.
    staged = DATA / "_llama_ready"
    if staged.exists(): shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir(parents=True, exist_ok=True)
    # CUDA runtime DLLs may be extracted at archive root while binaries live in a subfolder.
    for item in extract.rglob('*'):
        if item.is_file():
            shutil.copy2(item, staged / item.name)
    if not (staged / "llama-server.exe").exists():
        shutil.copy2(server, staged / "llama-server.exe")
    (staged / "localvision-backend.txt").write_text(backend, encoding="utf-8")
    if LLAMA.exists(): shutil.rmtree(LLAMA, ignore_errors=True)
    shutil.move(str(staged), str(LLAMA))
    shutil.rmtree(extract, ignore_errors=True)
    for archive in archives:
        try: archive.unlink()
        except Exception: pass
    return True

def ensure_model():
    preferred = os.environ.get('LOCALVISIONAI_LLM_MODEL')
    if preferred and Path(preferred).is_file():
        return True
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # Preserve a user's existing alternative GGUF model.
    if any(p.name != MODEL_NAME and p.stat().st_size > 1024**2 for p in MODEL_DIR.rglob('*.gguf')):
        return True
    model = MODEL_DIR / MODEL_NAME
    if model.exists() and model.stat().st_size > 4_500_000_000:
        return True
    _download(MODEL_URL, model, "Téléchargement du modèle conversationnel Qwen3 8B Q4… (~5 Go)", min_bytes=4_500_000_000)
    if model.stat().st_size < 4_500_000_000:
        raise RuntimeError("Le modèle GGUF téléchargé est incomplet.")
    return True


def run():
    DATA.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(DATA).free
    if free < 12 * 1024 * 1024 * 1024:
        raise RuntimeError("Espace disque insuffisant : au moins 12 Go libres sont nécessaires pour l’installation initiale.")
    ensure_comfy()
    ensure_llama()
    ensure_model()
    return True

if __name__ == "__main__":
    try:
        run()
        print("[LocalVisionAI] Installation locale prête.")
    except Exception as exc:
        print(f"[LocalVisionAI] ERREUR: {exc}")
        raise


MEDIA_MODELS = {
    'image': [
        ('checkpoints', 'RealVisXL_V5.0_fp16.safetensors',
         'https://huggingface.co/SG161222/RealVisXL_V5.0/resolve/main/RealVisXL_V5.0_fp16.safetensors?download=true')
    ],
    'video': [
        ('diffusion_models', 'wan2.1_t2v_1.3B_fp16.safetensors',
         'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors'),
        ('vae', 'wan_2.1_vae.safetensors',
         'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors'),
        ('text_encoders', 'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
         'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors')
    ],
    'isolated-image': [
        ('diffusion_models', 'hunyuanimage2.1_distilled_fp8_e4m3fn.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanImage_2.1_ComfyUI/resolve/main/split_files/diffusion_models/hunyuanimage2.1_distilled_fp8_e4m3fn.safetensors'),
        ('text_encoders', 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanImage_2.1_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors'),
        ('text_encoders', 'byt5_small_glyphxl_fp16.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanImage_2.1_ComfyUI/resolve/main/split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors'),
        ('vae', 'hunyuan_image_2.1_vae_fp16.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanImage_2.1_ComfyUI/resolve/main/split_files/vae/hunyuan_image_2.1_vae_fp16.safetensors')
    ],
    'isolated-video': [
        ('diffusion_models', 'hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors',
         'https://huggingface.co/Shiba-2-shiba/HY-OmniWeaving_HunyuanVideo_1.5_FP8_Patched/resolve/main/hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors?download=true'),
        ('text_encoders', 'qwen_2.5_vl_7b_finetuned_model.safetensors',
         'https://huggingface.co/tencent/HY-OmniWeaving/resolve/main/text_encoder/ckpt/text_encoder_model.safetensors?download=true'),
        ('text_encoders', 'byt5_small_glyphxl_fp16.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors'),
        ('vae', 'hunyuanvideo15_vae_fp32.safetensors',
         'https://huggingface.co/vafipas663/HY-OmniWeaving_repackaged/resolve/main/split_files/vae/hunyuanvideo15_vae_fp32.safetensors?download=true')
    ],
    'isolated-video-i2v': [
        ('diffusion_models', 'hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors',
         'https://huggingface.co/Shiba-2-shiba/HY-OmniWeaving_HunyuanVideo_1.5_FP8_Patched/resolve/main/hy_omniweaving_hunyuanvideo15_transformer_fp8_e4m3fn_patched.safetensors?download=true'),
        ('text_encoders', 'qwen_2.5_vl_7b_finetuned_model.safetensors',
         'https://huggingface.co/tencent/HY-OmniWeaving/resolve/main/text_encoder/ckpt/text_encoder_model.safetensors?download=true'),
        ('text_encoders', 'byt5_small_glyphxl_fp16.safetensors',
         'https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/resolve/main/split_files/text_encoders/byt5_small_glyphxl_fp16.safetensors'),
        ('vae', 'hunyuanvideo15_vae_fp32.safetensors',
         'https://huggingface.co/vafipas663/HY-OmniWeaving_repackaged/resolve/main/split_files/vae/hunyuanvideo15_vae_fp32.safetensors?download=true'),
        ('clip_vision', 'image_encoder.safetensors',
         'https://huggingface.co/Runware/Flex-Redux/resolve/main/image_encoder/model.safetensors?download=true'),
        ('clip_vision', 'image_embedder.safetensors',
         'https://huggingface.co/Runware/Flex-Redux/resolve/main/image_embedder/diffusion_pytorch_model.safetensors?download=true')
    ],
}


OBSOLETE_APP_MODELS = {
    'checkpoints': {
        'animagine-xl-4.0-opt.safetensors',
        'Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors',
        'epicrealismXL_vx1Finalkiss.safetensors',
    },
    'diffusion_models': {
        'wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors',
        'hunyuanvideo1.5_480p_t2v_cfg_distilled_fp8_scaled.safetensors',
        'hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.safetensors',
        'wan2.1_vace_1.3B_fp16.safetensors',
        'wan2.2_ti2v_5B_fp16.safetensors',
        'ltx-2.3-22b-dev-fp8.safetensors',
        'flux1-schnell-fp8.safetensors',
    },
    'vae': {
        'wan2.2_vae.safetensors',
        'hunyuanvideo15_vae_fp16.safetensors',
    },
    'clip_vision': {
        'clip_vision_h.safetensors',
        'sigclip_vision_patch14_384.safetensors',
    },
}


def _media_model_dir(create_engine=False):
    from local_app import server
    root = next((r for r in server._candidate_comfy_roots() if server._comfy_command(r)[0]), None)
    if root is None and create_engine:
        ensure_comfy()
        root = ENGINE
    if root is None:
        return None
    return (root / 'ComfyUI/models') if (root / 'ComfyUI/main.py').exists() else root / 'models'


def _omniweaving_extension_dir(create_engine=False):
    model_dir = _media_model_dir(create_engine)
    return (model_dir.parent / 'custom_nodes' / 'hy_omniweaving_comfyui_unofficial') if model_dir else None


def omniweaving_extension_status():
    target = _omniweaving_extension_dir(False)
    return bool(target and (target / 'nodes.py').is_file())


def ensure_omniweaving_extension():
    target = _omniweaving_extension_dir(True)
    if target is None:
        raise RuntimeError('Installation ComfyUI introuvable pour OmniWeaving.')
    marker = target / '.localvision_commit'
    if (target / 'nodes.py').is_file():
        if not marker.exists():
            # Respect an extension installed manually by the user.
            return True
        if marker.read_text(encoding='utf-8', errors='ignore').strip() == OMNIWEAVING_COMFY_COMMIT:
            return True

    archive = DATA / ('hy_omniweaving_comfyui_' + OMNIWEAVING_COMFY_COMMIT[:8] + '.zip')
    _download(OMNIWEAVING_COMFY_ARCHIVE, archive, 'Téléchargement du pont ComfyUI HY-OmniWeaving…', min_bytes=10_000)
    extract = DATA / '_extract_omniweaving'
    if extract.exists():
        shutil.rmtree(extract, ignore_errors=True)
    extract.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        z.extractall(extract)
    source = next((p for p in extract.iterdir() if p.is_dir() and p.name.startswith('hy_omniweaving_comfyui_unofficial-')), None)
    if source is None or not (source / 'nodes.py').is_file():
        raise RuntimeError('Extension HY-OmniWeaving téléchargée mais contenu invalide.')
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    marker.write_text(OMNIWEAVING_COMFY_COMMIT, encoding='utf-8')
    shutil.rmtree(extract, ignore_errors=True)
    try:
        archive.unlink()
    except OSError:
        pass
    return True


def cleanup_obsolete_media():
    """Remove only legacy model files installed by older LocalVisionAI builds."""
    model_dir = _media_model_dir(False)
    removed = []
    if model_dir is None:
        return removed
    for folder, names in OBSOLETE_APP_MODELS.items():
        for name in names:
            path = model_dir / folder / name
            try:
                if path.is_file():
                    path.unlink()
                    removed.append(str(path))
                part = path.with_suffix(path.suffix + '.part')
                if part.is_file():
                    part.unlink()
            except OSError:
                pass
    return removed


def media_status(component):
    if component not in MEDIA_MODELS:
        raise ValueError('Composant inconnu')
    model_dir = _media_model_dir(False)
    files = []
    for folder, name, _url in MEDIA_MODELS[component]:
        path = model_dir / folder / name if model_dir else None
        size = path.stat().st_size if path and path.is_file() else 0
        files.append({'name': name, 'path': str(path) if path else '', 'ready': size >= 1024**2, 'size': size})
    extension_ready = True
    if component in ('isolated-video', 'isolated-video-i2v'):
        extension_ready = omniweaving_extension_status()
    return {'ready': bool(files) and all(x['ready'] for x in files) and extension_ready,
            'files': files, 'extension_ready': extension_ready}


def ensure_media(component):
    if component not in MEDIA_MODELS:
        raise ValueError('Composant inconnu')
    model_dir = _media_model_dir(True)
    if model_dir is None:
        raise RuntimeError('Installation ComfyUI introuvable pour les modèles média.')
    if component in ('isolated-video', 'isolated-video-i2v'):
        ensure_omniweaving_extension()
    for folder, name, url in MEDIA_MODELS[component]:
        _download(url, model_dir / folder / name, 'Téléchargement : ' + name, min_bytes=1024**2)
    return True
