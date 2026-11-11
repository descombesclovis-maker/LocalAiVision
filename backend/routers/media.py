import asyncio
import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from lib import comfy, fal, gpu_queue
from lib.photo_prompt import comfy_photo_prompt
from lib.db import db
from lib.llm import friendly_error, generate_image
from lib.pipeline import spawn
from lib.store import create_media, finish_media, media_url, new_id, now_iso, read_bytes
from models.schemas import Activity, AdComposeRequest, Brand, BrandCreate, HuggingFaceTokenRequest, HuggingFaceTokenStatus, HuggingFaceVideoStatus, ImageRequest, Media, SmartMotionRequest, UploadRequest, VideoModel, VideoRequest
from lib import hf_video, hf_sana, secure_secret

router = APIRouter()
log = logging.getLogger("media")


def _out(d: dict) -> dict:
    d = {k: v for k, v in d.items() if k not in ("_id", "fal", "comfy")}
    d["url"] = media_url(d["id"]) if d.get("status") == "done" else None
    return d


COMFY_VIDEO = {"label": "LocalAi Video Engine — Gratuit", "tagline": "Wan 2.1 génératif local · T2V et I2V selon le modèle installé", "durations": ["3", "5", "6", "9", "12", "20", "30"], "aspects": ["16:9", "9:16", "1:1"], "audio": False}


async def _ref_b64(mid: str | None) -> tuple[str | None, str | None]:
    if not mid:
        return None, None
    md = await db.media.find_one({"id": mid})
    if not md or not md.get("gridfs_id") or md["kind"] != "image":
        raise HTTPException(400, "Image de référence introuvable")
    return base64.b64encode(await read_bytes(md["gridfs_id"])).decode(), md["mime"]


def _err(exc: Exception) -> str:
    return friendly_error(exc)


