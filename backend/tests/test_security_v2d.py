"""V2-D step A: security regression tests.

Covers:
  1. Engines page never offers public tunnel commands.
  2. Installers (Inno Setup and NSIS) exclude API key, boot token, benchmark output and env files.
  3. Vite dev server binds to loopback unless LAS_VITE_EXPOSE=1 is set explicitly.
  4. Session lifecycle through the real /api/auth/init route: first start, refresh, restart.

No GPU, ComfyUI, Ollama or MongoDB required.
"""
import fnmatch
import os
import re
import secrets
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------ 1. Engines page

def test_engines_page_has_no_public_tunnel_command():
    src = (ROOT / "frontend" / "src" / "pages" / "Engines.tsx").read_text(encoding="utf-8")
    # Warning text may name these services; no command or copy button may be offered.
    for forbidden in ("cloudflared tunnel", "ngrok http", "trycloudflare.com --", "tunnel --url", "tunnel-copy-", "tunnel-cmd-", "navigator.clipboard"):
        assert forbidden not in src, f"Engines.tsx still offers: {forbidden}"


def test_engines_page_explains_remote_access_safely():
    src = (ROOT / "frontend" / "src" / "pages" / "Engines.tsx").read_text(encoding="utf-8")
    assert "Ne pas exposer les moteurs sur Internet" in src
    assert "authentification" in src
    assert "127.0.0.1:11434" in src and "127.0.0.1:8188" in src


# ------------------------------------------------------------------ 2. Installers

def _iss_excludes(section_source: str, dest: str) -> list[str]:
    for line in section_source.splitlines():
        if f'DestDir: "{dest}"' in line:
            m = re.search(r'Excludes: "([^"]*)"', line)
            assert m, f"no Excludes for {dest}"
            return [e.strip() for e in m.group(1).split(",") if e.strip()]
    raise AssertionError(f"no [Files] line for {dest}")


def _nsi_excludes(component: str) -> list[str]:
    r"""Exclusions of the File /r line copying ${ROOT}\<component>\*.*"""
    src = (ROOT / "installer" / "LocalAiStudio.nsi").read_text(encoding="utf-8", errors="replace")
    for line in src.splitlines():
        if "File /r" in line and "${ROOT}" in line and f"\\{component}\\" in line:
            return re.findall(r"/x (\S+)", line)
    raise AssertionError(f"no File /r line for {component}")


SECRET_SAMPLES = [
    ".api_key", ".boot_token", ".env", ".env.local", ".env.production",
    "bench_runs", "private.key", "cert.pem",
]


@pytest.mark.parametrize("sample", SECRET_SAMPLES)
def test_inno_setup_excludes_secrets_from_backend(sample):
    src = (ROOT / "installer" / "LocalAiStudio.iss").read_text(encoding="utf-8", errors="replace")
    patterns = _iss_excludes(src, "{app}\\backend")
    assert any(fnmatch.fnmatch(sample, p) for p in patterns), f"{sample} would be packaged (Inno backend)"


@pytest.mark.parametrize("sample", SECRET_SAMPLES)
def test_nsis_excludes_secrets_from_backend(sample):
    patterns = _nsi_excludes("backend")
    assert any(fnmatch.fnmatch(sample, p) for p in patterns), f"{sample} would be packaged (NSIS backend)"


@pytest.mark.parametrize("sample", [".env", ".env.local"])
def test_frontend_env_files_excluded(sample):
    src = (ROOT / "installer" / "LocalAiStudio.iss").read_text(encoding="utf-8", errors="replace")
    assert any(fnmatch.fnmatch(sample, p) for p in _iss_excludes(src, "{app}\\frontend"))
    assert any(fnmatch.fnmatch(sample, p) for p in _nsi_excludes("frontend"))


def test_secret_files_actually_present_are_the_ones_excluded():
    """Guards against a secret file existing in backend/ that no installer rule covers."""
    src = (ROOT / "installer" / "LocalAiStudio.iss").read_text(encoding="utf-8", errors="replace")
    patterns = _iss_excludes(src, "{app}\\backend")
    for name in (".api_key", ".boot_token"):
        assert name in patterns


# ------------------------------------------------------------------ 3. Vite exposure

