import base64, json, mimetypes, os, re, subprocess, sys, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
try:
    from local_app import llm, workflows
except ImportError:
    import llm, workflows

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LOCALVISIONAI_DATA", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LocalVisionAI")))
WEB = ROOT / "local_app" / "web"
IMPORTED = DATA / "workflows" / "imported"
IMPORTED.mkdir(parents=True, exist_ok=True)
HOST = "127.0.0.1"
PORT = 3000
COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
_comfy_info_cache = {"time": 0, "data": {}}
_engine_lock = threading.RLock()
_comfy_lock = threading.Lock()
_setup_lock = threading.Lock()
_comfy_proc = None
_comfy_vram_args_cache = None
STARTUP = {"state": "idle", "message": "Prêt", "error": None, "started_at": None}
VERSION = "2.4.0"


IGNORE_JSON = {"package.json", "tsconfig.json", "config.json"}

# An explicit medium in the user's prompt must win over a stale graphical
# style saved in the UI. This prevents e.g. "une photo ..." from turning into
# a watercolor simply because Aquarelle had been selected during an earlier
# generation.
_STYLE_PATTERNS = (
    ("photo", re.compile(r"\b(photo(?:graph(?:ie|ique)?)?|photoreal(?:istic|ism)?|photor[ée]al(?:iste|isme)?)\b", re.I)),
    ("watercolor", re.compile(r"\b(aquarelle|watercolou?r)\b", re.I)),
    ("comic", re.compile(r"\b(bande\s+dessin[ée]e?|comic(?:\s*book)?|bd)\b", re.I)),
    ("render3d", re.compile(r"\b(rendu\s*3d|3d\s*render|image\s*3d)\b", re.I)),
    ("illustration", re.compile(r"\b(illustration|gouache|dessin(?:[ée]e?)?)\b", re.I)),
    ("cinema", re.compile(r"\b(cin[ée]ma(?:tographique)?|cinematic|film\s*still)\b", re.I)),
)


def _style_catalog():
    try:
        return json.loads((WEB / 'styles.json').read_text(encoding='utf-8'))
    except Exception:
        return []


def _explicit_style(prompt):
    text = prompt or ''
    for style_id, pattern in _STYLE_PATTERNS:
        if pattern.search(text):
            return style_id
    return None


def prepare_visual_request(prompt, selected_style='none', negative=None, reserved_profile=None, technical_quality=True):
    if reserved_profile == 'nsfw':
        try:
            from local_app import nsfw_profile
        except ImportError:
            import nsfw_profile
        prepared, neg, style = nsfw_profile.prepare_visual_request(
            prompt, selected_style, negative, technical_quality)
        raw = (prompt or '').strip()
        # The user's own request must remain the first semantic instruction.
        # Keep the profile's existing context, but move it after the raw prompt
        # instead of letting a broad profile prefix dominate composition.
        if raw and not prepared.startswith(raw):
            remainder = prepared
            pos = remainder.find(raw)
            if pos >= 0:
                remainder = (remainder[:pos] + remainder[pos + len(raw):]).strip()
            prepared = raw + (('\n\n' + remainder) if remainder else '')
        fidelity = (
            "Prompt fidelity only: preserve the user's requested viewpoint, framing, "
            "pose, clothing, scene, subject orientation and composition; do not replace "
            "specified details with a generic studio pose."
        )
        prepared += '\n\n' + fidelity
        return prepared, neg, style
    """Preserve the user's request and add only neutral technical quality hints.

    The original prompt is never paraphrased, softened, expanded with age/clothing/
    pose assumptions, or translated into composition instructions. A deliberately
    selected graphic style can still add its visual rendering preset. Technical
    hints only target rendering quality and common diffusion artefacts.
    """
    raw = (prompt or '').strip()
    explicit = _explicit_style(raw)
    # An explicit medium written by the user wins over a stale UI style. We do
    # not append another style prompt in that case: the user's wording is enough.
    effective_style = explicit or (selected_style if selected_style and selected_style != 'none' else None)
    prepared = raw

    if not explicit and effective_style:
        style = next((x for x in _style_catalog() if x.get('id') == effective_style), None)
        if style and style.get('prompt'):
            prepared += '\n\nVisual rendering style only: ' + style['prompt']

    if technical_quality:
        if effective_style == 'photo':
            quality = 'high detail, coherent anatomy, accurate hands, realistic texture, natural lighting, sharp focus, clean edges, low artifacts'
        elif effective_style in ('illustration', 'comic', 'watercolor'):
            quality = 'high detail, coherent anatomy, accurate hands, clean linework, consistent shapes, sharp focus, low artifacts'
        else:
            quality = 'high detail, coherent anatomy, accurate hands, clean edges, sharp focus, consistent shapes, low artifacts'
        prepared += '\n\nTechnical quality only: ' + quality + '.'

    neg = negative
    if technical_quality and not (negative or '').strip():
        neg = 'lowres, blurry, compression artifacts, watermark, unwanted text, malformed hands, fused fingers, extra fingers, missing fingers, extra limbs, duplicate limbs, broken anatomy, rendering artifacts'
    return prepared, neg, effective_style

