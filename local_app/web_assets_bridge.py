"""Safe, explicit transfer of generated media to a LocalAiWeb project.

A transfer only copies a user-selected local ComfyUI output to the project.
It does not publish the content, overwrite project files, or expose private
media to third-party APIs. The generated-file library stays independent.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import uuid
import time

ALLOWED={".png",".jpg",".jpeg",".webp",".gif",".mp4",".webm",".mov"}
MAX_SIZE=120*1024*1024


def _valid_magic(path):
    with path.open("rb") as stream:
        first=stream.read(16)
    suffix=path.suffix.lower()
    if suffix==".png":return first.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in (".jpg",".jpeg"):return first.startswith(b"\xff\xd8\xff")
    if suffix==".webp":return first.startswith(b"RIFF") and first[8:12]==b"WEBP"
    if suffix==".gif":return first.startswith((b"GIF87a",b"GIF89a"))
    if suffix in (".mp4",".mov"):return first[4:8]==b"ftyp"
    if suffix==".webm":return first.startswith(bytes.fromhex("1a45dfa3"))
    return False


def import_generation(store,comfy_root,project_id,filename,subfolder="",kind="output"):
    if kind!="output":
        raise ValueError("Seules les générations finales peuvent être transférées.")
    meta=store.meta(project_id)
    if not comfy_root:
        raise RuntimeError("Le dossier ComfyUI n'a pas été trouvé sur ce PC.")
    base=(Path(comfy_root)/"output").resolve()
    if not base.is_dir():
        raise FileNotFoundError("Le dossier de sorties ComfyUI est introuvable.")
    if not isinstance(filename,str) or not filename or len(filename)>160 or Path(filename).name!=filename:
        raise ValueError("Nom de génération invalide.")
    if Path(filename).suffix.lower() not in ALLOWED:
        raise ValueError("Format non pris en charge pour le site web.")
    if not isinstance(subfolder,str) or len(subfolder)>170 or "\x00" in subfolder:
        raise ValueError("Sous-dossier invalide.")
    target=(base/subfolder/filename).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError("Le fichier sélectionné est absent ou en dehors des sorties ComfyUI.")
    size=target.stat().st_size
    if size<8 or size>MAX_SIZE or not _valid_magic(target):
        raise ValueError("Fichier multimédia incorrect, trop volumineux ou format non reconnu.")
    asset_dir=store.project_dir(project_id)/"site"/"assets"/"ai"
    asset_dir.mkdir(parents=True,exist_ok=True)
    saved_name="creation-"+uuid.uuid4().hex[:12]+target.suffix.lower()
    dest=(asset_dir/saved_name).resolve()
    site=(store.project_dir(project_id)/"site").resolve()
    if not dest.is_relative_to(site):
        raise ValueError("Dossier d'importation invalide.")
    shutil.copy2(target,dest)
    rel="assets/ai/"+saved_name
    # Keep the source untouched and record an asset that can be referenced
    # by Claude Code or directly in the editor using its relative path.
    imports=list(meta.get("asset_imports") or [])
    imports.append({"path":rel,"source":"LocalAiVision","size":size,"created_at":time.time()})
    meta["asset_imports"]=imports[-200:]
    meta["updated_at"]=time.time()
    store.write_meta(project_id,meta)
    store.append_chat(project_id,"assistant",
        "Nouvelle ressource locale importée depuis LocalAiVision : "+rel+
        ". Elle est disponible dans les fichiers du site. Demande-moi où l'intégrer.")
    return {"ok":True,"project_id":project_id,"path":rel,"size":size,
            "note":"Ressource copiée au site. Aucune publication automatique."}
