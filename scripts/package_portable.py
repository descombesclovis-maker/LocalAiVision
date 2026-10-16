#!/usr/bin/env python3
"""Create release-ready ZIPs without accidentally including personal projects or AI weights."""
from __future__ import annotations

import argparse
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = "LocalAiVision-Source-Complet"
PORTABLE = "LocalAiVision-Portable-Windows"

README_SOURCE = """LOCAL AIVISION + LOCAL AIWEB — DOSSIER SOURCE COMPLET
====================================================
Version : code actuel du dépôt. Le modèle 3D photoréaliste (PBR, HDRI,
GLB compressés, qualité adaptative) figure dans
  local_app/web/templates/cinematic3d/

1) Décompresser l'intégralité de l'archive.
2) Sur Windows avec Python 3.11 : double-cliquer START_LOCAL_AI.bat.
3) Optionnel : INSTALLER_FENETRE_NATIVE.bat ajoute pywebview.
4) Pour compiler ton propre EXE : BUILD_LOCALVISIONAI.bat.

L'interface et les fichiers sont séparés de tout EXE précompilé.
Cette archive contient tout le code suivi dans Git, les interfaces,
les workflows et les tests ; elle ne contient NI les poids des modèles
IA (souvent plusieurs Go), NI ComfyUI, NI ton historique personnel.
Les modèles et projets déjà installés restent sous
%LOCALAPPDATA%\\LocalVisionAI. Ne supprime pas ce dossier.
Les moteurs IA doivent être installés ou configurés si nécessaire.
Three.js est chargé depuis un CDN : Internet requis pour les scènes WebGL.
Voir README_LOCAL_APP.md et local_app/web/templates/cinematic3d/README.md.
"""

README_PORTABLE = """LOCAL AIVISION + LOCAL AIWEB — DOSSIER WINDOWS PORTABLE
====================================================
Ce dossier contient l'application Windows exécutable avec ses ressources
(dans _internal). Il est INDÉPENDANT du .exe monofichier.
Il n'est pas nécessaire d'installer Python pour utiliser l'interface.

MODE D'EMPLOI
1) Extraire TOUS les fichiers du ZIP, ne rien retirer de _internal.
2) Fermer les autres instances de LocalVisionAI (port local 3000).
3) Double-cliquer sur LocalVisionAI.exe.
4) Ouvrir « Accéder à LocalAiWeb » en haut de l'application.
5) Cliquer « Site 3D » pour créer une expérience interactive.
6) Importer un modèle GLB dans Assets ; facultativement, un HDR pour
   améliorer les reflets et lumières.

IMPORTANT
- Les modèles IA, ComfyUI, CUDA, poids GPU et historiques personnels NE
  sont PAS inclus ; des installations complémentaires peuvent être
  nécessaires. Le logiciel réutilise les fichiers stockés sous
  %LOCALAPPDATA%\\LocalVisionAI.
- Ne supprime jamais tes dossiers de données et sauvegardes pour mettre
  à jour le programme. LocalAiWeb conserve ses projets séparément.
- Three.js et les décodeurs GLB sont chargés via CDN ; Internet est
  requis pour les scènes WebGL tant qu'ils ne sont pas empaquetés.
- La fluidité réelle des sites 3D dépend des modèles, textures,
  capacités GPU et navigateurs ; 60 FPS n'est pas garanti.
- Ce dossier fonctionne sur Windows x64 ; l'EXE n'a pas été testé ici
  sur ton ordinateur personnel.

Pour les sources modifiables, utiliser LocalAiVision-Source-Complet.zip.
"""

def source_zip(destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\x00")
    files = sorted(
        path for raw in tracked if raw
        if (path := ROOT / raw.decode("utf-8")).is_file()
    )
    if not any(p.name == "server.py" for p in files):
        raise RuntimeError("Missing required server source")
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as out:
        out.writestr(f"{SOURCES}/LISEZ_MOI_PORTABLE.txt", README_SOURCE.encode("utf-8"))
        for file in files:
            out.write(file, f"{SOURCES}/{file.relative_to(ROOT).as_posix()}")
    print(f"Source: {destination} ({len(files)} files, {destination.stat().st_size} bytes)")

def windows_portable_zip(destination: Path, dist: Path):
    executable = dist / "LocalVisionAI.exe"
    resources = dist / "_internal"
    if not executable.is_file() or not resources.is_dir():
        raise RuntimeError("PyInstaller onedir executable/resources missing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=7) as out:
        out.writestr(f"{PORTABLE}/LISEZ_MOI_PORTABLE.txt", README_PORTABLE.encode("utf-8"))
        for file in sorted(dist.rglob("*")):
            if file.is_file():
                out.write(file, f"{PORTABLE}/{file.relative_to(dist).as_posix()}")
    print(f"Portable: {destination} ({destination.stat().st_size} bytes)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["source", "windows"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--dist", default="dist/LocalVisionAI")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    source_zip(output) if args.kind == "source" else windows_portable_zip(output, (ROOT / args.dist).resolve())