def http_json(url, method="GET", payload=None, timeout=20, headers=None):
    data = None
    hdr = {"Content-Type": "application/json"}
    if headers:
        hdr.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=hdr, method=method)
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw.decode("utf-8")) if raw else {}

def comfy_get(path):
    return http_json(COMFY + path)

def comfy_post(path, payload):
    return http_json(COMFY + path, "POST", payload, timeout=60)

def _candidate_comfy_roots():
    here = Path(__file__).resolve().parent.parent
    roots = [
        here / "engine" / "ComfyUI",
        here / "ComfyUI",
        DATA / "ComfyUI",
        Path.home() / "ComfyUI",
        Path("D:/IA LOCAL/ComfyUI"),
    ]
    seen = set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key not in seen:
            seen.add(key)
            yield root

def _managed_comfy_vram_args():
    """Use low-VRAM mode automatically only on genuinely constrained NVIDIA GPUs."""
    global _comfy_vram_args_cache
    if _comfy_vram_args_cache is not None:
        return list(_comfy_vram_args_cache)

    mode = os.environ.get("LOCALVISION_COMFY_VRAM_MODE", "auto").strip().lower()
    if mode in ("low", "lowvram"):
        _comfy_vram_args_cache = ("--lowvram",)
        return list(_comfy_vram_args_cache)
    if mode in ("normal", "none", "off", "disabled"):
        _comfy_vram_args_cache = ()
        return []

    args = ()
    if mode in ("", "auto"):
        try:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            probe = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3, check=False,
                creationflags=creationflags,
            )
            totals = [int(line.strip()) for line in probe.stdout.splitlines() if line.strip().isdigit()]
            if totals and totals[0] <= 12288:
                args = ("--lowvram",)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    _comfy_vram_args_cache = args
    return list(args)


def _comfy_command(root):
    # Launch the Python child directly: no BAT wrapper, no frozen EXE recursion.
    launch = ["--listen", HOST, "--port", "8188", "--disable-auto-launch"] + _managed_comfy_vram_args()
    for py, main in ((root / "python_embeded/python.exe", root / "ComfyUI/main.py"),
                     (root / "python_embeded/python.exe", root / "main.py"),
                     (root / ".venv/Scripts/python.exe", root / "main.py"),
                     (root / "venv/Scripts/python.exe", root / "main.py")):
        if py.exists() and main.exists():
            return [str(py), str(main)] + launch, main.parent
    if not getattr(sys, "frozen", False) and (root / "main.py").exists():
        return [sys.executable, str(root / "main.py")] + launch, root
    return None, None


def _comfy_working_dir():
    """Return the ComfyUI directory used by the local installation, if known."""
    for root in _candidate_comfy_roots():
        cmd, cwd = _comfy_command(root)
        if cmd and cwd:
            return Path(cwd)
    return None


def _local_lora_metadata():
    """Return metadata for LoRA files already present on this machine."""
    cwd = _comfy_working_dir()
    if cwd is None:
        return []
    root = cwd / 'models' / 'loras'
    if not root.is_dir():
        return []

    catalog = {}
    bjornulf = cwd / 'custom_nodes' / 'Bjornulf_custom_nodes' / 'civitai' / 'parsed_lora_hunyuan_video_loras.json'
    if bjornulf.is_file():
        try:
            for item in json.loads(bjornulf.read_text(encoding='utf-8')):
                name = str(item.get('name') or '').strip()
                if name:
                    catalog[name + '.safetensors'] = item
        except Exception:
            pass

    result = []
    for path in sorted(root.rglob('*.safetensors'), key=lambda p: str(p).lower()):
        try:
            rel = path.relative_to(root).as_posix()
            meta = dict(catalog.get(path.name, {}))
            sidecar = path.with_suffix('.json')
            if sidecar.is_file():
                try:
                    local = json.loads(sidecar.read_text(encoding='utf-8'))
                    if isinstance(local, dict):
                        meta.update(local)
                except Exception:
                    pass
            words = meta.get('trained_words') or meta.get('trigger_words') or []
            if isinstance(words, str):
                words = [x.strip() for x in words.split(',') if x.strip()]
            result.append({
                'name': meta.get('name') or path.stem,
                'filename': path.name,
                'path': rel,
                'size': path.stat().st_size,
                'base_model': meta.get('base_model') or meta.get('compatibility') or '',
                'trained_words': words if isinstance(words, list) else [],
                'source': meta.get('source') or ('Bjornulf/CivitAI' if path.name in catalog else 'local'),
            })
        except OSError:
            continue
    return result


