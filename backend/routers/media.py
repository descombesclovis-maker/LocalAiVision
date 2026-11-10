import asyncio
import base64
import json
import logging
import os
import re
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
from models.schemas import Activity, Brand, BrandCreate, ImageRequest, Media, SmartMotionRequest, UploadRequest, VideoModel, VideoRequest

router = APIRouter()
log = logging.getLogger("media")


def _out(d: dict) -> dict:
    d = {k: v for k, v in d.items() if k not in ("_id", "fal", "comfy")}
    d["url"] = media_url(d["id"]) if d.get("status") == "done" else None
    return d


COMFY_VIDEO = {"label": "Local · ComfyUI", "tagline": "Gratuit, sur votre GPU (Wan 2.2 / LTX-Video)", "durations": ["3", "5"], "aspects": ["16:9", "9:16", "1:1"], "audio": False}


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
    return [{"key": "comfy", **COMFY_VIDEO}, smartmotion, *paid]


@lru_cache(maxsize=1)
def _smartmotion_runtime():
    from lib.smartmotion import local_runtime
    return local_runtime()


@router.get("/media/models/smartmotion")
async def smartmotion_status():
    try:
        python, depth = await asyncio.to_thread(_smartmotion_runtime)
        return {"available": True, "reason": "Runtime local et modèle de profondeur déjà installés", "depth_model": depth.name}
    except Exception as exc:
        return {"available": False, "reason": str(exc)[:240]}


_SMARTMOTION_PROCS: dict[str, asyncio.subprocess.Process] = {}


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


@router.post("/media/videos", response_model=Media)
async def create_video(body: VideoRequest):
    if body.model == "comfy":
        if body.comfy_preset == "wan21_fun_camera" and body.mode != "image":
            raise HTTPException(400, "Wan 2.1 Fun Camera nécessite une image de départ (Image → vidéo).")
        if body.duration not in COMFY_VIDEO["durations"]:
            body.duration = "3"
        if body.aspect_ratio not in COMFY_VIDEO["aspects"]:
            body.aspect_ratio = "16:9"
        ref = None
        if body.mode == "image":
            b64, mime = await _ref_b64(body.ref_media_id)
            if not b64:
                raise HTTPException(400, "Choisissez une image de départ")
            ref = (base64.b64decode(b64), mime or "image/png")
        m = await create_media("video", "video", body.prompt, "local-comfyui", aspect_ratio=body.aspect_ratio, duration=f"{body.duration}s")
        spawn(_run_comfy_video(m["id"], body, ref))
        return _out(m)
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
    smartmotion_proc = _SMARTMOTION_PROCS.get(mid)
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