@router.get("/media", response_model=list[Media])
async def list_media(kind: str = "", source: str = ""):
    flt: dict = {"status": {"$ne": "cancelled"}}
    if kind:
        flt["kind"] = kind
    if source:
        flt["source"] = source
    docs = await db.media.find(flt, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [_out(d) for d in docs]


@router.get("/media/models/video", response_model=list[VideoModel])
async def video_models():
    paid = [{"key": k, **{f: v[f] for f in ("label", "tagline", "durations", "aspects", "audio")}} for k, v in fal.VIDEO_MODELS.items()]
    smartmotion = {"key": "smartmotion", "label": "SmartMotion · local 2.5D", "tagline": "Animation de caméra à partir d'une image fixe; ne génère pas de mouvement d'objet.", "durations": ["5", "10", "15", "20", "30"], "aspects": ["1:1", "16:9"], "audio": False}
    cloud = {"key": "hf_ltx", "label": "Cloud gratuit · LTX Video", "tagline": "Calcul distant; quota partagé limité, disponibilité et qualité variables.", "durations": ["2"], "aspects": ["1:1"], "audio": False}
    return [cloud, {"key": "comfy", **COMFY_VIDEO}, smartmotion, *paid]


@router.get("/media/models/hf-ltx", response_model=HuggingFaceVideoStatus)
async def hf_ltx_status():
    result = await hf_video.status()
    result["auth_configured"] = bool(await db.settings.find_one({"id": "hf_api_token"}, {"_id": 0, "ciphertext": 1}))
    return result


async def _saved_hf_token() -> str:
    """Read and DPAPI-decrypt the server-side HF credential; never log or return it."""
    saved = await db.settings.find_one({"id": "hf_api_token"}, {"_id": 0, "ciphertext": 1})
    if not saved or not saved.get("ciphertext"):
        return ""
    try:
        return secure_secret.decrypt_secret(saved["ciphertext"])
    except Exception as exc:
        log.warning("Stored Hugging Face credential could not be decrypted (%s)", type(exc).__name__)
        return ""


@router.get("/media/models/private-sana")
async def private_sana_status():
    token = await _saved_hf_token()
    result = await hf_sana.status(token)
    result["credential_configured"] = bool(token)
    return result


@router.get("/settings/huggingface-token", response_model=HuggingFaceTokenStatus)
async def get_hf_token_status():
    configured = bool(await db.settings.find_one({"id": "hf_api_token"}, {"_id": 0, "ciphertext": 1}))
    return {"configured": configured, "storage": "Windows DPAPI · compte Windows courant", "note": "Le jeton n'est pas envoyé au Space public ZeroGPU afin d'éviter toute consommation de crédits ou facturation hors quota gratuit. Il est conservé chiffré pour les appels privés futurs."}


@router.put("/settings/huggingface-token", response_model=HuggingFaceTokenStatus)
async def save_hf_token(body: HuggingFaceTokenRequest):
    token = body.token.strip()
    if not token.startswith("hf_") or len(token) < 20:
        raise HTTPException(400, "Jeton Hugging Face invalide (format hf_ attendu).")
    try:
        ciphertext = secure_secret.encrypt_secret(token)
    except Exception as exc:
        raise HTTPException(503, f"Stockage sécurisé indisponible : {str(exc)[:160]}") from exc
    await db.settings.update_one({"id": "hf_api_token"}, {"$set": {"ciphertext": ciphertext}}, upsert=True)
    return await get_hf_token_status()


@router.delete("/settings/huggingface-token", response_model=HuggingFaceTokenStatus)
async def delete_hf_token():
    await db.settings.delete_one({"id": "hf_api_token"})
    return await get_hf_token_status()


@lru_cache(maxsize=1)
def _smartmotion_runtime():
    from lib.smartmotion import local_runtime
    return local_runtime()


@lru_cache(maxsize=1)
def _ad_video_runtime() -> Path:
    """Find an already-installed media runtime without requiring SmartMotion weights or GPU availability."""
    from lib.smartmotion import runtime_candidates
    probe = "import importlib.util,sys; req=['av','PIL','numpy']; sys.exit(0 if all(importlib.util.find_spec(x) for x in req) else 1)"
    for interpreter in runtime_candidates():
        try:
            result = subprocess.run([str(interpreter), "-c", probe], capture_output=True, timeout=10)
            if result.returncode == 0:
                return interpreter
        except (OSError, subprocess.SubprocessError):
            continue
    raise RuntimeError("Export requires an existing Python runtime with PyAV, Pillow, and NumPy; no packages were installed")


@router.get("/media/models/smartmotion")
async def smartmotion_status():
    try:
        python, depth = await asyncio.to_thread(_smartmotion_runtime)
        return {"available": True, "reason": "Runtime local et modèle de profondeur déjà installés", "depth_model": depth.name}
    except Exception as exc:
        return {"available": False, "reason": str(exc)[:240]}


_SMARTMOTION_PROCS: dict[str, asyncio.subprocess.Process] = {}
_AD_COMPOSE_PROCS: dict[str, asyncio.subprocess.Process] = {}


def _smartmotion_progress_label(event: dict) -> str:
    if event.get("phase") == "verification":
        return "SmartMotion · vérification complète du MP4…"
    done, total = int(event["frames_done"]), int(event["frames_total"])
    pct = min(100, round(done * 100 / max(total, 1)))
    return f"SmartMotion · rendu {done}/{total} images ({pct}%)"


async def _run_smartmotion(mid: str, body: SmartMotionRequest, image_bytes: bytes, python: Path, depth_model: Path) -> None:
    try:
        async with gpu_queue.slot(mid, "video", "SmartMotion", body.prompt, "media"):
            await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "running", "progress_label": "SmartMotion · chargement local…", "updated_at": now_iso()}})
            with tempfile.TemporaryDirectory(prefix="localaistudio-smartmotion-") as temp:
                root = Path(temp)
                source = root / "reference.png"
                output = root / "output"
                source.write_bytes(image_bytes)
                output.mkdir()
                command = [str(python), "-m", "lib.smartmotion", "--input", str(source), "--output-dir", str(output),
                           "--depth-model", str(depth_model), "--seconds", str(body.seconds), "--fps", str(body.fps), "--motion", body.motion]
                if body.output_size != "source":
                    command.extend(["--output-size", body.output_size])
                env = os.environ.copy()
                env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"})
                proc = await asyncio.create_subprocess_exec(*command, cwd=str(Path(__file__).resolve().parents[1]), env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                _SMARTMOTION_PROCS[mid] = proc
                deadline = asyncio.get_running_loop().time() + 900
                last_output = ""
                while True:
                    remaining = deadline - asyncio.get_running_loop().time()
                    if remaining <= 0:
                        proc.kill()
                        await proc.wait()
                        raise TimeoutError("SmartMotion a dépassé le délai local de 15 minutes")
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    last_output = text[-1000:]
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if event.get("event") == "progress":
                        label = _smartmotion_progress_label(event)
                        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})
                returncode = await proc.wait()
                if returncode != 0:
                    current = await db.media.find_one({"id": mid}, {"_id": 0, "status": 1})
                    if current and current.get("status") == "cancelled":
                        return
                    raise RuntimeError(f"SmartMotion a échoué ({returncode}): {last_output or 'aucun détail fourni'}")
                video = output / "smartmotion.mp4"
                manifest_path = output / "manifest.json"
                if not video.is_file() or not manifest_path.is_file():
                    raise RuntimeError("SmartMotion n'a pas produit la vidéo et son manifeste")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                data = video.read_bytes()
                doc = await db.media.find_one({"id": mid})
                if doc and doc.get("status") != "cancelled":
                    await finish_media(mid, data, "video/mp4")
                    await db.media.update_one({"id": mid}, {"$set": {"generation_metrics": manifest, "progress_label": "SmartMotion terminé · MP4 vérifié", "updated_at": now_iso()}})
    except asyncio.CancelledError:
        proc = _SMARTMOTION_PROCS.get(mid)
        if proc and proc.returncode is None:
            proc.kill()
        raise
    except Exception as exc:
        log.warning("SmartMotion %s: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc)[:400], "progress_label": "Échec SmartMotion", "updated_at": now_iso()}})
    finally:
        _SMARTMOTION_PROCS.pop(mid, None)


@router.post("/media/smartmotion", response_model=Media)
async def create_smartmotion(body: SmartMotionRequest):
    try:
        python, depth_model = await asyncio.to_thread(_smartmotion_runtime)
    except Exception as exc:
        raise HTTPException(503, f"SmartMotion indisponible : {str(exc)[:220]}") from exc
    ref, mime = await _ref_b64(body.ref_media_id)
    if not ref:
        raise HTTPException(400, "SmartMotion nécessite une image de départ")
    image_bytes = base64.b64decode(ref)
    m = await create_media("video", "smartmotion", body.prompt, "SmartMotion · local 2.5D", aspect_ratio="source" if body.output_size == "source" else body.output_size, duration=f"{body.seconds}s")
    spawn(_run_smartmotion(m["id"], body, image_bytes, python, depth_model))
    return _out(m)


async def _run_ad_compose(mid: str, clips: list[tuple[str, bytes]], overlay: bytes, python: Path, title: str) -> None:
    proc = None
    try:
        async with gpu_queue.slot(mid, "video", "Montage publicitaire H.264", title, "media"):
            await db.media.update_one({"id": mid}, {"$set": {"status": "running", "progress_label": "Préparation du montage publicitaire…", "updated_at": now_iso()}})
            with tempfile.TemporaryDirectory(prefix="localaistudio-ad-") as temp:
                root = Path(temp)
                clip_paths = []
                for index, (clip_id, data) in enumerate(clips, 1):
                    path = root / f"plan-{index:02d}.mp4"
                    path.write_bytes(data)
                    clip_paths.append(path)
                overlay_path = root / "overlay.png"
                overlay_path.write_bytes(overlay)
                output = root / "advertisement.mp4"
                command = [str(python), "-m", "lib.ad_video", "--clips", *[str(p) for p in clip_paths], "--overlay", str(overlay_path), "--output", str(output), "--fps", "24"]
                env = os.environ.copy()
                env.update({"PYTHONIOENCODING": "utf-8", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
                proc = await asyncio.create_subprocess_exec(*command, cwd=str(Path(__file__).resolve().parents[1]), env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                _AD_COMPOSE_PROCS[mid] = proc
                last_output = ""
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    last_output = text[-800:]
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if event.get("event") == "progress":
                        done, total = int(event["frames_done"]), max(1, int(event["frames_total"]))
                        if event.get("phase") == "verification":
                            label = f"Montage publicitaire · vérification intégrale du MP4 ({done} images)"
                        else:
                            percent = min(99, round(done * 100 / total))
                            label = f"Montage publicitaire · assemblage {done}/{total} images ({percent}%)"
                        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})
                returncode = await proc.wait()
                current = await db.media.find_one({"id": mid}, {"_id": 0, "status": 1})
                if current and current.get("status") == "cancelled":
                    return
                if returncode != 0 or not output.is_file():
                    raise RuntimeError(f"Assemblage publicitaire impossible ({returncode}): {last_output or 'sortie absente'}")
                report_path = output.with_suffix(".json")
                report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {"codec": "h264_nvenc"}
                await finish_media(mid, output.read_bytes(), "video/mp4")
                duration = f"{report.get('duration_seconds', 0)}s"
                aspect = f"{report.get('width', 0)}:{report.get('height', 0)}"
                await db.media.update_one({"id": mid}, {"$set": {"generation_metrics": report, "duration": duration, "aspect_ratio": aspect, "progress_label": "Publicité terminée · MP4 vérifié", "updated_at": now_iso()}})
    except asyncio.CancelledError:
        proc = _AD_COMPOSE_PROCS.get(mid)
        if proc and proc.returncode is None:
            proc.kill()
        raise
    except Exception as exc:
        log.warning("ad compose %s: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc)[:400], "progress_label": "Échec du montage publicitaire", "updated_at": now_iso()}})
    finally:
        _AD_COMPOSE_PROCS.pop(mid, None)


@router.post("/media/ads/compose", response_model=Media)
async def compose_ad(body: AdComposeRequest):
    match = re.match(r"^data:image/png;base64,([A-Za-z0-9+/=]+)$", body.overlay_data_url, re.S)
    if not match:
        raise HTTPException(400, "Le calque publicitaire doit être un PNG transparent")
    try:
        overlay = base64.b64decode(match.group(1), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(400, "Calque PNG invalide") from exc
    if not overlay or len(overlay) > 12 * 1024 * 1024:
        raise HTTPException(413, "Le calque dépasse la limite de 12 Mo")
    clips: list[tuple[str, bytes]] = []
    for clip_id in dict.fromkeys(body.clip_media_ids):
        doc = await db.media.find_one({"id": clip_id, "kind": "video", "status": "done"})
        if not doc or not doc.get("gridfs_id"):
            raise HTTPException(400, f"Le plan vidéo {clip_id} est introuvable ou non terminé")
        clips.append((clip_id, await read_bytes(doc["gridfs_id"])))
    if not clips or len(clips) > 8:
        raise HTTPException(400, "Sélectionnez entre 1 et 8 plans vidéo terminés")
    try:
        python = await asyncio.to_thread(_ad_video_runtime)
    except Exception as exc:
        raise HTTPException(503, f"L'encodeur local est indisponible : {str(exc)[:200]}") from exc
    label = body.title.strip() or "Publicité"
    media = await create_media("video", "ad", label, "Montage publicitaire local · H.264", aspect_ratio="multi-plan" if len(clips) > 1 else None)
    spawn(_run_ad_compose(media["id"], clips, overlay, python, label))
    return _out(media)



@router.get("/media/{mid}", response_model=Media)
async def get_media(mid: str):
    d = await db.media.find_one({"id": mid}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Média introuvable")
    return _out(d)


@router.get("/media/{mid}/file")
async def media_file(mid: str):
    d = await db.media.find_one({"id": mid})
    if not d or not d.get("gridfs_id"):
        raise HTTPException(404, "Fichier indisponible")
    return Response(await read_bytes(d["gridfs_id"]), media_type=d["mime"], headers={"Cache-Control": "public, max-age=31536000, immutable"})


@router.delete("/media/{mid}")
async def delete_media(mid: str):
    res = await db.media.delete_one({"id": mid})
    if not res.deleted_count:
        raise HTTPException(404, "Média introuvable")
    return {"ok": True}


async def _comfy_image(mid: str, prompt: str, ref: str | None, aspect: str, ref_mime: str, comfy_preset: str | None = None) -> None:
    async def progress(label: str) -> None:
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})

    async def queued(prompt_id: str) -> None:
        await db.media.update_one({"id": mid}, {"$set": {"comfy": prompt_id}})

    await db.media.update_one({"id": mid}, {"$set": {"progress_label": "En file d'attente GPU", "updated_at": now_iso()}})
    try:
        # V1-C: verify_ready is called once here (in media.py) before the GPU slot.
        # generate_image() no longer calls it, eliminating the redundant second check.
        s = comfy.image_settings(await comfy.get_settings(), comfy_preset)
        await comfy.verify_ready(s, video=False)
        async with gpu_queue.slot(mid, "photo", "ComfyUI", prompt, "media"):
            await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "running", "progress_label": "Rendu local sur votre GPU…", "updated_at": now_iso()}})
            data, mime = await comfy.generate_image(prompt, aspect, (base64.b64decode(ref), ref_mime) if ref else None, progress, queued, preset=comfy_preset)
        d = await db.media.find_one({"id": mid})
        if d and d["status"] != "cancelled":
            await finish_media(mid, data, mime)
    except gpu_queue.JobCancelled:
        pass
    except comfy.ComfyUnreachable as exc:
        log.warning("comfy image %s: ComfyUI inaccessible: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "ComfyUI inaccessible", "updated_at": now_iso()}})
    except comfy.ModelListUnavailable as exc:
        log.warning("comfy image %s: liste des modèles indisponible: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "Liste des modèles indisponible", "updated_at": now_iso()}})
    except comfy.MissingModel as exc:
        log.warning("comfy image %s: modèle manquant: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "Modèle manquant", "updated_at": now_iso()}})
    except Exception as exc:
        log.warning("comfy image %s: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": _err(exc), "progress_label": "Échec", "updated_at": now_iso()}})


async def _run_image(mid: str, prompt: str, model: str, ref: str | None, aspect: str = "1:1", ref_mime: str = "image/png", comfy_preset: str | None = None) -> None:
    if model == "comfy":
        return await _comfy_image(mid, prompt, ref, aspect, ref_mime, comfy_preset)
    await db.media.update_one({"id": mid}, {"$set": {"status": "running", "progress_label": "Génération en cours…", "updated_at": now_iso()}})
    try:
        data, mime = await generate_image(prompt, model, ref, aspect=aspect, ref_mime=ref_mime)
        await finish_media(mid, data, mime)
    except Exception as exc:
        log.exception("image %s", mid)
        await db.media.update_one({"id": mid}, {"$set": {"status": "error", "error": _err(exc), "progress_label": "Échec", "updated_at": now_iso()}})


@router.post("/media/images", response_model=Media)
async def create_image(body: ImageRequest):
    ref, ref_mime = await _ref_b64(body.ref_media_id)
    if body.model == "comfy":
        full = comfy_photo_prompt(body.prompt)
    else:
        full = f"{body.prompt}. Aspect ratio {body.aspect_ratio}. High-end, detailed, no watermark."
        if ref:
            full = f"Transform the provided image: {body.prompt}. Keep composition quality. Aspect ratio {body.aspect_ratio}."
    m = await create_media("image", "photo", body.prompt, "local-comfyui" if body.model == "comfy" else body.model, aspect_ratio=body.aspect_ratio)
    spawn(_run_image(m["id"], full, body.model, ref, body.aspect_ratio, ref_mime or "image/png", body.comfy_preset))
    return _out(m)


async def _run_video(mid: str, endpoint: str, payload: dict) -> None:
    started = time.monotonic()
    try:
        q = await fal.submit(endpoint, payload)
        await db.media.update_one({"id": mid}, {"$set": {"fal": q, "status": "running", "progress_label": "Envoyé au moteur vidéo", "updated_at": now_iso()}})
        while time.monotonic() - started < 1200:
            d = await db.media.find_one({"id": mid})
            if not d or d["status"] == "cancelled":
                return
            st = await fal.get_json(q["status_url"])
            status = (st.get("status") or "").upper()
            elapsed = int(time.monotonic() - started)
            if status in ("COMPLETED", "OK"):
                if st.get("error"):
                    raise fal.FalError(str(st["error"]))
                await db.media.update_one({"id": mid}, {"$set": {"progress_label": "Récupération de la vidéo…"}})
                res = await fal.get_json(q["response_url"], 60)
                url = (res.get("video") or {}).get("url")
                if not url:
                    raise fal.FalError("Aucune vidéo dans la réponse")
                await finish_media(mid, await fal.download(url), "video/mp4")
                return
            if status in ("FAILED", "CANCELLED", "CANCELED", "ERROR"):
                raise fal.FalError(f"Génération {status.lower()}")
            label = f"En file d'attente (position {st.get('queue_position', '?')}) · {elapsed}s" if status == "IN_QUEUE" else f"Rendu en cours · {elapsed}s écoulées"
            await db.media.update_one({"id": mid}, {"$set": {"progress_label": label, "updated_at": now_iso()}})
            await asyncio.sleep(4)
        raise fal.FalError("Délai dépassé (20 min)")
    except Exception as exc:
        log.exception("video %s", mid)
        msg = str(exc) if isinstance(exc, fal.InsufficientCredits) else _err(exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": msg, "progress_label": "Échec", "updated_at": now_iso()}})


async def _run_comfy_video(mid: str, body: VideoRequest, ref: tuple[bytes, str] | None) -> None:
    async def progress(label: str) -> None:
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})

    async def queued(prompt_id: str) -> None:
        await db.media.update_one({"id": mid}, {"$set": {"comfy": prompt_id, "progress_label": "Envoyé à ComfyUI"}})

    async def metrics(report: dict) -> None:
        await db.media.update_one({"id": mid}, {"$set": {"generation_metrics": report, "updated_at": now_iso()}})

    await db.media.update_one({"id": mid}, {"$set": {"progress_label": "En file d'attente GPU", "updated_at": now_iso()}})
    try:
        # V1-C: verify_ready is called once here (in media.py) before the GPU slot.
        # generate_video() no longer calls it, eliminating the redundant second check.
        # Apply the requested video preset BEFORE verification so the correct models are checked.
        s = await comfy.get_settings()
        if body.comfy_preset:
            s = comfy.video_settings(s, body.comfy_preset)
        await comfy.verify_ready(s, video=True)
        async with gpu_queue.slot(mid, "video", "ComfyUI", body.prompt, "media"):
            await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "running", "updated_at": now_iso()}})
            data, mime = await comfy.generate_video(body.prompt, body.duration, body.aspect_ratio, ref, progress, queued, camera_pose=body.camera_pose, preset=body.comfy_preset, on_metrics=metrics)
        d = await db.media.find_one({"id": mid})
        if d and d["status"] != "cancelled":
            await finish_media(mid, data, mime)
    except gpu_queue.JobCancelled:
        pass
    except comfy.ComfyUnreachable as exc:
        log.warning("comfy video %s: ComfyUI inaccessible: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "ComfyUI inaccessible", "updated_at": now_iso()}})
    except comfy.ModelListUnavailable as exc:
        log.warning("comfy video %s: liste des modèles indisponible: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "Liste des modèles indisponible", "updated_at": now_iso()}})
    except comfy.MissingModel as exc:
        log.warning("comfy video %s: modèle manquant: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc), "progress_label": "Modèle manquant", "updated_at": now_iso()}})
    except Exception as exc:
        log.warning("comfy video %s: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc)[:400], "progress_label": "Échec", "updated_at": now_iso()}})


_HF_VIDEO_TASKS: dict[str, asyncio.Task] = {}
_SANA_CLOUD_TASKS: dict[str, asyncio.Task] = {}
_SANA_CLOUD_LOCK = asyncio.Lock()


async def _run_sana_video(mid: str, prompt: str, seconds: str, token: str) -> None:
    async def progress(label: str) -> None:
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})
    try:
        await progress("SANA distant · attente du service…")
        # This cloud task deliberately does not enter gpu_queue: no local GPU is used.
        async with _SANA_CLOUD_LOCK:
            await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "running", "progress_label": "SANA distant · requête envoyée…", "updated_at": now_iso()}})
            data, report = await hf_sana.generate(prompt, seconds, token, progress)
        current = await db.media.find_one({"id": mid}, {"_id": 0, "status": 1})
        if current and current.get("status") != "cancelled":
            await finish_media(mid, data, "video/mp4")
            await db.media.update_one({"id": mid}, {"$set": {"generation_metrics": report, "progress_label": "SANA distant · MP4 vérifié", "updated_at": now_iso()}})
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.warning("Private SANA Space request failed (%s)", type(exc).__name__)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc)[:400], "progress_label": "Échec du moteur vidéo distant", "updated_at": now_iso()}})
    finally:
        _SANA_CLOUD_TASKS.pop(mid, None)