def _apply_lora_stack(api, selections):
    """Insert standard ComfyUI LoraLoader nodes for explicitly selected local LoRAs."""
    if not selections:
        return api
    available = {x['path'] for x in _local_lora_metadata()}
    clean = []
    for raw in selections[:8]:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get('path') or '').replace('\\', '/').strip('/')
        if path not in available:
            raise ValueError('LoRA local introuvable : ' + path)
        strength = float(raw.get('strength', 1.0))
        if not -2.0 <= strength <= 2.0:
            raise ValueError('La force LoRA doit être comprise entre -2 et 2.')
        clean.append((path, strength))
    if not clean:
        return api

    model_source = next(((nid, 0) for nid, n in api.items() if n['class_type'] in ('UNETLoader', 'CheckpointLoaderSimple')), None)
    clip_source = next(((nid, 0) for nid, n in api.items() if n['class_type'] in ('DualCLIPLoader', 'CLIPLoader')), None)
    if model_source is None or clip_source is None:
        raise ValueError('Ce workflow ne permet pas encore l’empilement automatique de LoRA.')

    original_ids = list(api)
    model_ref, clip_ref = [model_source[0], model_source[1]], [clip_source[0], clip_source[1]]
    next_id = max([int(x) for x in api if str(x).isdigit()] or [0]) + 1
    first_model_ref, first_clip_ref = list(model_ref), list(clip_ref)
    for path, strength in clean:
        nid = str(next_id); next_id += 1
        api[nid] = {
            'class_type': 'LoraLoader',
            'inputs': {
                'model': list(model_ref),
                'clip': list(clip_ref),
                'lora_name': path,
                'strength_model': strength,
                'strength_clip': strength,
            },
            '_meta': {'title': 'LocalVisionAI LoRA · ' + Path(path).stem},
        }
        model_ref, clip_ref = [nid, 0], [nid, 1]

    for nid in original_ids:
        node = api[nid]
        for key, value in list(node.get('inputs', {}).items()):
            if value == first_model_ref:
                node['inputs'][key] = list(model_ref)
            elif value == first_clip_ref:
                node['inputs'][key] = list(clip_ref)
    return api


def store_comfy_input(name, data):
    cwd = _comfy_working_dir()
    if cwd is None:
        raise RuntimeError("Impossible de localiser le dossier input de ComfyUI pour cette vidéo.")
    folder = cwd / 'input'
    folder.mkdir(parents=True, exist_ok=True)
    original = Path(name or 'input.bin').name
    safe = re.sub(r'[^\w .()\-]', '_', original, flags=re.UNICODE).strip('. ') or 'input.bin'
    filename = 'lva_' + uuid.uuid4().hex + '_' + safe
    target = (folder / filename).resolve()
    if not target.is_relative_to(folder.resolve()):
        raise ValueError('Nom de fichier invalide.')
    target.write_bytes(data)
    return {'name': filename, 'subfolder': '', 'type': 'input'}


def delete_comfy_output(filename, subfolder='', typ='output'):
    if typ != 'output':
        raise ValueError('Seuls les fichiers générés peuvent être supprimés depuis la bibliothèque.')
    cwd = _comfy_working_dir()
    if cwd is None:
        raise RuntimeError('Installation ComfyUI locale introuvable.')
    base = (cwd / 'output').resolve()
    safe_name = Path(filename or '').name
    if not safe_name:
        raise ValueError('Fichier manquant.')
    rel = Path(subfolder or '') / safe_name
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise ValueError('Chemin de sortie invalide.')
    existed = target.is_file()
    if existed:
        target.unlink()
    return existed


def ensure_comfyui(timeout=180):
    global _comfy_proc
    with _comfy_lock:
        if comfy_online()[0]:
            return True
        if _comfy_proc is None or _comfy_proc.poll() is not None:
            for root in _candidate_comfy_roots():
                cmd, cwd = _comfy_command(root)
                if not cmd:
                    continue
                logs = DATA / "logs"
                logs.mkdir(parents=True, exist_ok=True)
                with (logs / "comfy.log").open("ab") as log:
                    _comfy_proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=log, stderr=log,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                break
            else:
                return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if comfy_online()[0]:
                return True
            if _comfy_proc.poll() is not None:
                return False
            time.sleep(.5)
        return False


def comfy_online():
    try:
        data = http_json(COMFY + "/system_stats", timeout=2)
        return True, data
    except Exception as e:
        return False, str(e)

def object_info():
    now = time.time()
    if now - _comfy_info_cache["time"] < 20 and _comfy_info_cache["data"]:
        return _comfy_info_cache["data"]
    try:
        data = comfy_get("/object_info")
        _comfy_info_cache["time"] = now
        _comfy_info_cache["data"] = data
        return data
    except Exception:
        return {}

