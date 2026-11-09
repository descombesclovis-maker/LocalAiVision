import io
import re
import zipfile
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from lib.db import db
from lib.pipeline import files_list, files_map, initial_steps, pages_from, render, run_edit, run_pipeline, snapshot, spawn
from lib.store import ext_for, media_url, new_id, now_iso, read_bytes
from models.schemas import ChatRequest, FileUpdate, Project, ProjectCreate, ProjectSummary, ProjectUpdate, Version

router = APIRouter()


def _summary(d: dict) -> dict:
    d = {k: v for k, v in d.items() if k != "_id"}
    d["thumbnail_url"] = media_url(d["thumbnail_id"]) if d.get("thumbnail_id") else None
    return d


async def _get(pid: str) -> dict:
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Projet introuvable")
    return p


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(q: str = "", mode: str = ""):
    flt: dict = {}
    if q:
        flt["$or"] = [{"name": {"$regex": re.escape(q), "$options": "i"}}, {"prompt": {"$regex": re.escape(q), "$options": "i"}}]
    if mode in ("libre", "pro"):
        flt["mode"] = mode
    docs = await db.projects.find(flt, {"_id": 0, "files": 0, "messages": 0, "images": 0}).sort("updated_at", -1).to_list(500)
    return [_summary(d) for d in docs]


@router.post("/projects", response_model=Project)
async def create_project(body: ProjectCreate):
    return await start_project(body)


async def start_project(body: ProjectCreate, extra: Optional[dict] = None) -> dict:
    ts = now_iso()
    doc = {
        "id": new_id(),
        "name": body.name.strip(),
        "prompt": body.prompt.strip(),
        "mode": body.mode,
        "llm": body.llm,
        "engine": body.engine,
        "hero_video": body.hero_video and body.mode == "pro",
        "brand_id": body.brand_id,
        "style": body.style.model_dump() if body.style else None,
        "status": "queued",
        "site_type": "",
        "steps": initial_steps(),
        "pages": [],
        "files": [],
        "messages": [{"role": "user", "content": body.prompt.strip(), "created_at": ts}],
        "asset_ids": [],
        "version": 0,
        "created_at": ts,
        "updated_at": ts,
        **(extra or {}),
    }
    await db.projects.insert_one(doc)
    spawn(run_pipeline(doc["id"]))
    return _summary(doc)


@router.get("/projects/{pid}", response_model=Project)
async def get_project(pid: str):
    return _summary(await _get(pid))


@router.patch("/projects/{pid}", response_model=Project)
async def update_project(pid: str, body: ProjectUpdate):
    await _get(pid)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd:
        upd["updated_at"] = now_iso()
        await db.projects.update_one({"id": pid}, {"$set": upd})
    return _summary(await _get(pid))


@router.delete("/projects/{pid}")
async def delete_project(pid: str):
    await _get(pid)
    await db.projects.delete_one({"id": pid})
    await db.versions.delete_many({"project_id": pid})
    return {"ok": True}


@router.post("/projects/{pid}/retry", response_model=Project)
async def retry(pid: str):
    p = await _get(pid)
    if p["status"] in ("generating", "editing"):
        raise HTTPException(409, "Une génération est déjà en cours")
    steps = [s if s["status"] == "done" else {**s, "status": "pending", "detail": ""} for s in p["steps"]]
    await db.projects.update_one({"id": pid}, {"$set": {"steps": steps, "status": "queued", "error": None}})
    spawn(run_pipeline(pid))
    return _summary(await _get(pid))


@router.post("/projects/{pid}/chat", response_model=Project)
async def chat(pid: str, body: ChatRequest):
    p = await _get(pid)
    if p["status"] in ("generating", "editing", "queued"):
        raise HTTPException(409, "Une génération est déjà en cours sur ce projet")
    await db.projects.update_one({"id": pid}, {"$push": {"messages": {"role": "user", "content": body.message, "created_at": now_iso()}}})
    if p["status"] == "needs_input" or (p["status"] == "error" and not p.get("files")):
        steps = [s if s["status"] == "done" else {**s, "status": "pending", "detail": ""} for s in p["steps"]]
        await db.projects.update_one({"id": pid}, {"$set": {"answer": body.message, "status": "queued", "steps": steps}, "$unset": {"brief": ""}})
        spawn(run_pipeline(pid))
    else:
        await db.projects.update_one({"id": pid}, {"$set": {"status": "editing", "updated_at": now_iso()}})
        spawn(run_edit(pid, body.message, body.page, body.selection.model_dump() if body.selection else None, body.media_ids))
    return _summary(await _get(pid))