async def _run_hf_video(mid: str, body: VideoRequest, ref: tuple[bytes, str] | None) -> None:
    async def progress(label: str) -> None:
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"progress_label": label, "updated_at": now_iso()}})
    try:
        await progress("Cloud vidéo · vérification du service distant…")
        async with gpu_queue.slot(mid, "video", "Cloud vidéo", body.prompt, "media"):
            await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "running", "progress_label": "Cloud vidéo · préparation…", "updated_at": now_iso()}})
            data, report = await hf_video.generate(body.prompt, body.mode, int(body.duration), body.aspect_ratio, ref, progress)
        current = await db.media.find_one({"id": mid}, {"_id": 0, "status": 1})
        if current and current.get("status") != "cancelled":
            await finish_media(mid, data, "video/mp4")
            await db.media.update_one({"id": mid}, {"$set": {"generation_metrics": report, "progress_label": "Cloud gratuit · MP4 distant vérifié", "updated_at": now_iso()}})
    except gpu_queue.JobCancelled:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        log.warning("Hugging Face video %s: %s", mid, exc)
        await db.media.update_one({"id": mid, "status": {"$ne": "cancelled"}}, {"$set": {"status": "error", "error": str(exc)[:400], "progress_label": "Échec du service cloud vidéo", "updated_at": now_iso()}})
    finally:
        _HF_VIDEO_TASKS.pop(mid, None)


