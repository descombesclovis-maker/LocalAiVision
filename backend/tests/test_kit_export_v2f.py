"""Security and behaviour of the actual kit export; fixtures contain no user data."""

import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from lib.kit_export import KitExportError, build_kit


@pytest.fixture
def kit_root(tmp_path):
    files = {
        "backend/server.py": "# safe server\n",
        "frontend/src/main.tsx": "// safe ui\n",
        "installer/env.template": "DB_NAME=example\n",
        "install.ps1": "# safe installer\n",
    }
    for name, content in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest = tmp_path / "backend/kit_manifest.txt"
    manifest.write_text("\n".join([*files, "backend/kit_manifest.txt"]) + "\n", encoding="utf-8")
    # These realistic private paths sit next to, or inside, public source directories.
    private = [
        "backend/.api_key", "backend/.boot_token", "backend/.env", "backend/.env.production",
        "backend/.venv/Scripts/python.exe", "backend/bench_runs/private/photo.png",
        "backend/models/private.safetensors", "backend/uploads/client.jpg", "backend/lib/private.py",
        "frontend/.env.local", "frontend/node_modules/pkg/index.js", "frontend/src/customer-data.json",
        "frontend/.screenshots/home.png", "data/projects.db", "private.pem",
    ]
    for name in private:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("PRIVATE_SENTINEL", encoding="utf-8")
    return tmp_path


def names_and_contents(buf):
    with zipfile.ZipFile(buf) as archive:
        assert archive.testzip() is None
        return {n: archive.read(n) for n in archive.namelist()}


def test_only_explicit_release_files_are_exported(kit_root):
    result = names_and_contents(build_kit(kit_root))
    assert set(result) == {
        "LocalAiStudio/backend/server.py", "LocalAiStudio/frontend/src/main.tsx",
        "LocalAiStudio/installer/env.template", "LocalAiStudio/install.ps1",
        "LocalAiStudio/backend/kit_manifest.txt",
    }
    assert all(b"PRIVATE_SENTINEL" not in data for data in result.values())
    assert not any("/.env" in name.casefold() for name in result)


@pytest.mark.parametrize("bad", [
    "backend/.env", "backend/.ENV.PRODUCTION", "backend/.API_KEY", "backend/.boot_token",
    "backend/secret.pem", "backend/credential.pfx", "backend/.venv/x.py", "backend/bench_runs/x.py",
    "backend/models/model.safetensors", "frontend/node_modules/index.js", "backend/uploads/client.jpg",
    "frontend/src/private.jsonl", "backend/photo.PNG", "../outside.txt", "/absolute.txt",
    "C:/outside.txt", "backend/../outside.txt", "backend\\outside.txt", "backend//server.py",
])
def test_sensitive_or_invalid_manifest_entry_fails_closed(kit_root, bad):
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + bad + "\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)


def test_missing_entry_does_not_produce_partial_archive(kit_root):
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "frontend/src/missing.tsx\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)


def test_manifest_duplicate_is_rejected_case_insensitively(kit_root):
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "BACKEND/SERVER.PY\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)


def test_hardlink_to_private_content_is_not_exported(kit_root):
    src = kit_root / "backend/.api_key"
    link = kit_root / "frontend/src/safe-looking.tsx"
    try:
        os.link(src, link)
    except OSError as exc:
        pytest.skip(f"hard links unavailable on this filesystem: {exc}")
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "frontend/src/safe-looking.tsx\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)


def test_symlink_directory_is_not_exported(kit_root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("private-target")
    (outside / "source.tsx").write_text("PRIVATE_SENTINEL", encoding="utf-8")
    link = kit_root / "frontend/src/linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this system: {exc}")
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "frontend/src/linked/source.tsx\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junctions only")
def test_windows_junction_is_not_exported(kit_root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("private-junction-target")
    (outside / "source.tsx").write_text("PRIVATE_SENTINEL", encoding="utf-8")
    junction = kit_root / "frontend/src/linked"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True)
    if result.returncode:
        pytest.skip("Windows junction creation not available")
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "frontend/src/linked/source.tsx\n", encoding="utf-8")
    with pytest.raises(KitExportError):
        build_kit(kit_root)
    # Remove the junction only; never touch its target.
    junction.rmdir()
    assert (outside / "source.tsx").exists()


def test_actual_route_requires_auth_and_fails_closed(kit_root, monkeypatch):
    from starlette.testclient import TestClient
    from lib.auth import API_KEY
    from routers import engines
    import server

    monkeypatch.setattr(engines, "ROOT", kit_root)
    client = TestClient(server.app)  # no lifespan: no MongoDB writes
    assert client.get("/api/kit/download").status_code == 401
    response = client.get("/api/kit/download", headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert len(names_and_contents(io.BytesIO(response.content))) == 5
    manifest = kit_root / "backend/kit_manifest.txt"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "backend/.env\n", encoding="utf-8")
    refused = client.get("/api/kit/download", headers={"X-API-Key": API_KEY})
    assert refused.status_code == 503
    assert "PRIVATE_SENTINEL" not in refused.text


def test_real_release_manifest_produces_complete_kit():
    root = Path(__file__).resolve().parents[2]
    result = names_and_contents(build_kit(root))
    for required in ("install.ps1", "start-localaistudio.bat", "backend/server.py", "backend/lib/kit_export.py",
                     "frontend/package.json", "frontend/yarn.lock", "installer/LocalAiStudio.iss"):
        assert "LocalAiStudio/" + required in result
    assert not any("/.env" in n.casefold() or "/bench_runs/" in n.casefold() for n in result)
