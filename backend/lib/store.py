"""Binary media storage in Mongo GridFS + shared helpers."""
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from lib.db import db

bucket = AsyncIOMotorGridFSBucket(db, bucket_name="mediafs")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


async def save_bytes(data: bytes, mime: str, filename: str) -> str:
    fid = await bucket.upload_from_stream(filename, data, metadata={"mime": mime})
    return str(fid)


async def read_bytes(fid: str) -> bytes:
    stream = await bucket.open_download_stream(ObjectId(fid))
    return await stream.read()


def ext_for(mime: str) -> str:
    return {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "video/mp4": "mp4"}.get(mime, "bin")


async def create_media(
    kind: str,
    source: str,
    prompt: str,
    model: str,
    status: str = "pending",
    **extra,
) -> dict:
    doc = {
        "id": new_id(),
        "kind": kind,
        "source": source,
        "prompt": prompt,
        "model": model,
        "status": status,
        "progress_label": "En file d'attente" if status == "pending" else "",
        "gridfs_id": None,
        "mime": None,
        "aspect_ratio": extra.pop("aspect_ratio", None),
        "duration": extra.pop("duration", None),
        "project_id": extra.pop("project_id", None),
        "error": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        **extra,
    }
    await db.media.insert_one(doc)
    return doc


async def finish_media(media_id: str, data: bytes, mime: str) -> None:
    fid = await save_bytes(data, mime, f"{media_id}.{ext_for(mime)}")
    await db.media.update_one(
        {"id": media_id},
        {"$set": {"gridfs_id": fid, "mime": mime, "status": "done", "progress_label": "Terminé", "updated_at": now_iso()}},
    )


def media_url(media_id: str) -> str:
    return f"/api/media/{media_id}/file"