@router.post("/media/videos", response_model=Media)
async def create_video(body: VideoRequest):
    if body.model == "hf_sana":
        if body.mode != "text":
            raise HTTPException(400, "SANA 4-step prend en charge uniquement le texte → vidéo; aucun repli I2V n'est effectué.")
        if body.duration not in ("5", "8"):
            raise HTTPException(400, "SANA distant prend uniquement en charge les profils validés de 5 ou 8 secondes.")
        if body.aspect_ratio != "16:9":
            raise HTTPException(400, "SANA distant utilise son profil validé 1280×736, proche de 16:9.")
        token = await _saved_hf_token()
        if not token:
            raise HTTPException(503, "Enregistrez un jeton Hugging Face privé dans les réglages sécurisés pour accéder au Space.")
        remote = await hf_sana.status(token)
        if not remote.get("available"):
            raise HTTPException(503, "Moteur SANA distant indisponible : " + str(remote.get("reason", "statut non disponible"))[:240])
        media = await create_media("video", "hf-private-space", body.prompt, hf_sana.MODEL, aspect_ratio="16:9", duration=f"{body.duration}s")
        task = asyncio.create_task(_run_sana_video(media["id"], body.prompt, body.duration, token))
        _SANA_CLOUD_TASKS[media["id"]] = task
        return _out(media)
    if body.model == "hf_ltx":
        status = await hf_video.status()
        if not status["available"]:
            raise HTTPException(503, "Cloud gratuit Hugging Face indisponible : " + status["detail"])
        if body.duration != "2":
            raise HTTPException(400, "Cloud LTX : seul le réglage 2 s / 256×256 a été validé par un MP4 réel. Les autres durées/résolutions restent expérimentales.")
        if body.aspect_ratio != "1:1":
            raise HTTPException(400, "Cloud LTX : seul le format carré 1:1 a été validé.")
        if body.mode != "text":
            raise HTTPException(400, "Le Space expose un endpoint I2V, mais aucun rendu I2V n'a été validé; seul le T2V est activé.")
        ref = None
        label = hf_video.MODEL_LABEL
        media = await create_media("video", "hf-zerogpu", body.prompt, label, aspect_ratio=body.aspect_ratio, duration=f"{body.duration}s")
        task = asyncio.create_task(_run_hf_video(media["id"], body, ref))
        _HF_VIDEO_TASKS[media["id"]] = task
        return _out(media)
    if body.model == "comfy":
        if body.comfy_preset == "wan21_fun_camera" and body.mode != "image":
            raise HTTPException(400, "Wan 2.1 Fun Camera nécessite une image de départ (Image → vidéo).")
        if body.duration not in COMFY_VIDEO["durations"]:
            raise HTTPException(400, f"Durée non prise en charge : {body.duration}. Choisissez parmi {', '.join(COMFY_VIDEO['durations'])} s.")
        if body.aspect_ratio not in COMFY_VIDEO["aspects"]:
            raise HTTPException(400, f"Format non pris en charge : {body.aspect_ratio}. Choisissez parmi {', '.join(COMFY_VIDEO['aspects'])}.")
        if body.comfy_preset == "wan21_t2v" and body.mode != "text":
            raise HTTPException(400, "Wan 2.1 T2V 1.3B est T2V uniquement. Pour I2V, sélectionnez Wan 2.1 Fun Camera.")
        ref = None
        if body.mode == "image":
            b64, mime = await _ref_b64(body.ref_media_id)
            if not b64:
                raise HTTPException(400, "Choisissez une image de départ")
            ref = (base64.b64decode(b64), mime or "image/png")
        m = await create_media("video", "video", body.prompt, "local-comfyui", aspect_ratio=body.aspect_ratio, duration=f"{body.duration}s")
        spawn(_run_comfy_video(m["id"], body, ref))
        return _out(m)
    if body.model in fal.VIDEO_MODELS and not body.paid_cost_acknowledged:
        estimate = fal.estimated_cost_usd(body.model, body.duration)
        raise HTTPException(402, f"Confirmation requise : estimation publique fal.ai {estimate:.2f} USD pour cette durée. Les tarifs réellement débités par le fournisseur/proxy peuvent varier; aucun appel n'a été soumis. Confirmez le coût dans l'interface pour continuer.")
    image_url = None
    if body.mode == "image":
        ref, mime = await _ref_b64(body.ref_media_id)
        if not ref:
            raise HTTPException(400, "Choisissez une image de départ")
        image_url = f"data:{mime};base64,{ref}"
    try:
        endpoint, payload = fal.build_payload(body.model, body.mode, body.prompt, body.duration, body.aspect_ratio, image_url)
    except fal.FalError as exc:
        raise HTTPException(400, str(exc))
    m = await create_media(
        "video", "video", body.prompt, fal.VIDEO_MODELS[body.model]["label"],
        aspect_ratio=payload.get("aspect_ratio", body.aspect_ratio if body.mode == "text" else "auto"), duration=payload["duration"],
    )
    spawn(_run_video(m["id"], endpoint, payload))
    return _out(m)


