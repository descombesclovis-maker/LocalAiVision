"""Guard the Windows runtime lock shipped in the clean installer kit."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def _packages(path: str) -> dict[str, str]:
    return {
        line.split(" --hash=")[0].split("==")[0].replace("_", "-").lower(): line.split(" --hash=")[0].split("==")[1]
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }


def test_python_runtime_is_fully_pinned_and_hash_locked():
    runtime = _packages("requirements-local.txt")
    assert runtime == _packages("requirements-windows-py311.lock")
    assert runtime["uvicorn"] == "0.52.1"
    assert runtime["websockets"] == "17.4"
    lines = (ROOT / "requirements-windows-py311.lock").read_text(encoding="utf-8").splitlines()
    assert all(re.fullmatch(r"[\w.-]+==[\w.+-]+ --hash=sha256:[0-9a-f]{64}", line)
               for line in lines if line and not line.startswith("#"))
    assert "emergentintegrations" not in runtime  # paid provider is optional, never required for local startup


def test_release_manifest_includes_lock_and_local_yarn():
    manifest = (ROOT / "backend/kit_manifest.txt").read_text(encoding="utf-8").splitlines()
    for name in ("requirements-local.txt", "requirements-windows-py311.lock",
                 "installer/tooling/package.json", "installer/tooling/package-lock.json"):
        assert name in manifest
    import json
    lock = json.loads((ROOT / "installer/tooling/package-lock.json").read_text(encoding="utf-8"))
    yarn = lock["packages"]["node_modules/yarn"]
    assert yarn["version"] == "1.22.22" and yarn["integrity"].startswith("sha512-")