def scan_workflows():
    out = []
    # Bundled workflows and durable imports use distinct namespaces.
    for base, prefix in ((ROOT, ""), (IMPORTED, "imported/")):
        for p in base.glob("*.json"):
            if p.name in IGNORE_JSON:
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                workflows.validate_document(raw)
                out.append(workflow_card(prefix + p.name, raw))
            except (ValueError, OSError):
                continue
    info = object_info()
    for card in out:
        try:
            wf = load_workflow(card['id'])
            nodes = wf.values() if workflows.is_api(wf) else wf.get('nodes', [])
            models, missing = [], []
            for node in nodes:
                typ = node.get('class_type') or node.get('type')
                if typ in ('Note', 'MarkdownNote') or node.get('mode') in (2,4):
                    continue
                values = list(node.get('inputs', {}).values()) if workflows.is_api(wf) else node.get('widgets_values') or []
                names = [v for v in values if isinstance(v, str) and v.lower().endswith(('.safetensors','.gguf','.ckpt'))]
                models.extend(names)
                if info:
                    if typ not in info:
                        missing.append('Nœud : ' + str(typ))
                    else:
                        choices = []
                        for section in ('required','optional'):
                            for definition in info[typ].get('input', {}).get(section, {}).values():
                                if definition and isinstance(definition[0], list):
                                    choices.extend(definition[0])
                        missing.extend(n for n in names if n not in choices)
            if wf.get('definitions', {}).get('subgraphs'):
                missing.append('Exporter les sous-graphes au format API')
            card.update(models=models, missing=missing, ready=(not missing) if info else None)
        except Exception:
            card.update(models=[], missing=[], ready=None)
    return sorted(out, key=lambda x: x["name"].lower())


def workflow_card(rel, wf):
    name = Path(rel).stem
    low = name.lower()
    if "ltx" in low:
        kind, icon = "video-heavy", "🎞️"
    elif "motion" in low or "vace" in low or "video2video" in low or "video-to-video" in low:
        kind, icon = "motion", "↝"
    elif "video" in low or "wan" in low:
        kind, icon = "video", "🎬"
    elif "retouch" in low or "retouche" in low or "inpaint" in low or "img2img" in low:
        kind, icon = "retouch", "✨"
    else:
        kind, icon = "image", "🖼️"
    return {"id": rel, "name": name, "kind": kind, "icon": icon, "node_count": len(wf.get("nodes", wf)) if isinstance(wf, dict) else 0}

def load_workflow(rel):
    if not isinstance(rel, str):
        raise ValueError("Identifiant de workflow invalide")
    if rel.startswith("imported/"):
        base, name = IMPORTED.resolve(), rel[len("imported/"):]
    else:
        base, name = ROOT.resolve(), rel
    p = (base / name).resolve()
    if p.parent != base or p.suffix.lower() != ".json":
        raise ValueError("Chemin de workflow invalide")
    if not p.is_file():
        raise FileNotFoundError(rel)
    wf = json.loads(p.read_text(encoding="utf-8"))
    workflows.validate_document(wf)
    return wf


def convert_ui_to_api(wf):
    return workflows.to_api(wf, object_info())


def apply_user_inputs(api, prompt="", negative=None, image_ref=None, settings=None, mask_ref=None, video_ref=None):
    return workflows.apply_inputs(api, prompt, negative, image_ref, settings, mask_ref, video_ref)


def comfy_busy():
    state = comfy_get("/queue")
    return bool(state.get("queue_running") or state.get("queue_pending"))


def _free_comfy_if_idle():
    """Unload ComfyUI models only after every queued generation has finished."""
    try:
        state = comfy_get("/queue")
        if state.get("queue_running") or state.get("queue_pending"):
            return False
        comfy_post("/free", {"unload_models": True, "free_memory": True})
        return True
    except Exception:
        return False


def _prepare_chat(body):
    if comfy_online()[0]:
        if comfy_busy():
            raise RuntimeError("Une génération est en cours. Attends sa fin avant de lancer le chat, afin de préserver la mémoire GPU.")
        comfy_post("/free", {"unload_models": True, "free_memory": True})
    messages = body.get("messages") or []
    if not messages:
        raise ValueError("Aucun message à envoyer.")
    return messages


def _ensure_chat_components():
    """Install the local text engine lazily; media generation does not depend on it."""
    status = llm.status()
    if status.get("engine") and status.get("model"):
        return
    from local_app import bootstrap_windows
    previous_progress = bootstrap_windows.PROGRESS
    try:
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        STARTUP.update(state="running", message="Préparation du chat local…", error=None, started_at=time.time())
        if not status.get("engine"):
            bootstrap_windows.ensure_llama()
        if not status.get("model"):
            bootstrap_windows.ensure_model()
        STARTUP.update(state="ready", message="Chat local prêt.", error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state="error", message="Installation du chat à reprendre", error=str(exc), started_at=None)
        raise
    finally:
        bootstrap_windows.PROGRESS = previous_progress


