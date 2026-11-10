"""Materialize the reviewed release kit into a NEW directory, without Git.

Existing editions, source trees, reparse-point paths and existing targets are refused.
This copies application source only, never databases, models, secrets or environments.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from lib.kit_export import build_kit  # noqa: E402

_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _overlaps(a: Path, b: Path) -> bool:
    return a == b or a in b.parents or b in a.parents


def _guard_target(source: Path, target: Path) -> Path:
    source = source.resolve(strict=True)
    target = Path(os.path.abspath(target))
    # Do not follow a junction, symlink or other Windows reparse point to reach the destination.
    for parent in (target, *target.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
            raise ValueError(f"Destination contains a link or junction: {parent}")
    if target.exists():
        raise FileExistsError(f"Destination already exists; nothing overwritten: {target}")
    resolved = target.resolve(strict=False)
    protected = [source]
    if os.environ.get("LOCALAPPDATA"):
        editions = Path(os.environ["LOCALAPPDATA"]) / "LocalAiStudio-Editions"
        protected.extend((editions / "NextGen-Avant-Fusion", editions / "NextGen-V2E"))
    for entry in protected:
        if _overlaps(resolved, entry.resolve(strict=False)):
            raise ValueError(f"Destination must not overlap an existing source or edition: {entry}")
    return target


def materialize(source: Path, target: Path) -> int:
    source = Path(source).resolve(strict=True)
    target = _guard_target(source, target)
    archive_bytes = build_kit(source)  # validate all entries before creating target
    target.mkdir(parents=True, exist_ok=False)
    count = 0
    with zipfile.ZipFile(archive_bytes) as archive:
        for info in archive.infolist():
            parts = Path(info.filename).parts
            if not parts or parts[0] != "LocalAiStudio" or len(parts) < 2:
                raise ValueError("Unexpected release archive path")
            destination = target.joinpath(*parts[1:])
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    count = materialize(args.source, args.target)
    print(f"Materialized {count} reviewed source files into {args.target}")


if __name__ == "__main__":
    main()
