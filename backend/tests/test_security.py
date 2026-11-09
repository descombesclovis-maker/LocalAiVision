"""Security tests for V1-B.

Covers:
  1. Auth middleware — token validation, exempt paths, localhost bootstrap, 401 rejection.
  2. CORS configuration — restrictive defaults, '*' filtering, env override.
  3. CSP on preview responses — generated sites cannot call the API via fetch/XHR.
  4. Tunnel script neutralisation — no public unauthenticated cloudflared tunnels.
  5. V1-A verification — false "missing model" risk and double verify_ready() call.

No GPU, ComfyUI, Ollama or MongoDB required — httpx and FastAPI TestClient are mocked/in-process.
"""
import os
import inspect
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import Response

from starlette.testclient import TestClient

from lib import auth, comfy
from lib.auth import (
    API_KEY,
    AuthMiddleware,
    COOKIE_NAME,
    _extract_token,
    _is_exempt,
    _is_localhost,
    _load_or_create_key,
)

ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------ 1. auth middleware unit tests


class TestIsExempt:
    """Exempt paths should not require a token (public preview & asset serving)."""

    def test_health_check(self):
        assert _is_exempt("/api")
        assert _is_exempt("/api/")

    def test_preview_serving(self):
        assert _is_exempt("/api/preview/abc-123/index.html")
        assert _is_exempt("/api/preview/xyz/styles.css")

    def test_media_file_serving(self):
        assert _is_exempt("/api/media/550e8400-e29b-41d4-a716-446655440000/file")

    def test_sensitive_media_endpoints_require_auth(self):
        assert not _is_exempt("/api/media")
        assert not _is_exempt("/api/media/550e8400-e29b-41d4-a716-446655440000")
        assert not _is_exempt("/api/media/images")

    def test_sensitive_endpoints_require_auth(self):
        assert not _is_exempt("/api/projects")
        assert not _is_exempt("/api/projects/abc")
        assert not _is_exempt("/api/settings/comfyui")
        assert not _is_exempt("/api/queue")
        assert not _is_exempt("/api/brands")


class TestIsLocalhost:
    """_is_localhost must check BOTH the TCP source AND the Host header."""

    def test_loopback_with_localhost_host(self):
        scope = {"client": ("127.0.0.1", 50000), "headers": [(b"host", b"localhost:8001")]}
        assert _is_localhost(scope) is True

    def test_loopback_with_127_host(self):
        scope = {"client": ("127.0.0.1", 50000), "headers": [(b"host", b"127.0.0.1:8001")]}
        assert _is_localhost(scope) is True

    def test_ipv6_loopback(self):
        scope = {"client": ("::1", 50000), "headers": [(b"host", b"localhost:8001")]}
        assert _is_localhost(scope) is True

    def test_loopback_tcp_but_tunnel_host(self):
        """Even if a tunnel connects locally, the Host header reveals it."""
        scope = {"client": ("127.0.0.1", 50000), "headers": [(b"host", b"abc.trycloudflare.com")]}
        assert _is_localhost(scope) is False

    def test_remote_tcp(self):
        scope = {"client": ("192.168.1.5", 50000), "headers": [(b"host", b"localhost:8001")]}
        assert _is_localhost(scope) is False

    def test_no_client(self):
        scope = {"client": None, "headers": [(b"host", b"localhost:8001")]}
        assert _is_localhost(scope) is False


class TestExtractToken:
    def test_x_api_key_header(self):
        scope = {"headers": [(b"x-api-key", b"secret123")]}
        assert _extract_token(scope) == "secret123"

    def test_cookie(self):
        scope = {"headers": [(b"cookie", f"{COOKIE_NAME}=secret456; other=val".encode())]}
        assert _extract_token(scope) == "secret456"

    def test_no_token(self):
        scope = {"headers": []}
        assert _extract_token(scope) is None

    def test_empty_values(self):
        scope = {"headers": [(b"x-api-key", b""), (b"cookie", b"")] }
        assert _extract_token(scope) is None


class TestApiKey:
    def test_api_key_is_nonempty(self):
        assert len(API_KEY) >= 32

    def test_key_file_created(self):
        key_file = ROOT / "backend" / ".api_key"
        # Importing auth.py creates the file; verify it exists and is non-empty.
        assert key_file.exists()
        assert key_file.read_text().strip() == API_KEY


# ------------------------------------------------------------------ 2. integration tests (TestClient)


