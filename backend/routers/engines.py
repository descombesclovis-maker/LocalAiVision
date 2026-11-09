import asyncio
import io
import shutil
import subprocess
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from lib import comfy, diagnostic, gpu_queue
from lib.db import db
from lib.store import now_iso
from models.engines import ComfySettings, ComfyTest, Diagnostic, EnginePresets, KitInfo, QueueState

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {"Output", "node_modules", "__pycache__", ".pytest_cache", "dist", ".vite", "tests", ".git", ".emergent", ".screenshots"}
SKIP_FILES = {".env", "yarn-error.log", ".api_key", ".boot_token"}
ENV_EXAMPLE = """MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=localaistudio
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
APP_TZ=Europe/Paris
# Optionnel — moteurs payants de secours (Claude, Nano Banana, Veo, Kling) :
# EMERGENT_LLM_KEY=
"""


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


@router.get("/settings/comfyui/presets", response_model=EnginePresets)
async def presets():
    return {
        "image": [{"key": k, "label": v["label"], "files": {"image_checkpoint": v["checkpoint"]}} for k, v in comfy.IMAGE_PRESETS.items()],
        "video": [
            {"key": k, "label": v["label"], "files": {"video_model": v["model"], "video_text_encoder": v["text_encoder"], "video_vae": v["vae"]}}
            for k, v in comfy.VIDEO_PRESETS.items()
        ],
    }


def _add_tree(z: zipfile.ZipFile, src: Path, arc: str) -> None:
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if any(part in SKIP_DIRS for part in rel.parts) or p.name in SKIP_FILES or p.suffix == ".pyc" or not p.is_file():
            continue
        z.write(p, f"{arc}/{rel.as_posix()}")


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
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        _add_tree(z, ROOT / "backend", "LocalAiStudio/backend")
        _add_tree(z, ROOT / "frontend", "LocalAiStudio/frontend")
        _add_tree(z, ROOT / "local-kit", "LocalAiStudio")
        z.writestr("LocalAiStudio/backend/.env", ENV_EXAMPLE)
        spec = ROOT / "memory" / "SPEC.md"
        if spec.exists():
            z.write(spec, "LocalAiStudio/SPEC.md")
    buf.seek(0)
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