def run_chat(body):
    with _engine_lock:
        _ensure_chat_components()
        messages = _prepare_chat(body)
        return llm.chat(messages, body.get("settings") or {})


def run_chat_stream(body):
    with _engine_lock:
        _ensure_chat_components()
        messages = _prepare_chat(body)
        yield from llm.chat_stream(messages, body.get("settings") or {})


def translate_visual_prompt_to_english(text):
    raw = (text or '').strip()
    if not raw:
        return raw
    translated = llm.chat([
        {'role': 'system', 'content': (
            'Translate the following image or video generation prompt faithfully into natural English. '
            'Preserve all requested details, negations, numbers, viewpoint, framing, pose, clothing, '
            'actions, adjectives and proper nouns. Do not add explanations or creative details. '
            'Return only the English translation. If already English, return it unchanged.'
        )},
        {'role': 'user', 'content': raw}
    ], {'temperature': 0.0, 'top_p': 0.1, 'max_tokens': 2048})
    value = (translated or '').strip()
    value = re.sub(r'^(?:translation|english|translated prompt)\\s*:\\s*', '', value, flags=re.I).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1].strip()
    if not value:
        raise RuntimeError("La traduction anglaise du prompt n'a renvoyé aucun texte.")
    return value


def _wait_for_setup(timeout=7200):
    deadline = time.monotonic() + timeout
    while _setup_lock.locked():
        if time.monotonic() >= deadline:
            raise RuntimeError("L’installation des modèles prend trop de temps. Consulte le journal puis réessaie.")
        time.sleep(.25)


def _restart_owned_comfyui():
    global _comfy_proc
    proc = _comfy_proc
    if proc is None or proc.poll() is not None:
        return False
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try: proc.kill()
        except Exception: pass
    _comfy_proc = None
    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    return ensure_comfyui(timeout=180)


def _media_component_for_workflow(current):
    values = ' '.join(str(v).lower() for n in current.values() for v in n.get('inputs', {}).values() if isinstance(v, str))
    if 'hunyuanimage2.1_distilled_fp8_e4m3fn.safetensors' in values:
        return 'isolated-image'
    if 'hunyuanvideo1.5_480p_i2v_step_distilled_fp8_scaled.safetensors' in values:
        return 'isolated-video-i2v'
    if 'hunyuanvideo1.5_480p_t2v_cfg_distilled_fp8_scaled.safetensors' in values:
        return 'isolated-video'
    profile = workflows.profile(current)
    if profile == 'sdxl':
        return 'image'
    if profile == 'wan':
        return 'video'
    if profile == 'hunyuanimage21':
        return 'isolated-image'
    if profile == 'hunyuan15-i2v-step':
        return 'isolated-video-i2v'
    return 'isolated-video' if profile == 'hunyuan15' else None


def _preflight_with_media_repair(current):
    try:
        workflows.preflight(current, object_info())
        return
    except ValueError as first_error:
        text = str(first_error)
        component = _media_component_for_workflow(current)
        # Only self-repair missing model/file choices. Structural workflow errors
        # must remain visible instead of triggering unrelated downloads.
        if component is None or 'valeur ou fichier indisponible' not in text:
            raise

    from local_app import bootstrap_windows
    if not _setup_lock.acquire(blocking=False):
        _wait_for_setup()
        _setup_lock.acquire()
    try:
        labels = {
            'image':'RealVisXL (photo)',
            'video':'Wan 2.1 1.3B (vidéo)',
            'isolated-image':'HunyuanImage 2.1 distilled FP8 (espace isolé)',
            'isolated-video':'HunyuanVideo 1.5 T2V (espace isolé)',
            'isolated-video-i2v':'HunyuanVideo 1.5 I2V step-distilled (espace isolé)',
        }
        label = labels.get(component, component)
        STARTUP.update(state='running', message='Préparation automatique : ' + label, error=None, started_at=time.time())
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        # Safe to call even after another setup just finished: existing files are
        # detected immediately, while a genuinely missing file is downloaded.
        bootstrap_windows.ensure_media(component)
        _comfy_info_cache['time'] = 0
        _comfy_info_cache['data'] = {}
        STARTUP.update(state='ready', message='Modèles média prêts.', error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state='error', message='Installation à reprendre', error=str(exc), started_at=None)
        raise
    finally:
        _setup_lock.release()

    _comfy_info_cache['time'] = 0
    _comfy_info_cache['data'] = {}
    try:
        workflows.preflight(current, object_info())
    except ValueError:
        # ComfyUI normally refreshes model lists dynamically. If the instance
        # is the one started by LocalVisionAI, restart it once to force a scan.
        if not _restart_owned_comfyui():
            raise
        _comfy_info_cache['time'] = 0
        _comfy_info_cache['data'] = {}
        workflows.preflight(current, object_info())