@router.put("/projects/{pid}/files", response_model=Project)
async def save_file(pid: str, body: FileUpdate):
    p = await _get(pid)
    m = files_map(p)
    if body.path not in m:
        raise HTTPException(404, "Fichier introuvable")
    if m[body.path] == body.content:
        return _summary(p)
    m[body.path] = body.content
    await db.projects.update_one({"id": pid}, {"$set": {"files": files_list(m), "pages": pages_from(m), "updated_at": now_iso()}})
    await snapshot(pid, f"Modification manuelle · {body.path}")
    return _summary(await _get(pid))


@router.get("/projects/{pid}/versions", response_model=list[Version])
async def versions(pid: str):
    return await db.versions.find({"project_id": pid}, {"_id": 0, "files": 0}).sort("number", -1).to_list(500)


async def _restore(pid: str, number: int, label: str) -> dict:
    v = await db.versions.find_one({"project_id": pid, "number": number})
    if not v:
        raise HTTPException(404, "Version introuvable")
    m = {f["path"]: f["content"] for f in v["files"]}
    await db.projects.update_one({"id": pid}, {"$set": {"files": v["files"], "pages": pages_from(m), "updated_at": now_iso()}})
    await snapshot(pid, label)
    return _summary(await _get(pid))


@router.post("/projects/{pid}/versions/{number}/restore", response_model=Project)
async def restore(pid: str, number: int):
    await _get(pid)
    return await _restore(pid, number, f"Restauration de la version {number}")


@router.post("/projects/{pid}/undo", response_model=Project)
async def undo(pid: str):
    p = await _get(pid)
    if p.get("version", 0) < 2:
        raise HTTPException(400, "Aucune version précédente")
    return await _restore(pid, p["version"] - 1, "Annulation")


@router.get("/preview/{pid}/{path:path}")
async def preview(pid: str, path: str, v: Optional[int] = Query(default=None)):
    p = await _get(pid)
    if v:
        ver = await db.versions.find_one({"project_id": pid, "number": v})
        m = {f["path"]: f["content"] for f in ver["files"]} if ver else files_map(p)
    else:
        m = files_map(p)
    path = path or "index.html"
    if path not in m:
        raise HTTPException(404, "Fichier introuvable")
    mime = {"html": "text/html", "css": "text/css", "js": "application/javascript"}.get(path.rsplit(".", 1)[-1], "text/plain")
    return Response(render(m, path), media_type=f"{mime}; charset=utf-8", headers={"Cache-Control": "no-store"})


@router.get("/projects/{pid}/export")
async def export_zip(pid: str):
    p = await _get(pid)
    m = files_map(p)
    buf = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        rendered = {k: render(m, k) for k in m if not k.startswith("_")}
        for k, c in rendered.items():
            used |= set(re.findall(r"/api/media/([0-9a-f-]{36})/file", c))
        exts: dict[str, str] = {}
        for mid in used:
            md = await db.media.find_one({"id": mid})
            if md and md.get("gridfs_id"):
                exts[mid] = ext_for(md["mime"])
                z.writestr(f"assets/{mid}.{exts[mid]}", await read_bytes(md["gridfs_id"]))
        for k, c in rendered.items():
            c = re.sub(r"/api/media/([0-9a-f-]{36})/file", lambda mm: f"assets/{mm.group(1)}.{exts.get(mm.group(1), 'png')}", c)
            z.writestr(k, c)
        z.writestr("README.txt", f"{p['name']}\nSite généré par LocalAiWeb · Site web créé par Forma.\nOuvrez index.html dans un navigateur.\nPanier, réservations et formulaires fonctionnent dans le navigateur uniquement (aucun paiement ni e-mail réel branché).\n")
    buf.seek(0)
    safe = re.sub(r"[^a-zA-Z0-9-]+", "-", p["name"]).strip("-").lower() or "site"
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{safe}.zip"'})
