"""fal.ai video generation via the Emergent integration proxy (universal key).

Fal Universal Key supports queue inference through Emergent proxy only, not Fal Platform APIs.
Submit is never retried automatically; status/result GETs retry transient network errors.
"""
import asyncio
import os
from typing import Any
from urllib.parse import urlparse

import httpx

QUEUE_ORIGIN = "https://queue.fal.run"

VIDEO_MODELS: dict[str, dict[str, Any]] = {
    "veo": {
        "label": "Veo 3.1 Fast",
        "tagline": "Rapide, génère aussi le son",
        "t2v": "fal-ai/veo3.1/fast",
        "i2v": "fal-ai/veo3.1/fast/image-to-video",
        "durations": ["4s", "6s", "8s"],
        "aspects": ["16:9", "9:16"],
        "audio": True,
    },
    "kling": {
        "label": "Kling 2.5 Turbo Pro",
        "tagline": "Qualité premium, idéal pour animer une image",
        "t2v": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
        "i2v": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
        "durations": ["5", "10"],
        "aspects": ["16:9", "9:16", "1:1"],
        "audio": False,
    },
    "minimax": {
        "label": "MiniMax Hailuo 02",
        "tagline": "Le plus rapide et économique pour tester",
        "t2v": "fal-ai/minimax/hailuo-02/standard/text-to-video",
        "i2v": "fal-ai/minimax/hailuo-02/standard/image-to-video",
        "durations": ["6", "10"],
        "aspects": ["16:9"],
        "audio": False,
    },
}


class FalError(Exception):
    pass


class InsufficientCredits(FalError):
    pass


def _bases() -> tuple[str, str]:
    base = os.environ.get("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com").rstrip("/")
    control = f"{base}/api/v1/fal"
    return control, f"{control}/queue"


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {os.environ['EMERGENT_LLM_KEY']}", "Content-Type": "application/json"}
    if os.environ.get("job_id"):
        h["X-App-ID"] = h["X-Job-ID"] = os.environ["job_id"]
    if os.environ.get("run_id"):
        h["X-Environment-ID"] = os.environ["run_id"]
    if extra:
        h.update(extra)
    return h


def _trusted(url: str) -> str:
    _, queue_base = _bases()
    c, q = urlparse(url), urlparse(queue_base)
    if c.scheme != q.scheme or c.netloc != q.netloc or c.username or c.password or c.fragment or not c.path.startswith(q.path.rstrip("/") + "/"):
        raise FalError("URL de file non fiable renvoyée par le proxy")
    return url


def build_payload(model: str, mode: str, prompt: str, duration: str, aspect: str, image_url: str | None) -> tuple[str, dict]:
    cfg = VIDEO_MODELS[model]
    if duration not in cfg["durations"]:
        duration = cfg["durations"][0]
    endpoint = cfg["i2v"] if mode == "image" else cfg["t2v"]
    payload: dict[str, Any] = {"prompt": prompt, "duration": duration}
    if model == "veo":
        payload.update({"aspect_ratio": aspect if aspect in cfg["aspects"] else "16:9", "generate_audio": True, "resolution": "720p"})
    elif model == "kling" and mode != "image":
        payload["aspect_ratio"] = aspect if aspect in cfg["aspects"] else "16:9"
    elif model == "minimax":
        payload["prompt_optimizer"] = True
    if mode == "image":
        if not image_url:
            raise FalError("Une image de départ est requise")
        payload["image_url"] = image_url
    return endpoint, payload


async def submit(endpoint: str, payload: dict) -> dict[str, str]:
    control, _ = _bases()
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{control}/proxy", headers=_headers({"X-Fal-Target-Url": f"{QUEUE_ORIGIN}/{endpoint}"}), json=payload)
    if r.status_code == 402:
        raise InsufficientCredits("Solde de la clé universelle insuffisant pour cette vidéo")
    if r.status_code >= 400:
        raise FalError(f"Requête refusée ({r.status_code}) : {r.text[:300]}")
    s = r.json()
    return {
        "status_url": _trusted(s["status_url"]),
        "response_url": _trusted(s["response_url"]),
        "cancel_url": _trusted(s["cancel_url"]) if s.get("cancel_url") else "",
    }


async def get_json(url: str, timeout: int = 30) -> dict:
    delay = 1
    for attempt in range(5):
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.get(url, headers=_headers())
            if r.status_code >= 400 and r.status_code != 202:
                raise FalError(f"Erreur fal ({r.status_code}) : {r.text[:300]}")
            return r.json()
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as exc:
            if attempt == 4:
                raise FalError("Réseau indisponible pendant le suivi") from exc
            await asyncio.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")


async def cancel(url: str) -> None:
    if not url:
        return
    async with httpx.AsyncClient(timeout=30) as c:
        await c.put(url, headers=_headers())


async def download(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content
