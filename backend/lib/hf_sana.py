"""Private LocalAiStudio Hugging Face Space connector for SANA T2V.

The HF credential is supplied only by the authenticated backend (DPAPI storage),
never by browser code. Status calls are CPU/API-only; only ``generate`` allocates
remote ZeroGPU. This module deliberately does not route I2V to the T2V checkpoint.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Awaitable, Callable
from urllib.parse import quote, urlparse

import httpx

from lib.hf_video import HfVideoError, verify_mp4

SPACE_ID = "clocltrrh/LocalAiStudio-VideoEngine"
BASE_URL = "https://clocltrrh-localaistudio-videoengine.hf.space"
MODEL = "SANA-Video 2.0 5B 4-step"
PROFILES = {"5": ("5 seconds", 81, 16), "8": ("8 seconds", 193, 24)}
MAX_MP4_BYTES = 512 * 1024 * 1024


class SanaSpaceError(RuntimeError):
    """Safe-to-display remote Space failure; never includes request headers."""


def generation_data(prompt: str, seconds: str | int, seed: int = 42) -> list:
    key = str(seconds)
    if key not in PROFILES:
        raise SanaSpaceError("SANA distant accepte uniquement les profils validés de 5 ou 8 secondes.")
    if not prompt or not prompt.strip():
        raise SanaSpaceError("Le prompt vidéo est requis.")
    # These match the Space's exposed Gradio schema. The French source prompt is
    # passed verbatim; score 20 and RL scale 0.7 are the validated model defaults.
    return [prompt, PROFILES[key][0], 0.7, 20, int(seed), False]


def _named_result(payload):
    """Gradio may wrap the (video, seed) tuple in one or more lists."""
    while isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict) and ("url" in first or "path" in first):
            return first
        payload = first
    if isinstance(payload, dict) and "video" in payload:
        return _named_result(payload["video"])
    if isinstance(payload, dict) and "result" in payload:
        return _named_result(payload["result"])
    if isinstance(payload, dict) and ("url" in payload or "path" in payload):
        return payload
    if isinstance(payload, dict):
        raise SanaSpaceError("Le Space n'a pas fourni de fichier vidéo dans son résultat.")
    raise SanaSpaceError("Le Space a retourné un résultat vidéo inattendu.")


def _trusted_file_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.netloc == urlparse(BASE_URL).netloc and parsed.path.startswith("/gradio_api/file=")


async def _call(client: httpx.AsyncClient, endpoint: str, data: list, on_progress=None):
    response = await client.post(f"{BASE_URL}/gradio_api/call/{endpoint}", json={"data": data})
    response.raise_for_status()
    event_id = response.json().get("event_id")
    if not event_id:
        raise SanaSpaceError("Le Space n'a pas retourné d'identifiant de tâche.")
    result = None
    async with client.stream("GET", f"{BASE_URL}/gradio_api/call/{endpoint}/{quote(event_id)}", headers={"Accept": "text/event-stream"}) as stream:
        stream.raise_for_status()
        event = ""
        async for line in stream.aiter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
                if on_progress and event in ("generating", "heartbeat"):
                    await on_progress("SANA distant · génération GPU en cours…")
                elif on_progress and event == "complete":
                    await on_progress("SANA distant · récupération du MP4…")
            elif line.startswith("data:") and event in ("complete", "error"):
                raw = line[5:].strip()
                if event == "error":
                    # Do not surface arbitrary remote diagnostics or credential-like data.
                    raise SanaSpaceError("Le Space distant a échoué pendant le traitement; consultez son journal privé.")
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise SanaSpaceError("Réponse Gradio invalide.") from exc
                break
    if result is None:
        raise SanaSpaceError("Le Space a fermé le flux sans résultat.")
    return result


async def status(token: str) -> dict:
    if not token:
        return {"available": False, "reason": "Jeton HF privé non configuré côté backend.", "model": MODEL}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        timeout = httpx.Timeout(20, connect=8)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            info = await client.get(f"{BASE_URL}/gradio_api/info")
            info.raise_for_status()
            endpoints = info.json().get("named_endpoints", {})
            if "/generate" not in endpoints or "/engine_status" not in endpoints:
                return {"available": False, "reason": "API SANA attendue absente du Space privé.", "model": MODEL}
            status_result = await _call(client, "engine_status", [])
            value = status_result
            while isinstance(value, list) and value:
                value = value[0]
            if not isinstance(value, dict):
                return {"available": False, "reason": "Statut distant invalide.", "model": MODEL}
            ready = value.get("generation_ready") is True and "t2v" in value.get("supported_generation_tasks", [])
            return {
                "available": ready,
                "space": SPACE_ID,
                "model": MODEL,
                "provider": "Calcul distant Hugging Face Space privé; quota ZeroGPU partagé, restant non exposé.",
                "supported_tasks": ["t2v"] if ready else [],
                "durations_seconds": [5, 8] if ready else [],
                "resolution": "1280x736",
                "fps_profiles": {"5": 16, "8": 24},
                "i2v": False,
                "reason": value.get("reason", "SANA prêt." if ready else "SANA non prêt."),
                "quota_remaining_seconds": None,
                "paid_fallback": False,
            }
    except Exception as exc:
        return {"available": False, "reason": f"Space privé inaccessible ({type(exc).__name__}).", "model": MODEL}


async def generate(
    prompt: str,
    seconds: str | int,
    token: str,
    on_progress: Callable[[str], Awaitable[None]],
) -> tuple[bytes, dict]:
    data = generation_data(prompt, seconds)
    if not token:
        raise SanaSpaceError("Jeton HF privé non configuré côté backend.")
    started = time.monotonic()
    headers = {"Authorization": f"Bearer {token}"}
    timeout = httpx.Timeout(900, connect=15, read=900, write=120, pool=15)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        info = await client.get(f"{BASE_URL}/gradio_api/info")
        info.raise_for_status()
        endpoints = info.json().get("named_endpoints", {})
        spec = endpoints.get("/generate")
        if not spec:
            raise SanaSpaceError("L'API T2V /generate n'est pas exposée par le Space.")
        names = [p.get("parameter_name") for p in spec.get("parameters", [])]
        allowed = {"prompt", "video_duration", "rl_lora_scale", "motion_score", "seed", "randomize_seed"}
        if not names or any(n not in allowed for n in names):
            raise SanaSpaceError("Le schéma de génération SANA a changé; aucun travail GPU n'a été soumis.")
        params = dict(zip(("prompt", "video_duration", "rl_lora_scale", "motion_score", "seed", "randomize_seed"), data))
        payload = await _call(client, "generate", [params[name] for name in names], on_progress)
        file_data = _named_result(payload)
        url = file_data.get("url")
        if not isinstance(url, str) or not _trusted_file_url(url):
            raise SanaSpaceError("Le résultat ne pointe pas vers un fichier du Space attendu.")
        content = bytearray()
        async with client.stream("GET", url) as download:
            download.raise_for_status()
            if download.headers.get("content-type", "").split(";")[0].lower() != "video/mp4":
                raise SanaSpaceError("Le Space n'a pas retourné un MP4.")
            async for chunk in download.aiter_bytes(1024 * 1024):
                content.extend(chunk)
                if len(content) > MAX_MP4_BYTES:
                    raise SanaSpaceError("Le MP4 distant dépasse la limite de récupération autorisée.")
    report = verify_mp4(bytes(content))
    profile = PROFILES[str(seconds)]
    report.update({
        "provider": "Hugging Face private Space (remote GPU)",
        "space": SPACE_ID,
        "model": MODEL,
        "requested_prompt_verbatim": prompt,
        "requested_mode": "text",
        "requested_duration_seconds": int(seconds),
        "output_fps": profile[2],
        "output_frames_expected": profile[1],
        "quota_remaining_seconds": None,
        "quota_note": "Le quota ZeroGPU est partagé au niveau du compte; le restant n'est pas exposé par l'API Space.",
        "elapsed_wall_seconds": round(time.monotonic() - started, 3),
    })
    return bytes(content), report
