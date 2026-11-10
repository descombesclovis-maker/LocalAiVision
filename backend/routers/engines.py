import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from lib import comfy, diagnostic, gpu_queue
from lib.db import db
from lib.kit_export import KitExportError, build_kit
from lib.store import now_iso
from models.engines import ComfySettings, ComfyTest, Diagnostic, EnginePresets, KitInfo, QueueState

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


@router.get("/diagnostic", response_model=Diagnostic)
async def run_diagnostic(request: Request):
    host = (request.headers.get("x-forwarded-host") or request.url.hostname or "").split(":")[0]
    return await diagnostic.run(host)


@router.get("/settings/comfyui", response_model=ComfySettings)
async def get_comfy():
    return await comfy.get_settings()


@router.put("/settings/comfyui", response_model=ComfySettings)
async def put_comfy(body: ComfySettings):
    try:
        return await comfy.save_settings(body.model_dump())
    except comfy.ComfyError as exc:
        raise HTTPException(422, str(exc))


@router.post("/settings/comfyui/test", response_model=ComfyTest)
async def test_comfy(body: ComfySettings):
    return await comfy.test(body.model_dump())


@router.get("/settings/comfyui/image-models")
async def image_models():
    """Installed state of each image preset (True/False, None = ComfyUI list unavailable)."""
    return await comfy.image_model_status(await comfy.get_settings())


@router.get("/settings/comfyui/video-models")
async def video_models():
    """Installed state of video presets and camera controls discovered from ComfyUI."""
    return await comfy.video_model_status(await comfy.get_settings())


@router.get("/settings/comfyui/presets", response_model=EnginePresets)
async def presets():
    return {
        "image": [{"key": k, "label": v["label"], "files": {"image_checkpoint": v["checkpoint"]}} for k, v in comfy.IMAGE_PRESETS.items()],
        "video": [
            {"key": k, "label": v["label"], "files": {"video_model": v["model"], "video_text_encoder": v["text_encoder"], "video_vae": v["vae"]}}
            for k, v in comfy.VIDEO_PRESETS.items()
        ],
    }


INSTALLER = ROOT / "local-kit" / "installer" / "Output" / "Installer-LocalAiStudio.exe"


def _build_installer() -> None:
    """Recompile the NSIS installer from the current sources when makensis is available (a few seconds)."""
    if not shutil.which("makensis"):
        return
    INSTALLER.parent.mkdir(exist_ok=True)
    subprocess.run(["makensis", "-V1", f"-DROOT={ROOT}", "LocalAiStudio.nsi"], cwd=INSTALLER.parents[1], capture_output=True, timeout=240)


@router.get("/kit/info", response_model=KitInfo)
async def kit_info():
    if not INSTALLER.exists():
        await asyncio.to_thread(_build_installer)
    ok = INSTALLER.exists()
    return {"installer_available": ok, "installer_size_mb": round(INSTALLER.stat().st_size / 1024**2, 1) if ok else 0}


@router.get("/kit/installer")
async def download_installer():
    await asyncio.to_thread(_build_installer)
    if not INSTALLER.exists():
        raise HTTPException(404, "Installateur non compilé : utilisez le kit .zip puis installer\\build-installer.bat")
    return FileResponse(INSTALLER, media_type="application/vnd.microsoft.portable-executable", filename=INSTALLER.name)


@router.get("/kit/download")
async def download_kit():
    try:
        buf = await asyncio.to_thread(build_kit, ROOT)
    except KitExportError as exc:
        logger.warning("Export du kit refusé : %s", exc)
        raise HTTPException(503, "Kit indisponible : manifeste de distribution invalide ou incomplet") from exc
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": 'attachment; filename="LocalAiStudio-kit-windows.zip"'})


@router.get("/queue", response_model=QueueState)
async def queue_state():
    return await gpu_queue.snapshot()


@router.post("/queue/{job_id}/prioritize", response_model=QueueState)
async def queue_prioritize(job_id: str):
    if not await gpu_queue.prioritize(job_id):
        raise HTTPException(409, "Ce rendu n'est plus en attente")
    return await gpu_queue.snapshot()


@router.post("/queue/{job_id}/cancel", response_model=QueueState)
async def queue_cancel(job_id: str):
    if await gpu_queue.cancel(job_id):
        await db.media.update_one({"id": job_id}, {"$set": {"status": "cancelled", "progress_label": "Annulée", "updated_at": now_iso()}})
        return await gpu_queue.snapshot()
    if gpu_queue.is_active(job_id):
        if await db.media.find_one({"id": job_id}, {"_id": 1}):
            from routers.media import cancel_media
            await cancel_media(job_id)
            return await gpu_queue.snapshot()
        raise HTTPException(409, "Un site en cours de génération ne peut pas être interrompu ; attendez la fin de l'étape")
    raise HTTPException(404, "Rendu introuvable dans la file")
