"""Source-only installation target guards (no database or GPU required)."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("las_materialize", ROOT / "scripts/materialize_kit.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def source(tmp_path):
    src = tmp_path / "source"
    (src / "backend").mkdir(parents=True)
    (src / "backend/server.py").write_text("safe source", encoding="utf-8")
    (src / "backend/.env").write_text("PRIVATE-SENTINEL", encoding="utf-8")
    (src / "backend/kit_manifest.txt").write_text("backend/kit_manifest.txt\nbackend/server.py\n", encoding="utf-8")
    return src


def test_only_reviewed_source_is_materialized(source, tmp_path):
    target = tmp_path / "new-edition"
    assert module.materialize(source, target) == 2
    assert (target / "backend/server.py").read_text() == "safe source"
    assert not (target / "backend/.env").exists()


def test_existing_target_is_never_overwritten(source, tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    sentinel = target / "user-data"
    sentinel.write_text("preserve")
    with pytest.raises(FileExistsError):
        module.materialize(source, target)
    assert sentinel.read_text() == "preserve" and len(list(target.iterdir())) == 1


def test_target_cannot_overlap_source(source):
    with pytest.raises(ValueError, match="overlap"):
        module.materialize(source, source / "nested-new")


def test_failure_to_validate_manifest_creates_no_target(source, tmp_path):
    (source / "backend/kit_manifest.txt").write_text("backend/kit_manifest.txt\nbackend/.env\n", encoding="utf-8")
    target = tmp_path / "not-created"
    with pytest.raises(Exception):
        module.materialize(source, target)
    assert not target.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junctions only")
def test_target_inside_junction_is_refused(source, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
    if proc.returncode:
        pytest.skip("junction creation unavailable")
    try:
        with pytest.raises(ValueError, match="junction"):
            module.materialize(source, link / "edition")
        assert not (outside / "edition").exists()
    finally:
        link.rmdir()  # only remove the test junction, not its target


def test_target_cannot_be_inside_legacy_edition(source, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    legacy = tmp_path / "LocalAiStudio-Editions/NextGen-Avant-Fusion"
    with pytest.raises(ValueError, match="overlap"):
        module.materialize(source, legacy / "new")
    assert not legacy.exists()
