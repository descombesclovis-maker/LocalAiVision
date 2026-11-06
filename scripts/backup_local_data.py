"""Offline, non-destructive backup. Run with Studio/ComfyUI/browser closed.

Pass the actual user data roots explicitly; no model downloads or migration.
Browser-exported JSON may be passed as another --source.
"""
import argparse
import os
import tempfile
import zipfile
from pathlib import Path


def backup(sources, destination):
    destination=Path(destination).resolve()
    sources=[Path(p).resolve(strict=True) for p in sources]
    if destination.exists():raise ValueError('La sauvegarde existe déjà : choisis un nouveau fichier.')
    if any(p.is_dir() and destination.is_relative_to(p) for p in sources):raise ValueError('La destination doit être hors des données sauvegardées.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.studio-backup-',dir=destination.parent);os.close(fd)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
            for index,source in enumerate(sources):
                for path in sorted(source.rglob('*')) if source.is_dir() else [source]:
                    if path.is_symlink():raise ValueError('Lien symbolique refusé : '+str(path))
                    if path.is_file():archive.write(path,str(Path(str(index)+'-'+source.name)/(path.relative_to(source) if source.is_dir() else path.name)))
        # Hard link is exclusive: an existing destination cannot be overwritten.
        os.link(temporary,destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',action='append',required=True)
    parser.add_argument('--destination',required=True)
    args=parser.parse_args();print(backup(args.source,args.destination))
