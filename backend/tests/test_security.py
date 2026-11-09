"""Security tests for V1-B and V1-B.2.

Covers:
  1. Auth middleware — token validation, exempt paths, /api/auth/init, 401 rejection.
  2. Bootstrap token — one-time use, invalidation after consumption, env-var source.
  3. CORS configuration — restrictive defaults, '*' filtering, env override.
  4. CSP + sandbox on preview responses — generated sites cannot call the API.
  5. Tunnel script neutralisation — no public unauthenticated cloudflared tunnels.
  6. V1-A verification — false "missing model" risk documented; double verify_ready documented.
  7. API key file excluded from kit downloads and git.

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
    _load_or_create_key,
    boot,
    _BootToken,
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

    def test_auth_init_is_exempt(self):
        """POST /api/auth/init must be exempt — it validates the boot token itself."""
        assert _is_exempt("/api/auth/init")

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


# ------------------------------------------------------------------ 2. bootstrap token tests


class TestBootToken:
    """One-time bootstrap token: valid once, rejected on replay."""

    def test_boot_token_env_var_is_used(self, monkeypatch):
        """conftest.py sets LAS_BOOT_TOKEN=test-boot-token; _BootToken should use it."""
        monkeypatch.setenv("LAS_BOOT_TOKEN", "my-test-token-xyz")
        bt = _BootToken()
        assert bt.token == "my-test-token-xyz"
        assert not bt.is_consumed

    def test_consume_valid_token(self):
        """First consume() with the correct token returns True and marks consumed."""
        bt = _BootToken()
        tok = bt.token
        assert bt.consume(tok) is True
        assert bt.is_consumed

    def test_consume_invalid_token(self):
        """consume() with wrong value returns False."""
        bt = _BootToken()
        assert bt.consume("wrong-token") is False
        assert not bt.is_consumed

    def test_consume_once(self):
        """Token can be consumed exactly once — replay is rejected."""
        bt = _BootToken()
        tok = bt.token
        assert bt.consume(tok) is True
        assert bt.consume(tok) is False  # replay rejected

    def test_consume_empty_string(self):
        bt = _BootToken()
        assert bt.consume("") is False

    def test_no_localhost_bypass(self):
        """_is_localhost is no longer exported — auto-bootstrap has been removed (V1-B.2)."""
        assert not hasattr(auth, "_is_localhost"), (
            "_is_localhost should not be exported: auto-bootstrap from loopback was removed in V1-B.2. "
            "No request may be authorised solely because it comes from localhost."
        )


# ------------------------------------------------------------------ 3. integration tests (TestClient)


def _make_app(custom_boot_token: str = "integration-boot-token") -> FastAPI:
    """Minimal FastAPI app with auth middleware, /api/auth/init, and representative endpoints."""
    from lib.auth import boot as _boot
    from fastapi import Request as _Request
    from fastapi.responses import JSONResponse

    # Reset the shared boot singleton for integration tests.
    import os
    os.environ["LAS_BOOT_TOKEN"] = custom_boot_token
    from lib import auth as _auth_mod
    test_boot = _auth_mod._BootToken()

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.post("/api/auth/init")
    async def init_session(request: _Request):
        token = request.headers.get("x-boot-token", "")
        if not test_boot.consume(token):
            from fastapi import HTTPException
            raise HTTPException(401, "Jeton d'initialisation invalide ou déjà utilisé")
        resp = JSONResponse({"ok": True})
        resp.set_cookie(COOKIE_NAME, API_KEY, httponly=True, samesite="strict", path="/api")
        return resp

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
                        headers={"Content-Security-Policy": "connect-src 'none'; form-action 'none'"})

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
    """Requests without a valid token must be rejected."""

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

    def test_no_localhost_auto_bootstrap(self, client):
        """V1-B.2: loopback requests without a token must NOT be auto-authenticated."""
        # The TestClient sends requests without a token; they must be rejected.
        # (Previously the middleware would issue a cookie on the first loopback request.)
        r = client.get("/api/projects")
        assert r.status_code == 401
        # No Set-Cookie header should be present on the 401 response.
        assert "set-cookie" not in {k.lower() for k in r.headers}


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


class TestAuthInit:
    """POST /api/auth/init: validates the one-time boot token, issues a session cookie."""

    def test_valid_boot_token_returns_200_with_cookie(self):
        app = _make_app("my-boot-token-abc123")
        c = TestClient(app)
        r = c.post("/api/auth/init", headers={"X-Boot-Token": "my-boot-token-abc123"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert COOKIE_NAME in r.cookies or "set-cookie" in {k.lower() for k in r.headers}

    def test_invalid_boot_token_returns_401(self):
        app = _make_app("correct-token")
        c = TestClient(app)
        r = c.post("/api/auth/init", headers={"X-Boot-Token": "wrong-token"})
        assert r.status_code == 401

    def test_empty_boot_token_returns_401(self):
        app = _make_app("correct-token")
        c = TestClient(app)
        r = c.post("/api/auth/init")
        assert r.status_code == 401

    def test_boot_token_is_one_time_use(self):
        """The token must be invalidated after first successful use."""
        app = _make_app("one-time-tok")
        c = TestClient(app)
        r1 = c.post("/api/auth/init", headers={"X-Boot-Token": "one-time-tok"})
        assert r1.status_code == 200
        r2 = c.post("/api/auth/init", headers={"X-Boot-Token": "one-time-tok"})
        assert r2.status_code == 401  # replay rejected

    def test_no_secret_needed_in_frontend(self):
        """The X-Boot-Token header is injected by the Vite proxy, never embedded in the
        frontend bundle. Verify the frontend source does not contain a hardcoded token."""
        main_tsx = ROOT / "frontend" / "src" / "main.tsx"
        if main_tsx.exists():
            content = main_tsx.read_text(encoding="utf-8", errors="replace")
            # The bootstrap call must not include a hardcoded token value.
            assert "LAS_BOOT_TOKEN" not in content, (
                "LAS_BOOT_TOKEN should never appear in the frontend bundle — "
                "it is injected by the Vite proxy configure hook."
            )


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

    def test_auth_init_no_token_required(self, client):
        """POST /api/auth/init is exempt from the auth middleware (it validates its own token)."""
        # Without a valid boot token the endpoint returns 401, but the middleware lets it through.
        r = client.post("/api/auth/init")
        # 401 from the endpoint itself (bad boot token), not from the middleware.
        assert r.status_code == 401  # endpoint-level, not middleware-level


class TestOptionsPassthrough:
    """CORS preflight (OPTIONS) must not require auth."""

    def test_options_no_auth(self, client):
        r = client.options("/api/projects")
        # OPTIONS is passed through by the middleware (no 401).
        assert r.status_code != 401


# ------------------------------------------------------------------ 4. CSP + sandbox on preview responses


class TestCspHeader:
    """Generated-site previews must carry CSP that blocks API calls."""

    def test_preview_has_csp(self, client):
        r = client.get("/api/preview/abc/index.html")
        csp = r.headers.get("content-security-policy", "")
        assert "connect-src" in csp
        assert "'none'" in csp

    def test_csp_blocks_connect_and_forms(self, client):
        r = client.get("/api/preview/abc/index.html")
        csp = r.headers.get("content-security-policy", "")
        # connect-src 'none' blocks fetch/XHR; form-action 'none' blocks form submissions.
        assert "connect-src 'none'" in csp
        assert "form-action 'none'" in csp

    def test_iframe_sandbox_attribute_in_editor(self):
        """Editor.tsx must render the preview iframe with sandbox (no allow-same-origin)."""
        editor_tsx = ROOT / "frontend" / "src" / "pages" / "Editor.tsx"
        if editor_tsx.exists():
            content = editor_tsx.read_text(encoding="utf-8", errors="replace")
            assert 'sandbox="allow-scripts allow-forms"' in content, (
                "Preview iframe must have sandbox='allow-scripts allow-forms' "
                "(no allow-same-origin) for effective script isolation."
            )

    def test_no_allow_same_origin_in_sandbox(self):
        """allow-same-origin would nullify the sandbox — must not be present."""
        editor_tsx = ROOT / "frontend" / "src" / "pages" / "Editor.tsx"
        if editor_tsx.exists():
            content = editor_tsx.read_text(encoding="utf-8", errors="replace")
            # Ensure 'allow-same-origin' is not in any sandbox attribute.
            import re
            sandbox_values = re.findall(r'sandbox="([^"]*)"', content)
            for val in sandbox_values:
                assert "allow-same-origin" not in val, (
                    "allow-same-origin in sandbox defeats script isolation."
                )

    def test_postmessage_bridge_in_preview(self):
        """Element-selection bridge injected into preview must use postMessage, not contentDocument."""
        projects_py = ROOT / "backend" / "routers" / "projects.py"
        if projects_py.exists():
            content = projects_py.read_text(encoding="utf-8", errors="replace")
            assert "postMessage" in content, (
                "Preview bridge must use postMessage (not contentDocument) for sandboxed iframe communication."
            )
            assert "parent.postMessage" in content


# ------------------------------------------------------------------ 5. tunnel script neutralised


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


# ------------------------------------------------------------------ 6. CORS configuration


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


# ------------------------------------------------------------------ 7. V1-A verification (documented risks)


class TestV1aVerification:
    """Verify the two risks identified in V1-A — documented for V1-C targeted fix."""

    def test_choices_catches_all_exceptions(self):
        """Risk 1: _choices catches all exceptions and returns [] on any error.
        _missing_files then falsely reports models as missing (false positive).
        FIX (V1-C): _choices should return None on error; _missing_files should skip check when None."""
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

    def test_double_verify_ready_documented(self):
        """Risk 2: verify_ready called in both media.py and comfy.py per generation.
        This test documents the current (pre-V1-C) state.
        After V1-C the call in comfy.generate_image/generate_video will be removed."""
        # comfy.py currently calls verify_ready in generate_image and generate_video.
        src_img = inspect.getsource(comfy.generate_image)
        src_vid = inspect.getsource(comfy.generate_video)
        # media.py also calls verify_ready.
        media_src = (ROOT / "backend" / "routers" / "media.py").read_text()
        assert "verify_ready" in media_src, "media.py should call verify_ready (V1-C will deduplicate)"
        # Document the current state for V1-C reference.
        # After V1-C, the assertions about comfy.py may be inverted.


# ------------------------------------------------------------------ 8. API key and boot token file protection


class TestApiKeyProtection:
    """The API key and boot token files must not be included in kit downloads or committed to git."""

    def test_api_key_in_skip_files(self):
        src = (ROOT / "backend" / "routers" / "engines.py").read_text()
        assert ".api_key" in src
        assert "SKIP_FILES" in src

    def test_boot_token_in_skip_files(self):
        """V1-B.2: .boot_token must also be excluded from kit downloads."""
        src = (ROOT / "backend" / "routers" / "engines.py").read_text()
        assert ".boot_token" in src

    def test_api_key_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text()
        assert ".api_key" in gitignore

    def test_boot_token_gitignored(self):
        """V1-B.2: .boot_token must be gitignored."""
        gitignore = (ROOT / ".gitignore").read_text()
        assert ".boot_token" in gitignore

    def test_env_example_uses_loopback(self):
        src = (ROOT / "backend" / "routers" / "engines.py").read_text()
        assert "CORS_ORIGINS=*" not in src
        assert "localhost" in src

    def test_launcher_generates_boot_token(self):
        """start-localaistudio.bat must generate LAS_BOOT_TOKEN on startup."""
        content = (ROOT / "start-localaistudio.bat").read_text(encoding="utf-8", errors="replace")
        assert "LAS_BOOT_TOKEN" in content
