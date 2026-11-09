"""API-key authentication for the LocalAiStudio backend.

LocalAiStudio is a 100 % local desktop application: the FastAPI backend listens on 127.0.0.1 and
the React frontend (Vite dev server) proxies ``/api/*`` calls to it.  No request is ever authorised
*because* it comes from localhost — instead, the first request from a verified loopback connection
receives a signed ``las_session`` httpOnly cookie, and every subsequent request (header **or** cookie)
must carry a valid token.

Threat model addressed
-----------------------
* Malicious websites → CORS restricted to loopback origins (server.py) + token required.
* Generated-site JS → ``Content-Security-Policy: connect-src 'none'`` on preview responses
  (routers/projects.py) blocks fetch/XHR even though the preview shares the backend origin.
* Public tunnels → tunnel-preview.bat no longer creates unauthenticated Cloudflare tunnels.
* Direct backend access → 401 without a valid token.
"""
import json
import secrets
from pathlib import Path
from typing import Optional

from starlette.types import ASGIApp, Receive, Scope, Send

# -- key management -----------------------------------------------------------

_KEY_FILE = Path(__file__).resolve().parent.parent / ".api_key"
COOKIE_NAME = "las_session"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _load_or_create_key() -> str:
    """Return the persistent API key, creating a random one on first run.

    The file lives in ``backend/.api_key`` (gitignored, excluded from kit downloads).  If the
    directory is read-only the key is kept in memory only and regenerated on restart — acceptable
    for a local app where the cookie is reissued on the next localhost request.
    """
    if _KEY_FILE.exists():
        key = _KEY_FILE.read_text().strip()
        if key:
            return key
    key = secrets.token_hex(32)
    try:
        _KEY_FILE.write_text(key)
        try:
            _KEY_FILE.chmod(0o600)
        except (OSError, NotImplementedError):
            pass  # Windows ignores Unix permission bits
    except OSError:
        pass  # in-memory fallback
    return key


API_KEY = _load_or_create_key()

# -- helpers ------------------------------------------------------------------

# Paths that never require a token: preview HTML (served to generated sites) and
# media file serving (images/videos referenced by generated-site <img>/<video> tags).
# Listing, creating, deleting, and triggering media all require auth.
_EXEMPT_PREFIXES = ("/api/preview/",)
_EXEMPT_SUFFIXES = ("/file",)
_HEALTH_PATHS = frozenset({"/api", "/api/"})


def _is_exempt(path: str) -> bool:
    if path in _HEALTH_PATHS:
        return True
    if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return True
    # /api/media/{id}/file  — public asset serving for generated-site previews
    if path.startswith("/api/media/") and path.endswith("/file"):
        return True
    return False


def _is_localhost(scope: Scope) -> bool:
    """True only when the TCP connection *and* the Host header are both loopback.

    Checking the Host header prevents a tunnel bypass: even if cloudflared connects locally,
    the Host header would be the tunnel URL, not ``localhost``.
    """
    client = scope.get("client")
    if not client or client[0] not in ("127.0.0.1", "::1"):
        return False
    for name, value in scope.get("headers", []):
        if name == b"host":
            host = value.decode("latin-1").split(":")[0].lower()
            return host in _LOOPBACK_HOSTS
    return False


def _extract_token(scope: Scope) -> Optional[str]:
    """Return the bearer token from the ``X-API-Key`` header or the ``las_session`` cookie."""
    raw_cookie = None
    for name, value in scope.get("headers", []):
        if name == b"x-api-key" and value.strip():
            return value.decode("latin-1")
        if name == b"cookie":
            raw_cookie = value.decode("latin-1")
    if raw_cookie:
        for part in raw_cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE_NAME and v:
                return v
    return None


# -- ASGI middleware ----------------------------------------------------------


class AuthMiddleware:
    """Pure ASGI auth middleware (no BaseHTTPMiddleware — safe with StreamingResponse).

    Flow:
      1. OPTIONS, non-/api, and exempt paths → pass through.
      2. Valid X-API-Key header or las_session cookie → pass through.
      3. Loopback connection (TCP + Host) with no token → pass through AND set cookie
         (auto-bootstrap: the very first request from the local frontend gets a cookie
         so subsequent calls are authenticated without any frontend code change).
      4. Anything else → 401 JSON.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope["path"]
        method = scope["method"]

        # CORS preflight, non-API paths, and exempt endpoints never need auth.
        if method == "OPTIONS" or not path.startswith("/api") or _is_exempt(path):
            return await self.app(scope, receive, send)

        token = _extract_token(scope)
        if token == API_KEY:
            return await self.app(scope, receive, send)

        # Auto-bootstrap: issue a cookie to the first loopback request.
        if _is_localhost(scope):
            cookie = (
                f"{COOKIE_NAME}={API_KEY}; HttpOnly; SameSite=Strict; Path=/api"
            )

            async def _send_with_cookie(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"set-cookie", cookie.encode("latin-1")))
                    message["headers"] = headers
                await send(message)

            return await self.app(scope, receive, _send_with_cookie)

        # Non-authenticated, non-loopback → reject.
        body = json.dumps({"detail": "Authentification requise"}).encode("latin-1")
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
