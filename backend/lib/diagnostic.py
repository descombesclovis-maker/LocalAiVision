"""Installation diagnostic: checks everything LocalAiStudio needs on the machine that runs it
(database, disk, Ollama + model, ComfyUI + GPU + model files, Node) and says exactly what to fix."""
import asyncio
import shutil
import subprocess
from pathlib import Path

from lib import comfy, local_engine
from lib.db import db
from lib.store import now_iso

ROOT = Path(__file__).resolve().parents[2]
MODELS_GB = 45  # FLUX dev fp8 + Wan 2.2 5B + encoders + text model, with margin


def _check(key: str, label: str, status: str, detail: str, fix: str = "", cmd: str = "") -> dict:
    return {"key": key, "label": label, "status": status, "detail": detail, "fix": fix, "cmd": cmd}


async def _mongo() -> dict:
    try:
        await asyncio.wait_for(db.command("ping"), 4)
        return _check("mongodb", "Base de données MongoDB", "ok", "MongoDB répond.")
    except Exception:
        return _check("mongodb", "Base de données MongoDB", "error", "MongoDB ne répond pas : projets et médias ne peuvent pas être enregistrés.",
                      "Démarrez le service MongoDB (ou réinstallez-le avec l'installateur).", "net start MongoDB")


def _disk() -> dict:
    u = shutil.disk_usage(ROOT)
    free = u.free / 1024**3
    detail = f"{free:.0f} Go libres sur {u.total / 1024**3:.0f} Go (disque de LocalAiStudio)."
    if free >= MODELS_GB + 15:
        return _check("disk", "Espace disque", "ok", detail)
    status = "warn" if free >= 20 else "error"
    return _check("disk", "Espace disque", status, detail,
                  f"Prévoyez au moins {MODELS_GB + 15} Go libres pour les modèles (FLUX ≈ 17 Go, Wan 2.2 ≈ 17 Go, texte ≈ 9 Go) et les rendus. "
                  "Libérez de la place ou installez les modèles ComfyUI sur un autre disque.")


def _node() -> dict:
    exe = shutil.which("node")
    if not exe:
        return _check("node", "Node.js (interface)", "error", "Node.js est introuvable.", "Installez Node.js LTS.", "winget install OpenJS.NodeJS.LTS")
    try:
        v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        v = "?"
    major = int(v.lstrip("v").split(".")[0]) if v[1:2].isdigit() else 0
    if major and major < 18:
        return _check("node", "Node.js (interface)", "warn", f"Node.js {v} est trop ancien.", "Installez Node.js 20 LTS ou plus récent.", "winget install OpenJS.NodeJS.LTS")
    return _check("node", "Node.js (interface)", "ok", f"Node.js {v}.")


async def _ollama() -> list[dict]:
    s = await local_engine.get_settings()
    name = "Ollama" if s["kind"] == "ollama" else "LM Studio"
    try:
        models = await local_engine.list_models(s)
    except Exception:
        fix = ("Installez Ollama puis lancez-le (icône dans la barre des tâches, ou commande ci-dessous). "
               if s["kind"] == "ollama" else "Ouvrez LM Studio → onglet Developer → Start server. ")
        return [
            _check("llm", f"{name} (sites web)", "error", f"Injoignable à {s['base_url']}.", fix + "Vérifiez l'adresse dans Moteurs → Configurer.",
                   "ollama serve" if s["kind"] == "ollama" else ""),
            _check("llm_model", f"Modèle de texte {s['model']}", "error", "Impossible de vérifier : le serveur ne répond pas.", f"Démarrez d'abord {name}."),
        ]
    out = [_check("llm", f"{name} (sites web)", "ok", f"Joignable à {s['base_url']} · {len(models)} modèle(s) installé(s).")]
    if s["model"] in models:
        out.append(_check("llm_model", f"Modèle de texte {s['model']}", "ok", "Installé et prêt."))
    else:
        alt = f" Modèles présents : {', '.join(models[:5])}." if models else ""
        out.append(_check("llm_model", f"Modèle de texte {s['model']}", "error", "Modèle absent." + alt,
                          "Téléchargez le modèle (≈ 9 Go), ou choisissez un modèle présent dans Moteurs → Configurer.",
                          f"ollama pull {s['model']}" if s["kind"] == "ollama" else ""))
    return out


