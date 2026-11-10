"""Hugging Face ZeroGPU connector using the Space's documented Gradio HTTP API."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Awaitable, Callable
from urllib.parse import quote

import httpx

SPACE_ID = "DeepRat/LTX-Video-ZeroGPU-Optimized"
BASE_URL = "https://deeprat-ltx-video-zerogpu-optimized.hf.space"
MODEL_LABEL = "Hugging Face ZeroGPU · LTX Video 0.9.8 13B Distilled"
FREE_QUOTA = "Ce connecteur appelle le Space sans jeton: quota ZeroGPU non authentifié officiel 2 min/jour (remise à zéro 24 h après la première utilisation). Avec compte Free authentifié: 5 min/jour, mais l'authentification est volontairement non utilisée pour empêcher toute facturation par crédits. Quota restant non exposé."
log = logging.getLogger("hf_video")


class HfVideoError(RuntimeError):
    pass


def verify_mp4(data: bytes) -> dict:
    """Reject truncated MP4s and extract movie duration / encoded track dimensions from ISO-BMFF boxes."""
    if len(data) < 64 or data[4:8] != b"ftyp":
        raise HfVideoError("Le fournisseur n'a pas retourné un conteneur MP4 valide (signature ftyp absente).")
    def parse_boxes(blob: bytes):
        result = []
        pos = 0
        while pos + 8 <= len(blob):
            size = int.from_bytes(blob[pos:pos + 4], "big")
            kind = blob[pos + 4:pos + 8]
            head = 8
            if size == 1:
                if pos + 16 > len(blob): break
                size = int.from_bytes(blob[pos + 8:pos + 16], "big"); head = 16
            elif size == 0:
                size = len(blob) - pos
            if size < head or pos + size > len(blob): break
            result.append((kind.decode("ascii", errors="replace"), blob[pos + head:pos + size], head))
            pos += size
        return result
    root = parse_boxes(data)
    boxes = [kind for kind, _, _ in root]
    if not {"ftyp", "moov", "mdat"}.issubset(set(boxes)) or sum(head + len(payload) for _, payload, head in root) != len(data):
        raise HfVideoError("MP4 distant incomplet : boîtes ftyp/moov/mdat manquantes ou tronquées.")
    duration = None
    dimensions = []
    def walk(children):
        nonlocal duration
        for kind, payload, _head in children:
            if kind == "mvhd" and len(payload) >= 20:
                version = payload[0]
                if version == 1 and len(payload) >= 32:
                    scale = int.from_bytes(payload[20:24], "big"); ticks = int.from_bytes(payload[24:32], "big")
                elif version == 0:
                    scale = int.from_bytes(payload[12:16], "big"); ticks = int.from_bytes(payload[16:20], "big")
                else: continue
                if scale: duration = ticks / scale
            elif kind == "tkhd" and len(payload) >= 8:
                w = int.from_bytes(payload[-8:-4], "big") >> 16; h = int.from_bytes(payload[-4:], "big") >> 16
                if w and h: dimensions.append({"width": w, "height": h})
            if kind in ("moov", "trak", "mdia", "minf", "stbl", "edts", "dinf"):
                walk(parse_boxes(payload))
    walk(root)
    return {"container": "mp4", "top_level_boxes": boxes, "bytes": len(data), "duration_seconds": round(duration, 3) if duration is not None else None, "video_tracks": dimensions, "structural_check": "ftyp/moov/mdat présents, tailles des boîtes cohérentes; durée et dimensions extraites si déclarées"}


async def status() -> dict:
    headers = {"Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=5), follow_redirects=True) as client:
            response = await client.get(f"{BASE_URL}/gradio_api/info", headers=headers)
            response.raise_for_status()
            info = response.json()
        endpoints = info.get("named_endpoints", {})
        t2v = "/text_to_video" in endpoints
        i2v = "/image_to_video" in endpoints
        return {"available": bool(t2v), "space": SPACE_ID, "model": "LTX Video 0.9.8 13B Distilled", "hardware": "Hugging Face ZeroGPU · calcul distant", "t2v": t2v, "i2v": i2v, "free_quota": FREE_QUOTA, "quota_remaining": None, "durations_seconds": [2], "limitations": ["Seul un MP4 1,9 s à 256×256 (demande 2 s) a été obtenu. La demande 3 s à 704×512 a échoué sans détail; ces paramètres ne sont pas proposés.", "Le Space annonce 0,3–8,5 s et jusqu'à 1280 px, mais les durées/résolutions supérieures ne sont pas validées.", "Le Space ajoute lui-même des mots anglais de vitesse au prompt et ne garantit pas une fidélité littérale.", "L'endpoint I2V existe, mais aucun MP4 I2V n'a été validé; I2V reste désactivé dans l'interface.", "Quota partagé limité; file d'attente publique et disponibilité variables.", "LTX-Video 0.9.x licence Open Weights avec restrictions d'usage; vérifier l'éligibilité de l'entité avant l'usage commercial."], "auth_configured": False, "detail": "API Gradio officielle joignable."}
    except Exception as exc:
        return {"available": False, "space": SPACE_ID, "model": "LTX Video 0.9.8 13B Distilled", "hardware": "Hugging Face ZeroGPU · calcul distant", "t2v": False, "i2v": False, "free_quota": FREE_QUOTA, "quota_remaining": None, "durations_seconds": [2], "limitations": [], "auth_configured": False, "detail": f"Space/API indisponible : {str(exc)[:200]}"}


async def _upload_image(client: httpx.AsyncClient, image: bytes, mime: str) -> str:
    filename = "reference.png" if mime == "image/png" else "reference.jpg"
    response = await client.post(f"{BASE_URL}/gradio_api/upload", files={"files": (filename, image, mime)})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], str):
        raise HfVideoError("Gradio n'a pas confirmé l'envoi de l'image de référence.")
    return payload[0]


async def generate(
    prompt: str,
    mode: str,
    seconds: int,
    aspect_ratio: str,
    image: tuple[bytes, str] | None,
    on_progress: Callable[[str], Awaitable[None]],
) -> tuple[bytes, dict]:
    if mode not in ("text", "image"):
        raise HfVideoError("Mode cloud non pris en charge.")
    if mode == "image" and not image:
        raise HfVideoError("Le mode Image → vidéo nécessite une image de référence.")
    if seconds != 2 or aspect_ratio != "1:1":
        raise HfVideoError("Seul le réglage cloud 2 s / 256×256 a été validé par un MP4 réel.")
    started = time.monotonic()
    width = height = 256
    timeout = httpx.Timeout(600, connect=15, read=600, write=120, pool=15)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        info_response = await client.get(f"{BASE_URL}/gradio_api/info")
        info_response.raise_for_status()
        endpoint = "/text_to_video" if mode == "text" else "/image_to_video"
        spec = info_response.json().get("named_endpoints", {}).get(endpoint)
        if not spec:
            raise HfVideoError(f"L'API officielle du Space n'expose pas {endpoint}.")
        uploaded_path = await _upload_image(client, image[0], image[1]) if image else ""
        values = {
            "prompt": prompt,
            "negative_prompt": "worst quality, inconsistent motion, blurry, jittery, distorted",
            "input_image_filepath": {"path": uploaded_path, "url": None, "meta": {"_type": "gradio.FileData"}} if image else "",
            "input_video_filepath": "",
            "height_ui": height,
            "width_ui": width,
            "mode": "text-to-video" if mode == "text" else "image-to-video",
            "duration_ui": float(seconds),
            "ui_frames_to_use": 9,
            "seed_ui": 42,
            "randomize_seed": False,
            "ui_guidance_scale": 1.0,
            "improve_texture_flag": False,
            "slow_motion_flag": False,
        }
        params = [p.get("parameter_name") for p in spec.get("parameters", [])]
        missing = [name for name in params if name not in values]
        if missing:
            raise HfVideoError(f"Schéma Gradio modifié : paramètres non reconnus {missing}.")
        response = await client.post(f"{BASE_URL}/gradio_api/call{endpoint}", json={"data": [values[n] for n in params]})
        response.raise_for_status()
        event_id = response.json().get("event_id")
        if not event_id:
            raise HfVideoError("L'API Gradio n'a pas retourné d'identifiant de génération.")
        await on_progress("Hugging Face ZeroGPU · requête soumise; attente du GPU distant…")
        events: list[str] = []
        async with client.stream("GET", f"{BASE_URL}/gradio_api/call{endpoint}/{quote(event_id)}", headers={"Accept": "text/event-stream"}) as stream:
            stream.raise_for_status()
            current_event = ""
            lines = stream.aiter_lines().__aiter__()
            pending_line = asyncio.create_task(anext(lines))
            while True:
                try:
                    line = await asyncio.wait_for(asyncio.shield(pending_line), timeout=15)
                except asyncio.TimeoutError:
                    elapsed = int(time.monotonic() - started)
                    await on_progress(f"Hugging Face ZeroGPU · flux distant en attente depuis {elapsed}s; position de file non exposée par le Space…")
                    continue
                except StopAsyncIteration:
                    break
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    if current_event == "complete":
                        await on_progress("Hugging Face ZeroGPU · génération terminée; récupération du MP4…")
                    elif current_event == "error":
                        await on_progress("Hugging Face ZeroGPU · traitement distant en échec")
                    elif current_event not in ("heartbeat", "generating"):
                        await on_progress(f"Hugging Face ZeroGPU · état distant : {current_event[:60]}")
                elif line.startswith("data:"):
                    events.append(line[5:].strip())
                    if current_event == "error":
                        detail = line[5:].strip()
                        if detail in ("null", '""', ""):
                            detail = "ZeroGPU a refusé ou interrompu le traitement (quota épuisé, file saturée ou erreur Space); la cause détaillée n'est pas exposée par ce Space. Aucun jeton n'est envoyé, donc aucun crédit payant n'est utilisé."
                        raise HfVideoError("Erreur du Space : " + detail[:300])
                pending_line = asyncio.create_task(anext(lines))
        if not events:
            raise HfVideoError("Le Space a fermé le flux sans résultat vidéo.")
        try:
            result = json.loads(events[-1])
            while isinstance(result, list) and result:
                result = result[0]
            video_data = result.get("video") if isinstance(result, dict) else None
            remote_url = video_data.get("url") if isinstance(video_data, dict) else None
        except Exception as exc:
            raise HfVideoError("Réponse vidéo Gradio inattendue.") from exc
        if not remote_url or not remote_url.startswith(BASE_URL + "/gradio_api/file="):
            raise HfVideoError("URL de sortie Gradio absente ou hors du domaine HF attendu.")
        download = await client.get(remote_url)
        download.raise_for_status()
        if download.headers.get("content-type", "").split(";")[0].lower() != "video/mp4":
            raise HfVideoError("Le téléchargement distant n'est pas typé video/mp4.")
        data = download.content
    report = verify_mp4(data)
    report.update({"provider": "Hugging Face ZeroGPU", "space": SPACE_ID, "model": "LTX Video 0.9.8 13B Distilled", "requested_prompt_verbatim": prompt, "requested_mode": mode, "requested_duration_seconds": seconds, "requested_width": width, "requested_height": height, "elapsed_wall_seconds": round(time.monotonic() - started, 3), "hf_quota_remaining": None, "quota_note": "ZeroGPU free-tier quota shared at account level; remaining quota is not exposed by this public Space API."})
    return data, report