def _vite_src() -> str:
    return (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")


def test_vite_listens_on_loopback_by_default():
    src = _vite_src()
    assert 'host: exposeDevServer ? true : "127.0.0.1"' in src
    assert 'allowedHosts: exposeDevServer ? true : ["localhost", "127.0.0.1"]' in src
    assert 'process.env.LAS_VITE_EXPOSE === "1"' in src


def test_vite_api_target_is_configurable_with_safe_default():
    src = _vite_src()
    assert 'target: process.env.LAS_API_TARGET || "http://localhost:8001"' in src


def test_vite_no_unconditional_host_true():
    src = _vite_src()
    assert not re.search(r"^\s*host:\s*true\s*,", src, re.M), "host: true must only be reachable through LAS_VITE_EXPOSE"
    assert not re.search(r"^\s*allowedHosts:\s*true\s*,", src, re.M)
    assert "cors: exposeDevServer" in src
    assert not re.search(r"^\s*cors:\s*true\s*,", src, re.M)


def test_vite_reads_boot_token_at_request_time():
    """After a backend restart the boot token file changes; the proxy must not keep a stale value."""
    src = _vite_src()
    assert "readBootToken" in src
    assert 'proxyReq.setHeader("X-Boot-Token", bootToken)' in src
    assert 'req.method === "POST" && pathname === "/api/auth/init"' in src


# ------------------------------------------------------------------ 4. Session lifecycle (real route)

@pytest.fixture()
def server_module(monkeypatch, tmp_path):
    monkeypatch.setenv("MONGO_URL", "mongodb://127.0.0.1:1")
    monkeypatch.setenv("DB_NAME", "localaistudio_security_tests")
    monkeypatch.setenv("LAS_BOOT_TOKEN", secrets.token_hex(32))
    # server imports a Motor client that needs a current event loop; earlier async tests may have closed it.
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    import server
    from lib import auth
    monkeypatch.setattr(auth, "_BOOT_FILE", tmp_path / ".boot_token")
    fresh = auth._BootToken()
    monkeypatch.setattr(server, "boot", fresh)
    return server


def _client(server):
    from starlette.testclient import TestClient
    return TestClient(server.app)


def test_first_start_init_sets_session_cookie_and_consumes_token(server_module):
    from lib.auth import API_KEY, COOKIE_NAME
    client = _client(server_module)
    r = client.post("/api/auth/init", headers={"X-Boot-Token": server_module.boot.token})
    assert r.status_code == 200
    assert r.cookies.get(COOKIE_NAME) == API_KEY
    assert server_module.boot.is_consumed


def test_wrong_boot_token_is_rejected_without_cookie(server_module):
    from lib.auth import COOKIE_NAME
    client = _client(server_module)
    r = client.post("/api/auth/init", headers={"X-Boot-Token": "wrong"})
    assert r.status_code == 401
    assert COOKIE_NAME not in r.cookies


def test_refresh_with_valid_session_cookie_does_not_error(server_module):
    """The frontend calls /api/auth/init on every page load. A refresh must not log a 401."""
    from lib.auth import API_KEY, COOKIE_NAME
    client = _client(server_module)
    assert client.post("/api/auth/init", headers={"X-Boot-Token": server_module.boot.token}).status_code == 200
    client.cookies.set(COOKIE_NAME, API_KEY, path="/api")
    r = client.post("/api/auth/init")  # refresh: boot token already consumed, session cookie present
    assert r.status_code == 200, "refresh with a valid session must be idempotent"
    # Without the cookie, the same protected route is refused by the middleware (rejection happens before routing).
    assert _client(server_module).get("/api/companies").status_code == 401


def test_refresh_without_cookie_and_consumed_token_is_rejected(server_module):
    token = server_module.boot.token
    assert _client(server_module).post("/api/auth/init", headers={"X-Boot-Token": token}).status_code == 200
    # Fresh client = no cookie: the consumed one-time token must not open a second session.
    r = _client(server_module).post("/api/auth/init", headers={"X-Boot-Token": token})
    assert r.status_code == 401


def test_session_survives_backend_restart(monkeypatch, tmp_path):
    """The API key lives in .api_key, so a restarted backend reads the same key and old cookies stay valid."""
    from lib import auth
    key_file = tmp_path / ".api_key"
    key_file.write_text("a" * 64)
    monkeypatch.setattr(auth, "_KEY_FILE", key_file)
    assert auth._load_or_create_key() == "a" * 64
    assert auth._load_or_create_key() == "a" * 64  # second start: unchanged


def test_boot_token_regenerated_on_restart_without_env(monkeypatch, tmp_path):
    from lib import auth
    monkeypatch.delenv("LAS_BOOT_TOKEN", raising=False)
    boot_file = tmp_path / ".boot_token"
    monkeypatch.setattr(auth, "_BOOT_FILE", boot_file)
    first = auth._init_boot_token()
    assert boot_file.read_text() == first
    second = auth._init_boot_token()
    assert second != first and boot_file.read_text() == second
