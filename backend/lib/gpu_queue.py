"""Single-slot GPU scheduler: ComfyUI renders and local (Ollama) site generations run one at a time, in priority order."""
import asyncio
import statistics
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from lib.db import db

DEFAULT_SECONDS = {"photo": 60, "video": 600, "site": 1200, "edit": 180}


class JobCancelled(Exception):
    pass


_cond = asyncio.Condition()
_waiting: dict[str, dict] = {}
_active: Optional[dict] = None
_cancelled: set[str] = set()


def _head() -> Optional[str]:
    return min(_waiting, key=lambda k: _waiting[k]["key"]) if _waiting else None


@asynccontextmanager
async def slot(job_id: str, kind: str, engine: str, label: str, ref: str) -> AsyncIterator[None]:
    """ref = 'media' | 'project' — what the job id points to."""
    global _active
    async with _cond:
        _waiting[job_id] = {"id": job_id, "kind": kind, "engine": engine, "label": label[:120], "ref": ref, "key": time.time(), "queued_at": time.time()}
        _cond.notify_all()
        while not (_active is None and _head() == job_id):
            if job_id in _cancelled:
                _cancelled.discard(job_id)
                _waiting.pop(job_id, None)
                _cond.notify_all()
                raise JobCancelled()
            await _cond.wait()
        job = _waiting.pop(job_id)
        _active = {**job, "started": time.time()}
    ok = False
    try:
        yield
        ok = True
    finally:
        seconds = time.time() - _active["started"]
        async with _cond:
            _active = None
            _cond.notify_all()
        if ok and seconds > 3:
            await db.render_stats.insert_one({"kind": kind, "seconds": round(seconds, 1), "at": datetime.now(timezone.utc).isoformat()})


async def cancel(job_id: str) -> bool:
    """Cancel a waiting job. Returns False if it's not waiting (running or unknown)."""
    async with _cond:
        if job_id not in _waiting:
            return False
        _cancelled.add(job_id)
        _cond.notify_all()
    return True


async def prioritize(job_id: str) -> bool:
    async with _cond:
        if job_id not in _waiting:
            return False
        _waiting[job_id]["key"] = min(j["key"] for j in _waiting.values()) - 1
        _cond.notify_all()
    return True


def is_active(job_id: str) -> bool:
    return bool(_active and _active["id"] == job_id)


async def _estimates() -> dict[str, tuple[float, int]]:
    out = {}
    for kind, default in DEFAULT_SECONDS.items():
        rows = await db.render_stats.find({"kind": kind}, {"_id": 0, "seconds": 1}).sort("at", -1).to_list(15)
        vals = [r["seconds"] for r in rows]
        out[kind] = (statistics.median(vals) if vals else default, len(vals))
    return out


async def snapshot() -> dict:
    est = await _estimates()
    now = time.time()
    items = []
    clock = 0.0
    if _active:
        typical, n = est[_active["kind"]]
        elapsed = now - _active["started"]
        remaining = max(typical - elapsed, 5)
        items.append({**_pub(_active), "status": "running", "position": 0, "elapsed_s": int(elapsed), "eta_s": int(remaining),
                      "start_in_s": 0, "typical_s": int(typical), "samples": n})
        clock = remaining
    for pos, job in enumerate(sorted(_waiting.values(), key=lambda j: j["key"]), start=1):
        typical, n = est[job["kind"]]
        items.append({**_pub(job), "status": "waiting", "position": pos, "elapsed_s": int(now - job["queued_at"]),
                      "eta_s": int(clock + typical), "start_in_s": int(clock), "typical_s": int(typical), "samples": n})
        clock += typical
    return {"items": items, "total_eta_s": int(clock)}


def _pub(j: dict) -> dict:
    return {k: j[k] for k in ("id", "kind", "engine", "label", "ref")}