def run_generation(body):
    # The first photo request can arrive while the automatic SDXL download is
    # still running. Wait for it instead of failing and forcing a second click.
    _wait_for_setup()
    with _engine_lock:
        if not ensure_comfyui(timeout=180):
            raise RuntimeError("ComfyUI n’est pas prêt. Consulte l’état d’installation et le journal comfy.log, puis utilise Réessayer.")
        wf = load_workflow(body.get("workflow"))
        api = convert_ui_to_api(wf)
        if not api:
            raise ValueError("Workflow vide ou non convertible")
        requires_image = any(n['class_type'] == 'LoadImage' for n in api.values())
        requires_mask = any(n['class_type'] == 'LoadImageMask' for n in api.values())
        requires_video = any(n['class_type'] == 'LoadVideo' for n in api.values())
        if requires_image and not body.get('image'):
            raise ValueError("Ajoute une image de référence avec le bouton +.")
        if requires_mask and not body.get('mask'):
            raise ValueError("Ouvre le masque et peins la zone à retoucher.")
        if requires_video and not body.get('video'):
            raise ValueError("Ajoute une vidéo de référence avec le bouton vidéo.")
        image_ref = mask_ref = video_ref = None
        if body.get('image'):
            data = base64.b64decode(body['image'].split(',', 1)[-1], validate=True)
            image_ref = upload_image('lva_' + uuid.uuid4().hex + '_' + Path(body.get('image_name') or 'input.png').name, data)
        if body.get('mask'):
            data = base64.b64decode(body['mask'].split(',', 1)[-1], validate=True)
            mask_ref = upload_image('lva_mask_' + uuid.uuid4().hex + '.png', data)
        if body.get('video'):
            data = base64.b64decode(body['video'].split(',', 1)[-1], validate=True)
            video_ref = store_comfy_input(Path(body.get('video_name') or 'reference.mp4').name, data)
        settings = body.get('settings') or {}
        source_prompt = (body.get('prompt') or '').strip()
        source_negative = body.get('negative')
        if settings.get('prompt_translation'):
            _ensure_chat_components()
            try:
                prepared_prompt = translate_visual_prompt_to_english(source_prompt)
                prepared_negative = translate_visual_prompt_to_english(source_negative) if isinstance(source_negative, str) and source_negative.strip() else source_negative
            finally:
                llm.stop_server()
        else:
            prepared_prompt = source_prompt
            prepared_negative = source_negative
        if settings.get('exact_prompt'):
            prompt = prepared_prompt
            negative = prepared_negative
            effective_style = None
        else:
            prompt, negative, effective_style = prepare_visual_request(
                prepared_prompt, settings.get('style'), prepared_negative, settings.get('reserved_profile'), settings.get('technical_quality', True))
        count = max(1, min(int(settings.get('count') or 1), 4))
        base_seed = settings.get('seed')
        prepared = []
        for index in range(count):
            current = json.loads(json.dumps(api))
            run_settings = dict(settings)
            if base_seed is None:
                run_settings['seed'] = uuid.uuid4().int % 2147483647
            else:
                run_settings['seed'] = int(base_seed) + (0 if settings.get('keepSeed') else index)
            current = apply_user_inputs(current, prompt, negative, image_ref, run_settings, mask_ref, video_ref)
            current = _apply_lora_stack(current, run_settings.get('loras') or [])
            _preflight_with_media_repair(current)
            prepared.append(current)
        # Only the subprocess created by this application may be stopped.
        llm.stop_server()
        results, warnings = [], []
        if llm.online()[0]:
            warnings.append("Un serveur texte externe reste actif ; sa mémoire GPU ne peut pas être libérée par cette application.")
        for current in prepared:
            try:
                result = queue_prompt(current)
                if not result.get('prompt_id'):
                    raise RuntimeError(json.dumps(result, ensure_ascii=False))
                results.append(result)
            except Exception as exc:
                if not results:
                    raise
                warnings.append("Seule une partie du lot a été acceptée : " + str(exc))
                break
        ids = [x['prompt_id'] for x in results]
        return {'ok': True, 'prompt_id': ids[0], 'prompt_ids': ids, 'warnings': warnings}