@router.post("/media/{mid}/cancel", response_model=Media)
async def cancel_media(mid: str):
    d = await db.media.find_one({"id": mid})
    if not d:
        raise HTTPException(404, "Média introuvable")
    if d["status"] not in ("pending", "running"):
        raise HTTPException(400, "Cette génération n'est plus en cours")
    await gpu_queue.cancel(mid)
    sana_task = _SANA_CLOUD_TASKS.get(mid)
    if sana_task and not sana_task.done():
        sana_task.cancel()  # Stops local polling; the remote Space may continue its already-started GPU job.
    smartmotion_proc = _SMARTMOTION_PROCS.get(mid) or _AD_COMPOSE_PROCS.get(mid)
    if smartmotion_proc and smartmotion_proc.returncode is None:
        smartmotion_proc.terminate()
    if d.get("comfy"):
        try:
            await comfy.cancel(d["comfy"])
        except Exception:
            log.warning("comfy cancel failed for %s", mid)
    if d.get("fal", {}).get("cancel_url"):
        try:
            await fal.cancel(d["fal"]["cancel_url"])
        except Exception:
            log.warning("cancel failed for %s", mid)
    await db.media.update_one({"id": mid}, {"$set": {"status": "cancelled", "progress_label": "Annulée", "updated_at": now_iso()}})
    return _out(await db.media.find_one({"id": mid}, {"_id": 0}))