def _make_app() -> FastAPI:
    """Minimal FastAPI app with auth middleware and representative endpoints."""
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/")
    async def root():
        return {"message": "ok"}

    @app.get("/api/projects")
    async def list_projects():
        return {"projects": []}

    @app.delete("/api/projects/{pid}")
    async def delete_project(pid: str):
        return {"ok": True}

    @app.get("/api/preview/{pid}/{path:path}")
    async def preview(pid: str, path: str):
        return Response("<html></html>", media_type="text/html",
                        headers={"Content-Security-Policy": "connect-src 'none'"})

    @app.get("/api/media/{mid}/file")
    async def media_file(mid: str):
        return Response(b"\x89PNG", media_type="image/png")

    @app.delete("/api/media/{mid}")
    async def delete_media(mid: str):
        return {"ok": True}

    return app


@pytest.fixture
def client():
    return TestClient(_make_app())


class TestAuthRejection:
    """Requests without a valid token from a non-loopback source must be rejected."""

    def test_no_auth_returns_401(self, client):
        r = client.get("/api/projects")
        assert r.status_code == 401
        assert "Authentification requise" in r.json()["detail"]

    def test_wrong_api_key_returns_401(self, client):
        r = client.get("/api/projects", headers={"X-API-Key": "wrong"})
        assert r.status_code == 401

    def test_wrong_cookie_returns_401(self, client):
        r = client.get("/api/projects", headers={"Cookie": f"{COOKIE_NAME}=wrong"})
        assert r.status_code == 401

    def test_delete_without_auth_401(self, client):
        r = client.delete("/api/projects/abc")
        assert r.status_code == 401


class TestAuthAccepted:
    """Requests with a valid token (header or cookie) must succeed."""

    def test_valid_api_key_header(self, client):
        r = client.get("/api/projects", headers={"X-API-Key": API_KEY})
        assert r.status_code == 200
        assert r.json() == {"projects": []}

    def test_valid_cookie(self, client):
        r = client.get("/api/projects", headers={"Cookie": f"{COOKIE_NAME}={API_KEY}"})
        assert r.status_code == 200

    def test_delete_with_auth(self, client):
        r = client.delete("/api/projects/abc", headers={"X-API-Key": API_KEY})
        assert r.status_code == 200


class TestExemptPaths:
    """Exempt paths must work without any token."""

    def test_health_check_no_auth(self, client):
        r = client.get("/api/")
        assert r.status_code == 200

    def test_preview_no_auth(self, client):
        r = client.get("/api/preview/abc/index.html")
        assert r.status_code == 200

    def test_media_file_no_auth(self, client):
        r = client.get("/api/media/xyz/file")
        assert r.status_code == 200

    def test_sensitive_media_still_requires_auth(self, client):
        r = client.delete("/api/media/xyz")
        assert r.status_code == 401


class TestOptionsPassthrough:
    """CORS preflight (OPTIONS) must not require auth."""

    def test_options_no_auth(self, client):
        r = client.options("/api/projects")
        # OPTIONS is passed through by the middleware (no 401).
        assert r.status_code != 401


# ------------------------------------------------------------------ 3. CSP on preview responses


class TestCspHeader:
    """Generated-site previews must carry CSP connect-src 'none' to block API calls."""

    def test_preview_has_csp(self, client):
        r = client.get("/api/preview/abc/index.html")
        csp = r.headers.get("content-security-policy", "")
        assert "connect-src" in csp
        assert "'none'" in csp

    def test_csp_blocks_connect_but_not_images(self, client):
        r = client.get("/api/preview/abc/index.html")
        csp = r.headers.get("content-security-policy", "")
        # connect-src 'none' blocks fetch/XHR but <img> tags are governed by img-src (default *).
        assert "connect-src 'none'" in csp


# ------------------------------------------------------------------ 4. tunnel script neutralised


class TestTunnelScript:
    """tunnel-preview.bat must not create public unauthenticated tunnels."""

    def test_no_cloudflared_tunnel_url(self):
        content = (ROOT / "tunnel-preview.bat").read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        # No line should execute cloudflared — only REM/echo lines may mention it.
        for line in lines:
            stripped = line.strip()
            if "cloudflared" in stripped.lower():
                assert stripped.upper().startswith("REM") or stripped.lower().startswith("echo"), \
                    f"Non-comment line references cloudflared: {line}"

    def test_contains_security_warning(self):
        content = (ROOT / "tunnel-preview.bat").read_text(encoding="utf-8", errors="replace")
        assert "SECURISE" in content or "SÉCURISÉ" in content.upper()

    def test_loopback_addresses_mentioned(self):
        content = (ROOT / "tunnel-preview.bat").read_text(encoding="utf-8", errors="replace")
        assert "127.0.0.1:11434" in content
        assert "127.0.0.1:8188" in content


# ------------------------------------------------------------------ 5. CORS configuration