def upload_image(filename, data):
    boundary = "----LocalVisionAI" + uuid.uuid4().hex
    body = bytearray()
    def add_field(name, value):
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode())
    body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode())
    body.extend(data)
    body.extend(f"\r\n".encode())
    add_field("type","input")
    add_field("overwrite","true")
    body.extend(f"--{boundary}--\r\n".encode())
    req = Request(COMFY + "/upload/image", data=bytes(body), headers={"Content-Type":f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def queue_prompt(api):
    return comfy_post("/prompt", {"prompt": api, "client_id": str(uuid.uuid4())})

def history(prompt_id):
    result = comfy_get("/history/" + quote(prompt_id))
    if prompt_id not in result:
        queue = comfy_get('/queue')
        active = queue.get('queue_running', []) + queue.get('queue_pending', [])
        result['_missing'] = not any(len(item)>1 and item[1]==prompt_id for item in active)
    else:
        # Outputs remain on disk; unloading the finished models gives the chat
        # or the next media engine the maximum available GPU memory.
        _free_comfy_if_idle()
    return result

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(raw)

    def send_bytes(self, data, content_type="application/octet-stream", status=200):
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/ping":
            self.send_json({"app": "LocalVisionAI", "version": VERSION})
            return
        if u.path == "/api/health":
            online, detail = comfy_online()
            media = {'image': {'ready': False}, 'video': {'ready': False}, 'isolated-video': {'ready': False}}
            try:
                from local_app import bootstrap_windows
                media = {
                    'image': bootstrap_windows.media_status('image'),
                    'video': bootstrap_windows.media_status('video'),
                    'isolated-image': bootstrap_windows.media_status('isolated-image'),
                    'isolated-video': bootstrap_windows.media_status('isolated-video'),
                    'isolated-video-i2v': bootstrap_windows.media_status('isolated-video-i2v')
                }
            except Exception:
                pass
            self.send_json({"online":online,"detail":detail,"url":COMFY,"llm":llm.status(), "startup": dict(STARTUP), "media": media, "version": VERSION})
            return
        if u.path == "/api/logs":
            parts = []
            for name in ("startup.log", "comfy.log", "llm.log"):
                path = DATA / "logs" / name
                if path.is_file():
                    with path.open("rb") as log:
                        log.seek(max(0, path.stat().st_size - 12000))
                        parts.append(name + "\n" + log.read().decode("utf-8", errors="replace"))
            self.send_json({"text": "\n\n".join(parts) or "Aucun journal disponible pour le moment."})
            return
        if u.path == "/api/llm":
            self.send_json(llm.status())
            return
        if u.path == "/api/workflows":
            self.send_json({"workflows":scan_workflows()})
            return
        if u.path == "/api/loras":
            self.send_json({"loras": _local_lora_metadata()})
            return
        if u.path == "/api/workflow":
            rel = parse_qs(u.query).get("id",[None])[0]
            try: self.send_json({"workflow":load_workflow(rel)})
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path.startswith("/api/history/"):
            pid = u.path.split("/",3)[3]
            try: self.send_json(history(pid))
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path == "/api/view":
            q = parse_qs(u.query)
            try:
                filename=q.get("filename",[""])[0]; sub=q.get("subfolder",[""])[0]; typ=q.get("type",["output"])[0]
                params=f"?filename={quote(filename)}&subfolder={quote(sub)}&type={quote(typ)}"
                with urlopen(COMFY+"/view"+params,timeout=60) as r:
                    self.send_bytes(r.read(),r.headers.get_content_type())
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path.startswith("/api/asset"):
            # Kept as a stable namespace for future local asset management.
            self.send_json({"ok":True})
            return
        if u.path == "/" or u.path.startswith("/assets/"):
            rel = "index.html" if u.path=="/" else u.path[len("/assets/"):]
            p = (WEB / rel).resolve()
            if not p.is_relative_to(WEB.resolve()) or not p.exists() or not p.is_file():
                self.send_response(404); self.end_headers(); return
            data=p.read_bytes()
            c=mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            self.send_bytes(data,c)
            return
        self.send_response(404); self.end_headers()

    def do_POST(self):
        u=urlparse(self.path)
        length=int(self.headers.get("Content-Length","0"))
        raw=self.rfile.read(length)
        try: body=json.loads(raw.decode())
        except Exception:
            self.send_json({"error":"JSON invalide"},400); return
        if u.path == "/api/setup":
            if body.get("component", "engines") not in ("engines", "image", "video", "isolated-image", "isolated-video", "isolated-video-i2v"):
                self.send_json({"error": "Composant inconnu"}, 400)
                return
            started = start_setup(body.get("component", "engines"))
            self.send_json({"ok": True, "started": started, "startup": dict(STARTUP)})
            return
        if u.path == "/api/import-workflow":
            try:
                workflows.validate_document(body.get("workflow"))
                name=Path(body.get("name","workflow.json").replace("\\", "/")).name
                name=re.sub(r'[^\w .()-]', '_', name).strip('. ') or 'workflow'
                if not name.lower().endswith(".json"): name += ".json"
                dest=IMPORTED / (uuid.uuid4().hex[:8] + "_" + name)
                dest.write_text(json.dumps(body["workflow"],ensure_ascii=False,indent=2),encoding="utf-8")
                self.send_json({"ok":True,"id":"imported/" + dest.name})
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/upload":
            try:
                b64=body["data"].split(",",1)[-1]
                result=upload_image(Path(body.get("name","input.png")).name,base64.b64decode(b64))
                self.send_json({"ok":True,"file":result})
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        if u.path == "/api/delete-output":
            try:
                deleted = delete_comfy_output(body.get('filename',''), body.get('subfolder',''), body.get('type','output'))
                self.send_json({"ok": True, "deleted": deleted})
            except Exception as e:
                self.send_json({"error": str(e)}, 400)
            return
        if u.path == "/api/chat/stop":
            llm.cancel_chat()
            self.send_json({"ok": True})
            return
        if u.path == "/api/chat/stream":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-transform")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                self.wfile.write(b'{"ready":true}\n')
                self.wfile.flush()
                for chunk in run_chat_stream(body):
                    self.wfile.write((json.dumps({"delta": chunk}, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b'{"done":true}\n')
                self.wfile.flush()
            except Exception as e:
                try:
                    self.wfile.write((json.dumps({"error": str(e)}, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    pass
            return
        if u.path == "/api/chat":
            try:
                answer = run_chat(body)
                self.send_json({"ok":True,"message":answer})
            except HTTPError as e:
                try: detail=e.read().decode()
                except: detail=str(e)
                self.send_json({"error":detail},502)
            except Exception as e: self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/generate":
            try:
                self.send_json(run_generation(body))
            except HTTPError as e:
                try: detail=e.read().decode()
                except: detail=str(e)
                self.send_json({"error":detail},502)
            except Exception as e:
                self.send_json({"error":str(e)},400)
            return
        if u.path == "/api/interrupt":
            try: self.send_json(comfy_post("/interrupt","{}" if False else {}))
            except Exception as e: self.send_json({"error":str(e)},502)
            return
        self.send_response(404); self.end_headers()

def _setup_worker(component):
    try:
        from local_app import bootstrap_windows
        bootstrap_windows.PROGRESS = lambda message: STARTUP.update(message=message)
        STARTUP.update(state="running", message="Préparation des composants…", error=None, started_at=time.time())
        if component == "engines":
            # Attempt components independently: a text download must not prevent
            # an already installed image engine from working (or vice versa).
            errors = []
            for label, action in (("ComfyUI", bootstrap_windows.ensure_comfy),
                                  ("RealVisXL image", lambda: bootstrap_windows.ensure_media('image'))):
                STARTUP['message'] = "Installation / vérification : " + label
                try:
                    action()
                    if label == "ComfyUI" and not ensure_comfyui():
                        raise RuntimeError("ComfyUI ne démarre pas ; consulte logs/comfy.log.")
                    if label == "RealVisXL image":
                        _comfy_info_cache['time'] = 0
                        _comfy_info_cache['data'] = {}
                except Exception as exc:
                    errors.append(label + " : " + str(exc))
            if errors:
                raise RuntimeError("\n".join(errors))
        else:
            STARTUP['message'] = "Téléchargement des modèles " + (
                "photo (RealVisXL)" if component == 'image'
                else "photo isolée (HunyuanImage 2.1)" if component == 'isolated-image'
                else "vidéo isolée T2V (HunyuanVideo 1.5)" if component == 'isolated-video'
                else "vidéo isolée I2V (HunyuanVideo 1.5 step-distilled)" if component == 'isolated-video-i2v'
                else "vidéo (Wan 2.1)")
            bootstrap_windows.ensure_media(component)
            _comfy_info_cache['time'] = 0
        STARTUP.update(state="ready", message="Moteur média prêt. Le chat local sera préparé seulement à sa première utilisation.", error=None, started_at=None)
    except Exception as exc:
        STARTUP.update(state="error", message="Installation à reprendre", error=str(exc), started_at=None)
        print("[LocalVisionAI]", exc, flush=True)
    finally:
        _setup_lock.release()
        if component == "engines":
            try:
                bootstrap_windows.cleanup_obsolete_media()
            except Exception:
                pass


def start_setup(component="engines"):
    if not _setup_lock.acquire(blocking=False):
        return False
    STARTUP.update(state="running", message="Préparation…", error=None, started_at=time.time())
    threading.Thread(target=_setup_worker, args=(component,), daemon=True).start()
    return True


def stop_engines():
    llm.stop_server()
    proc = _comfy_proc
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    print(f"LocalVisionAI -> http://{HOST}:{PORT}", flush=True)
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    if os.environ.get('LOCALVISIONAI_SKIP_SETUP') != '1':
        start_setup()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        stop_engines()


if __name__=="__main__":
    main()
