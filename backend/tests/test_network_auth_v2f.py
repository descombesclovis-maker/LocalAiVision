"""Behavioural auth/CORS tests; TestClient has no lifespan and never contacts MongoDB."""

import secrets

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from lib import auth
import server


@pytest.fixture
def session_client(monkeypatch):
    monkeypatch.setenv("LAS_BOOT_TOKEN", secrets.token_hex(32))
    monkeypatch.setenv("CORS_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000")
    monkeypatch.setattr(server, "boot", auth._BootToken())
    return TestClient(server.app)


def test_wildcard_is_removed_from_cors_configuration(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*,http://127.0.0.1:3000")
    assert server._cors_origins() == ["http://127.0.0.1:3000"]
    monkeypatch.setenv("CORS_ORIGINS", "*")
    assert "*" not in server._cors_origins()
    assert "http://127.0.0.1:3000" in server._cors_origins()


def test_foreign_cors_preflight_is_denied(session_client):
    resp = session_client.options("/api/kit/info", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_local_cors_preflight_is_allowed(session_client):
    resp = session_client.options("/api/kit/info", headers={
        "Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_cross_site_init_cannot_consume_boot_token(session_client):
    token = server.boot.token
    denied = session_client.post("/api/auth/init", headers={"Origin": "https://evil.example", "X-Boot-Token": token})
    assert denied.status_code == 403
    assert not server.boot.is_consumed
    assert "set-cookie" not in denied.headers
    denied = session_client.post("/api/auth/init", headers={"Sec-Fetch-Site": "cross-site", "X-Boot-Token": token})
    assert denied.status_code == 403
    assert not server.boot.is_consumed
    accepted = session_client.post("/api/auth/init", headers={"Origin": "http://127.0.0.1:3000", "X-Boot-Token": token})
    assert accepted.status_code == 200 and server.boot.is_consumed
    cookie = accepted.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie


def test_session_replay_and_unauthenticated_export_are_rejected(session_client):
    token = server.boot.token
    assert session_client.get("/api/kit/download").status_code == 401
    assert session_client.post("/api/auth/init", headers={"X-Boot-Token": token}).status_code == 200
    assert session_client.get("/api/kit/download").status_code == 200
    fresh = TestClient(server.app)
    assert fresh.post("/api/auth/init", headers={"X-Boot-Token": token}).status_code == 401
    assert fresh.get("/api/kit/download").status_code == 401


def test_cookie_names_isolate_editions(session_client, monkeypatch):
    monkeypatch.setattr(auth, "COOKIE_NAME", "las_session_v2e")
    assert session_client.get("/api/kit/download", headers={"Cookie": f"las_session={auth.API_KEY}"}).status_code == 401
    assert session_client.get("/api/kit/download", headers={"Cookie": f"las_session_v2e={auth.API_KEY}"}).status_code == 200


def test_only_exact_init_path_and_read_only_assets_are_exempt():
    app = FastAPI()
    app.add_middleware(auth.AuthMiddleware)

    @app.post("/api/auth/init-extra")
    async def wrong_init():
        return {"bad": True}

    @app.delete("/api/media/{mid}/file")
    async def delete_file(mid: str):
        return {"bad": True}

    @app.delete("/api/preview/{pid}/{path:path}")
    async def delete_preview(pid: str, path: str):
        return {"bad": True}

    client = TestClient(app)
    assert client.post("/api/auth/init-extra").status_code == 401
    assert client.delete("/api/media/test/file").status_code == 401
    assert client.delete("/api/preview/test/index.html").status_code == 401
    assert not auth._is_exempt("/api/auth/init-extra")


def test_non_ascii_invalid_tokens_do_not_crash():
    assert not auth.tokens_equal("\u00e9", "test")
    assert auth.tokens_equal("test", "test")
    assert not auth._BootToken().consume("\u00e9")