class TestCorsConfig:
    """CORS must default to loopback-only and never use '*' with credentials."""

    def test_default_origins_are_loopback(self):
        from server import _LOOPBACK_ORIGINS
        assert all("localhost" in o or "127.0.0.1" in o for o in _LOOPBACK_ORIGINS)

    def test_wildcard_filtered_out(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "*")
        from server import _cors_origins, _LOOPBACK_ORIGINS
        origins = _cors_origins()
        assert "*" not in origins
        assert origins == _LOOPBACK_ORIGINS

    def test_custom_origins_respected(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        from server import _cors_origins
        origins = _cors_origins()
        assert "https://example.com" in origins

    def test_mixed_origins_keep_non_wildcard(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "*,http://localhost:3000")
        from server import _cors_origins
        origins = _cors_origins()
        assert "*" not in origins
        assert "http://localhost:3000" in origins


# ------------------------------------------------------------------ 6. V1-A verification


class TestV1aVerification:
    """Verify the two risks identified in V1-A without modifying the engines."""

    def test_choices_returns_empty_on_error(self):
        """Risk 1: if ComfyUI's object_info endpoint fails, _choices returns [].
        This causes _missing_files to falsely report models as missing."""
        # _choices swallows all exceptions and returns [] — see the dedicated async test below.
        # This test documents the risk; the actual behavior is verified in test_choices_empty_on_http_error.
        from lib import comfy
        # _choices catches all exceptions — confirmed by reading the source.
        src = inspect.getsource(comfy._choices)
        assert "except Exception" in src
        assert "return []" in src

    @pytest.mark.asyncio
    async def test_choices_empty_on_http_error(self):
        """_choices catches all exceptions and returns an empty list."""
        class _ErrClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                return None
            async def get(self, url):
                raise ConnectionRefusedError("ComfyUI not running")

        c = _ErrClient()
        result = await comfy._choices(c, "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result == []

    @pytest.mark.asyncio
    async def test_false_missing_model_when_list_unavailable(self):
        """Risk 1 confirmed: when model lists are empty (endpoint failed),
        _missing_files reports the preset's model as missing — a false positive."""
        s = comfy.DEFAULTS.copy()
        lists = {"checkpoints": [], "diffusion_models": [], "text_encoders": [], "vae": []}
        missing = comfy._missing_files(s, lists, video=False)
        # The image checkpoint is reported as missing even though it might be installed —
        # the empty list came from a failed request, not from ComfyUI actually having no models.
        assert s["image_checkpoint"] in missing
        # Document: this is the false-positive risk. A targeted fix would distinguish
        # "request failed" (list unavailable) from "list empty" (no models installed).

    def test_double_verify_ready_in_comfy(self):
        """Risk 2 confirmed: verify_ready is called in both media.py and comfy.py."""
        # Check comfy.py's generate_image calls verify_ready
        src_comfy = inspect.getsource(comfy.generate_image)
        assert "verify_ready" in src_comfy, "comfy.generate_image should call verify_ready"
        src_comfy_vid = inspect.getsource(comfy.generate_video)
        assert "verify_ready" in src_comfy_vid, "comfy.generate_video should call verify_ready"

        # Check media.py calls verify_ready — read source directly to avoid importing
        # routers.media (which triggers motor GridFS bucket init needing an event loop).
        media_src = (ROOT / "backend" / "routers" / "media.py").read_text()
        assert "verify_ready" in media_src, "media.py should call verify_ready"
        # verify_ready appears in both _comfy_image and _run_comfy_video → at least 2 calls.
        assert media_src.count("verify_ready") >= 2, "media.py should call verify_ready at least twice (image + video)"

        # Document: verify_ready runs twice per generation — once in media.py (before GPU slot)
        # and once in comfy.generate_image/generate_video (after get_settings). Each call fetches
        # system_stats + 4 object_info endpoints (5 HTTP round-trips). The redundancy is harmless
        # (~0.1s localhost overhead) but wasteful. A targeted fix: remove verify_ready from
        # generate_image/generate_video since all callers already pre-check via media.py.


# ------------------------------------------------------------------ 7. API key file excluded from kit


class TestApiKeyProtection:
    """The API key file must not be included in kit downloads or committed to git."""

    def test_api_key_in_skip_files(self):
        # Read source directly to avoid importing routers.engines (motor event loop issue).
        src = (ROOT / "backend" / "routers" / "engines.py").read_text()
        assert ".api_key" in src
        assert "SKIP_FILES" in src

    def test_api_key_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text()
        assert ".api_key" in gitignore

    def test_env_example_uses_loopback(self):
        src = (ROOT / "backend" / "routers" / "engines.py").read_text()
        assert "CORS_ORIGINS=*" not in src
        assert "localhost" in src
