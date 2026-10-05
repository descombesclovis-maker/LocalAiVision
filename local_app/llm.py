import json, os, subprocess, sys, time, threading
from pathlib import Path
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = int(os.environ.get("LOCALVISIONAI_LLM_PORT", "8090"))
URL = f"http://{HOST}:{PORT}"
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LOCALVISIONAI_DATA", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LocalVisionAI")))
MODEL_DIR = DATA / "models"
ENGINE_DIR = DATA / "llama"
_proc = None
_lock = threading.RLock()
_cancel_event = threading.Event()


def _engine_candidates():
    roots = [ROOT / "llama", ROOT / "engine" / "llama", ENGINE_DIR]
    for root in roots:
        for name in ("llama-server.exe", "llama.exe"):
            p = root / name
            if p.exists():
                yield p


def find_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    preferred = os.environ.get("LOCALVISIONAI_LLM_MODEL")
    if preferred:
        p = Path(preferred).expanduser()
        if p.exists() and p.suffix.lower() == ".gguf":
            return p
    models = sorted(MODEL_DIR.rglob("*.gguf"), key=lambda p: p.stat().st_mtime, reverse=True)
    return models[0] if models else None


def online():
    try:
        req = Request(URL + "/v1/models", headers={"Accept": "application/json"})
        with urlopen(req, timeout=2) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return False, str(e)


def _gpu_layers(engine):
    configured = os.environ.get("LOCALVISIONAI_GPU_LAYERS")
    if configured is not None:
        return configured
    folder = engine.parent
    # The installer prefers CUDA, then Vulkan. Both can offload the complete
    # Qwen3 8B Q4 model on a 12 GB RTX card. CPU builds intentionally stay at 0.
    if (folder / "ggml-cuda.dll").exists() or (folder / "ggml-vulkan.dll").exists():
        return "999"
    return "0"


def _ensure_server(timeout=180):
    global _proc
    ok, _ = online()
    if ok:
        return True
    engine = next(_engine_candidates(), None)
    model = find_model()
    if not engine or not model:
        return False
    try:
        if _proc is not None and _proc.poll() is None:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if online()[0]:
                    return True
                if _proc.poll() is not None:
                    break
                time.sleep(.5)
            return False
        ENGINE_DIR.mkdir(parents=True, exist_ok=True)
        args = [str(engine), "-m", str(model), "--host", HOST, "--port", str(PORT),
                "--alias", "localvision-model", "--ctx-size", os.environ.get("LOCALVISIONAI_CONTEXT", "16384"),
                "-ngl", _gpu_layers(engine), "--jinja"]
        logs = DATA / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / "llm.log").open("ab") as log:
            _proc = subprocess.Popen(args, cwd=str(engine.parent), stdout=log,
                                     stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        ok, _ = online()
        if ok:
            return True
        if _proc.poll() is not None:
            return False
        time.sleep(0.5)
    return False


def status():
    ok, detail = online()
    model = find_model(); engine = next(_engine_candidates(), None)
    backend = "cpu"
    if engine:
        if (engine.parent / "ggml-cuda.dll").exists(): backend = "cuda"
        elif (engine.parent / "ggml-vulkan.dll").exists(): backend = "vulkan"
    return {"online": ok, "engine": str(engine) if engine else None, "model": str(model) if model else None,
            "model_name": model.name if model else None, "model_dir": str(MODEL_DIR), "url": URL,
            "backend": backend, "gpu_layers": _gpu_layers(engine) if engine else None,
            "detail": detail if not ok else None}


def _require_server():
    if ensure_server():
        return
    engine = next(_engine_candidates(), None)
    model = find_model()
    if not engine and model:
        raise RuntimeError("IA texte locale non disponible : llama.cpp (llama-server.exe) n'est pas installé. Clique sur « Installer / réessayer les moteurs » ; le modèle Qwen déjà présent sera conservé.")
    if engine and not model:
        raise RuntimeError("IA texte locale non disponible : aucun modèle GGUF n'est installé dans " + str(MODEL_DIR) + ".")
    if not engine and not model:
        raise RuntimeError("IA texte locale non disponible : llama.cpp et le modèle GGUF sont absents.")
    log = DATA / "logs" / "llm.log"
    raise RuntimeError("IA texte locale : llama.cpp est installé mais n'a pas réussi à démarrer. Consulte " + str(log) + ".")


def _prepare(messages, settings):
    messages = [dict(m) for m in messages if m.get('role') in ('system', 'user', 'assistant') and isinstance(m.get('content'), str)]
    limit = int(os.environ.get('LOCALVISIONAI_CONTEXT', '16384'))
    max_tokens = max(128, min(int(settings.get('max_tokens', 2048)), max(128, limit // 2)))
    def token_count(items):
        content = '\n'.join(m['content'] for m in items)
        request = Request(URL + '/tokenize', data=json.dumps({'content':content}).encode(), headers={'Content-Type':'application/json'})
        try:
            with urlopen(request, timeout=15) as response:
                return len(json.load(response)['tokens']) + 32 * len(items)
        except Exception:
            return len(content.encode('utf-8')) + 32 * len(items)
    while token_count(messages) + max_tokens + 256 > limit:
        oldest = next((i for i,m in enumerate(messages[:-1]) if m['role'] != 'system'), None)
        if oldest is None:
            raise RuntimeError('Ce message dépasse la capacité de contexte du modèle local. Envoie un texte plus court ou augmente LOCALVISIONAI_CONTEXT.')
        messages.pop(oldest)
        while len(messages)>1 and messages[0 if messages[0]['role']!='system' else 1]['role']=='assistant':
            messages.pop(0 if messages[0]['role']!='system' else 1)
    payload = {"model":"localvision-model","messages":messages,"stream":True,
               "temperature":float(settings.get("temperature",0.7)),
               "top_p":float(settings.get("top_p",0.9)),
               "max_tokens":max_tokens,
               "chat_template_kwargs": {"enable_thinking": False}}
    return payload


def chat_stream(messages, settings=None):
    settings = settings or {}
    _cancel_event.clear()
    _require_server()
    payload = _prepare(messages, settings)
    req = Request(URL + "/v1/chat/completions", data=json.dumps(payload).encode("utf-8"),
                  headers={"Content-Type":"application/json", "Accept":"text/event-stream"}, method="POST")
    yielded = False
    with urlopen(req, timeout=600) as r:
        for raw in r:
            if _cancel_event.is_set():
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content") or ""
            if content:
                yielded = True
                yield content
    if not yielded and not _cancel_event.is_set():
        raise RuntimeError("Le modèle n’a renvoyé aucun texte. Réessaie avec une question plus courte.")


def cancel_chat():
    _cancel_event.set()


def chat(messages, settings=None):
    return ''.join(chat_stream(messages, settings))


def ensure_server(timeout=180):
    with _lock:
        return _ensure_server(timeout)


def stop_server():
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            _proc.terminate()
            try:
                _proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                _proc.kill()
                _proc.wait(timeout=5)
        _proc = None
