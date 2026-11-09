#!/usr/bin/env python3
"""Importer sans écrasement l'archive source officielle NextGen dans cette branche.

Usage: python scripts/import_nextgen_archive.py chemin/vers/LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip
Ne supprime aucun modèle et n'exécute ni installateur ni génération.
"""
import hashlib
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_SHA256 = "11ec72839c83489760775a981056e7a4f0123a8705efdf9f7d9a6380335e5357"
SKIP = {".env", ".git", "node_modules", "__pycache__", ".venv", "venv"}
REQUIRED = {"backend/server.py", "frontend/package.json", "frontend/src/App.tsx"}

def run(path):
    source = Path(path).resolve(strict=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError("Le ZIP ne correspond pas à la version vérifiée. Empreinte SHA-256 : " + digest)
    with zipfile.ZipFile(source) as z:
        files = {}
        for info in z.infolist():
            if info.is_dir():
                continue
            raw = info.filename.replace(chr(92), "/")
            parts = Path(raw).parts
            if Path(raw).is_absolute() or ".." in parts or not parts:
                raise RuntimeError("Chemin dangereux dans l'archive : " + raw)
            if any(p in SKIP for p in parts):
                continue
            if info.file_size > 5_000_000:
                raise RuntimeError("Fichier anormalement volumineux : " + raw)
            if raw.startswith("LocalAiStudio/"):
                raw = raw[len("LocalAiStudio/"):]
            files[raw] = z.read(info)
        if not REQUIRED.issubset(files):
            raise RuntimeError("Archive incomplète : " + ", ".join(sorted(REQUIRED - files.keys())))
        conflicts = []
        for name, data in files.items():
            target = (ROOT / name).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise RuntimeError("Sortie hors du dépôt : " + name)
            if target.exists() and target.read_bytes() != data:
                conflicts.append(name)
        if conflicts:
            raise RuntimeError("Import interrompu : fichiers existants différents (aucun écrasement). " + ", ".join(conflicts[:15]))
        for name, data in files.items():
            target = ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(data)
        print("Import terminé :", len(files), "fichiers; vérifie git status, puis lance les tests ciblés.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/import_nextgen_archive.py chemin/vers/archive.zip")
    run(sys.argv[1])