@router.post("/media/upload", response_model=Media)
async def upload(body: UploadRequest):
    m = re.match(r"^data:(image/(?:png|jpeg|webp));base64,(.+)$", body.data_url, re.S)
    if not m:
        raise HTTPException(400, "Format d'image non pris en charge (PNG, JPEG ou WebP)")
    data = base64.b64decode(m.group(2))
    if len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "Image trop lourde (12 Mo max)")
    doc = await create_media("image", body.source, body.prompt or body.source, "import", status="running")
    await finish_media(doc["id"], data, m.group(1))
    return _out(await db.media.find_one({"id": doc["id"]}, {"_id": 0}))


@router.get("/activity", response_model=Activity)
async def activity():
    items = []
    for p in await db.projects.find({"status": {"$in": ["queued", "generating", "editing"]}}, {"_id": 0, "id": 1, "name": 1, "status": 1, "steps": 1}).to_list(50):
        run = next((s for s in p.get("steps", []) if s["status"] == "running"), None)
        label = "Modification en cours" if p["status"] == "editing" else (run["label"] if run else "En préparation")
        items.append({"id": p["id"], "kind": "site", "name": p.get("name") or "Nouveau site", "status": p["status"], "label": label})
    for d in await db.media.find({"status": {"$in": ["pending", "running"]}, "source": {"$ne": "site"}}, {"_id": 0}).to_list(50):
        items.append({"id": d["id"], "kind": d["kind"], "name": d["prompt"][:60], "status": d["status"], "label": d.get("progress_label", "")})
    return {"count": len(items), "items": items}


# ------------------------------------------------------------------ brands

@router.get("/brands", response_model=list[Brand])
async def list_brands():
    return await db.brands.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/brands", response_model=Brand)
async def create_brand(body: BrandCreate):
    doc = {"id": new_id(), **body.model_dump(), "created_at": now_iso()}
    await db.brands.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/brands/{bid}", response_model=Brand)
async def update_brand(bid: str, body: BrandCreate):
    res = await db.brands.update_one({"id": bid}, {"$set": body.model_dump()})
    if not res.matched_count:
        raise HTTPException(404, "Marque introuvable")
    return await db.brands.find_one({"id": bid}, {"_id": 0})


@router.delete("/brands/{bid}")
async def delete_brand(bid: str):
    res = await db.brands.delete_one({"id": bid})
    if not res.deleted_count:
        raise HTTPException(404, "Marque introuvable")
    return {"ok": True}
