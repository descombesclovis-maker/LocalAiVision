"""Build the redistributable kit from an explicit, reviewed source manifest.

Do not walk the installation directory: it may contain private projects, outputs,
local environments or credentials. The same manifest is shipped with the kit so
this also works in an installation without Git. A missing/unsafe entry fails the
whole export rather than falling back to a directory scan.
"""

import io
import stat
import zipfile
from pathlib import Path, PurePosixPath

MANIFEST = "backend/kit_manifest.txt"
SKIP_FILES = frozenset({".env", ".api_key", ".boot_token", "yarn-error.log", "credentials.json", "id_rsa", "id_ed25519"})
SKIP_DIRS = frozenset({
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache", ".vite",
    ".emergent", ".screenshots", "bench_runs", "benchmarks", "dist", "build", "output", "outputs",
    "uploads", "userdata", "user_data", "backups", "data", "tests",
})
PRIVATE_SUFFIXES = frozenset({
    ".pyc", ".pyo", ".key", ".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db", ".bson",
    ".dump", ".jsonl", ".log", ".safetensors", ".ckpt", ".gguf", ".pt", ".pth", ".onnx",
    ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm",
})
_MAX_FILE_BYTES = 8 * 1024 * 1024
_MAX_KIT_BYTES = 32 * 1024 * 1024
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class KitExportError(RuntimeError):
    """The release manifest or an entry is missing or unsafe."""


def _validate_name(name: str) -> PurePosixPath:
    # Manifest and ZIP paths are always relative POSIX paths, including on Windows.
    if not name or "\\" in name or ":" in name or "\x00" in name:
        raise KitExportError("invalid manifest path")
    path = PurePosixPath(name)
    if path.is_absolute() or path.as_posix() != name or any(p in {"", ".", ".."} for p in path.parts):
        raise KitExportError("invalid manifest path")
    parts = [p.casefold() for p in path.parts]
    filename = parts[-1]
    if any(p in SKIP_DIRS for p in parts[:-1]):
        raise KitExportError("private directory in manifest")
    if filename in SKIP_FILES or filename.startswith(".env."):
        raise KitExportError("private file in manifest")
    if path.suffix.casefold() in PRIVATE_SUFFIXES:
        raise KitExportError("private or generated file type in manifest")
    # The source-code package backend/models is not a model weights directory.
    if "models" in parts[:-1] and not (parts[:2] == ["backend", "models"] and path.suffix.casefold() == ".py"):
        raise KitExportError("model directory in manifest")
    return path


def _checked_file(root: Path, rel: PurePosixPath) -> Path:
    """Reject symlinks, Windows junctions/reparse points, hard links and non-files."""
    current = root
    try:
        for index, part in enumerate(rel.parts):
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
                raise KitExportError("link or reparse point in manifest path")
            if index < len(rel.parts) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    raise KitExportError("manifest parent is not a directory")
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise KitExportError("manifest entry is not a private regular file")
        if info.st_size > _MAX_FILE_BYTES:
            raise KitExportError("manifest file exceeds size limit")
        return current
    except OSError as exc:
        raise KitExportError("manifest entry is inaccessible") from exc


def build_kit(root: Path) -> io.BytesIO:
    """Return a ZIP in memory, or raise KitExportError without exporting a partial kit."""
    root = Path(root).resolve(strict=True)
    manifest_path = _checked_file(root, _validate_name(MANIFEST))
    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise KitExportError("manifest is unreadable") from exc
    paths = []
    seen = set()
    total = 0
    for line in lines:
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        rel = _validate_name(name)
        folded = rel.as_posix().casefold()
        if folded in seen:
            raise KitExportError("duplicate manifest path")
        seen.add(folded)
        source = _checked_file(root, rel)
        total += source.stat().st_size
        if total > _MAX_KIT_BYTES:
            raise KitExportError("kit exceeds size limit")
        paths.append((source, rel))
    if MANIFEST.casefold() not in seen or not paths:
        raise KitExportError("manifest must include itself")
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source, rel in paths:
                archive.write(source, f"LocalAiStudio/{rel.as_posix()}")
    except OSError as exc:
        raise KitExportError("manifest entry could not be read") from exc
    buf.seek(0)
    return buf