async def _comfy() -> list[dict]:
    s = await comfy.get_settings()
    base = s["base_url"].rstrip("/")
    try:
        async with comfy._client(8) as c:
            r = await c.get(f"{base}/system_stats")
            r.raise_for_status()
            dev = (r.json().get("devices") or [{}])[0]
            lists = await asyncio.gather(
                comfy._choices(c, base, "CheckpointLoaderSimple", "ckpt_name"),
                comfy._choices(c, base, "UNETLoader", "unet_name"),
                comfy._choices(c, base, "CLIPLoader", "clip_name"),
                comfy._choices(c, base, "VAELoader", "vae_name"),
            )
    except Exception:
        return [
            _check("comfy", "ComfyUI (photos & vidéos)", "error", f"Injoignable à {base}.",
                   "Lancez ComfyUI Desktop (ou « python main.py --listen » en version portable). ComfyUI Desktop utilise parfois le port 8000 : "
                   "ajustez l'adresse dans Moteurs → Configurer."),
            _check("gpu", "Carte graphique", "warn", "Impossible de lire la carte graphique : ComfyUI ne répond pas.", "Démarrez ComfyUI."),
            _check("img_model", "Modèle photo", "warn", "Impossible de vérifier : ComfyUI ne répond pas.", "Démarrez ComfyUI."),
            _check("vid_model", "Modèles vidéo", "warn", "Impossible de vérifier : ComfyUI ne répond pas.", "Démarrez ComfyUI."),
        ]
    ckpts, unets, clips, vaes = lists
    vram = (dev.get("vram_total") or 0) / 1024**3
    gname = dev.get("name", "GPU").split(":")[-1].strip()
    out = [_check("comfy", "ComfyUI (photos & vidéos)", "ok", f"Joignable à {base}.")]
    if dev.get("type") == "cpu" or vram == 0:
        out.append(_check("gpu", "Carte graphique", "error", "ComfyUI tourne sur le processeur : les rendus seront extrêmement lents.",
                          "Installez la version NVIDIA de ComfyUI et les derniers pilotes GeForce."))
    elif vram < 11:
        out.append(_check("gpu", "Carte graphique", "warn", f"{gname} · {vram:.1f} Go de VRAM.",
                          "Moins de 12 Go : préférez FLUX schnell ou SDXL pour les photos et LTX-Video pour les vidéos (Moteurs → Configurer)."))
    else:
        out.append(_check("gpu", "Carte graphique", "ok", f"{gname} · {vram:.1f} Go de VRAM."))
    if s["image_checkpoint"] in ckpts:
        out.append(_check("img_model", f"Modèle photo · {s['image_checkpoint']}", "ok", "Présent dans models/checkpoints."))
    else:
        out.append(_check("img_model", f"Modèle photo · {s['image_checkpoint']}", "error", "Fichier absent de ComfyUI/models/checkpoints.",
                          "Lancez download-models.ps1 (ou cochez « Modèles IA » dans l'installateur), puis redémarrez ComfyUI.",
                          "powershell -ExecutionPolicy Bypass -File .\\download-models.ps1"))
    need = [("diffusion_models" if s["video_preset"] == "wan22" else "checkpoints", s["video_model"], unets if s["video_preset"] == "wan22" else ckpts),
            ("text_encoders", s["video_text_encoder"], clips)]
    if s.get("video_vae"):
        need.append(("vae", s["video_vae"], vaes))
    missing = [f"{folder}/{f}" for folder, f, have in need if f and f not in have]
    if missing:
        out.append(_check("vid_model", "Modèles vidéo (Wan 2.2 / LTX)", "error", "Absents : " + ", ".join(missing),
                          "Lancez download-models.ps1, puis redémarrez ComfyUI. Sans ces fichiers, la vidéo d'en-tête et les pubs vidéo sont désactivées.",
                          "powershell -ExecutionPolicy Bypass -File .\\download-models.ps1"))
    else:
        out.append(_check("vid_model", "Modèles vidéo (Wan 2.2 / LTX)", "ok", "Tous les fichiers sont présents."))
    return out


async def run(host: str) -> dict:
    online = host not in ("localhost", "127.0.0.1", "0.0.0.0", "::1") and not host.startswith("192.168.")
    mongo, llm, cf = await asyncio.gather(_mongo(), _ollama(), _comfy())
    checks = [mongo, _disk(), _node(), *llm, *cf]
    if online:
        checks.insert(0, _check("where", "Où tourne cette application ?", "info",
                                "Vous consultez la preview en ligne : les vérifications portent sur le serveur, pas sur votre PC. "
                                "Ollama et ComfyUI de votre PC ne sont joignables que via un accès authentifié.",
                                "Installez LocalAiStudio sur votre PC (Moteurs → Kit Windows). Les tunnels publics non authentifiés ont été désactivés pour des raisons de sécurité."))
    count = {k: sum(1 for c in checks if c["status"] == k) for k in ("ok", "warn", "error")}
    return {"checks": checks, "ok": count["ok"], "warn": count["warn"], "error": count["error"], "online": online, "checked_at": now_iso()}
