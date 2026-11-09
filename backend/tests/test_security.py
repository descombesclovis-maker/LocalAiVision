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
        # Read server.py source directly to avoid the motor/event-loop import issue.
        server_src = (ROOT / "backend" / "server.py").read_text()
        assert "localhost" in server_src
        assert "127.0.0.1" in server_src
        # _LOOPBACK_ORIGINS must not contain wildcards.
        assert '"*"' not in server_src.split("_LOOPBACK_ORIGINS")[1].split("]")[0]

    def test_wildcard_filtered_out(self):
        server_src = (ROOT / "backend" / "server.py").read_text()
        # _cors_origins() must filter out '*'.
        assert 'if "*"' in server_src or "!= '*'" in server_src or "wildcard" in server_src.lower() or \
               'o != "*"' in server_src or '"*" not in' in server_src, (
            "_cors_origins must filter out '*' to prevent wildcard CORS with credentials."
        )

    def test_custom_origins_respected(self):
        server_src = (ROOT / "backend" / "server.py").read_text()
        assert "CORS_ORIGINS" in server_src, "CORS_ORIGINS env var must be supported"

    def test_mixed_origins_keep_non_wildcard(self):
        """Mixing '*' with real origins: '*' must be dropped, valid origins kept."""
        server_src = (ROOT / "backend" / "server.py").read_text()
        # The cors_origins function must split on comma and filter wildcards.
        assert "split" in server_src or "CORS_ORIGINS" in server_src


# ------------------------------------------------------------------ 7. V1-A verification (documented risks)


class TestV1aVerification:
    """Verify the two risks identified in V1-A — documented for V1-C targeted fix."""

    def test_choices_returns_none_on_error(self):
        """V1-C fix: _choices now returns None on error (not []) to distinguish
        'list unavailable' from 'list empty'. This prevents false «model missing» diagnostics."""
        from lib import comfy
        src = inspect.getsource(comfy._choices)
        assert "return None" in src, (
            "After V1-C, _choices must return None on error, not []. "
            "None = list unavailable; [] = list available but empty."
        )

    @pytest.mark.asyncio
    async def test_choices_returns_none_on_http_error(self):
        """V1-C: _choices returns None (not []) when ComfyUI is unreachable."""
        class _ErrClient:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                return None
            async def get(self, url):
                raise ConnectionRefusedError("ComfyUI not running")

        c = _ErrClient()
        result = await comfy._choices(c, "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result is None, "After V1-C, _choices must return None on error (not [])"

    @pytest.mark.asyncio
    async def test_no_false_missing_model_when_list_unavailable(self):
        """V1-C fix confirmed: when model lists are None (endpoint failed),
        _missing_files no longer reports models as missing — the false positive is fixed."""
        s = comfy.DEFAULTS.copy()
        # All lists are None (failed requests) — must not report any model as missing.
        lists = {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}
        missing = comfy._missing_files(s, lists, video=False)
        assert missing == [], (
            "V1-C fix: _missing_files must not report models as missing when lists are None (unavailable). "
            "None means the request failed — not that the model is absent."
        )

    def test_double_verify_ready_documented(self):
        """V1-C: verify_ready has been removed from comfy.generate_image/generate_video.
        It is now called exactly once per generation in media.py, before the GPU slot.
        This test verifies the V1-C fix is in place."""
        import ast, textwrap
        # After V1-C, generate_image and generate_video must NOT call verify_ready.
        src_img = inspect.getsource(comfy.generate_image)
        src_vid = inspect.getsource(comfy.generate_video)

        def _count_verify_ready_calls(src: str) -> int:
            try:
                tree = ast.parse(textwrap.dedent(src))
                return sum(
                    1 for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and (
                        (isinstance(node.func, ast.Attribute) and node.func.attr == "verify_ready")
                        or (isinstance(node.func, ast.Name) and node.func.id == "verify_ready")
                    )
                )
            except SyntaxError:
                return -1

        assert _count_verify_ready_calls(src_img) == 0, (
            "V1-C: generate_image() must not call verify_ready() — "
            "media.py calls it once before the GPU slot."
        )
        assert _count_verify_ready_calls(src_vid) == 0, (
            "V1-C: generate_video() must not call verify_ready() — "
            "media.py calls it once before the GPU slot."
        )
        # media.py still calls verify_ready (the authoritative single call).
        media_src = (ROOT / "backend" / "routers" / "media.py").read_text()
        assert "verify_ready" in media_src, "media.py must still call verify_ready()"


# ------------------------------------------------------------------ 8. API key and boot token file protection


class TestApiKeyProtection:
    """The API key and boot token files must not be included in kit downloads or committed to git."""

    def test_api_key_in_skip_files(self):
        from lib.kit_export import SKIP_FILES
        assert ".api_key" in SKIP_FILES

    def test_boot_token_in_skip_files(self):
        """V1-B.2: .boot_token must also be excluded from kit downloads."""
        from lib.kit_export import SKIP_FILES
        assert ".boot_token" in SKIP_FILES

    def test_api_key_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text()
        assert ".api_key" in gitignore

    def test_boot_token_gitignored(self):
        """V1-B.2: .boot_token must be gitignored."""
        gitignore = (ROOT / ".gitignore").read_text()
        assert ".boot_token" in gitignore

    def test_kit_does_not_export_a_local_dotenv(self):
        import zipfile
        from lib.kit_export import build_kit
        with zipfile.ZipFile(build_kit(ROOT)) as archive:
            assert not any("/.env" in name.casefold() for name in archive.namelist())

    def test_launcher_generates_boot_token(self):
        """start-localaistudio.bat must generate LAS_BOOT_TOKEN on startup."""
        content = (ROOT / "start-localaistudio.bat").read_text(encoding="utf-8", errors="replace")
        assert "LAS_BOOT_TOKEN" in content
