from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import projects


@pytest.fixture
def client(monkeypatch):
    def files(text):
        return [{"path": "index.html", "content": f"<main>{text}</main>"}]

    async def find_version(query):
        if query in ({"project_id": "atelier", "number": 1}, {"project_id": "atelier", "number": 2}):
            return {"files": files(f"Archive V{query['number']}")}

    monkeypatch.setattr(projects, "_get", AsyncMock(return_value={"files": files("Brouillon courant")}))
    monkeypatch.setattr(projects, "db", SimpleNamespace(versions=SimpleNamespace(find_one=find_version)))
    app = FastAPI()
    app.include_router(projects.router)
    with TestClient(app) as browser:
        yield browser


@pytest.mark.parametrize(("query", "expected"), [
    ("", "Brouillon courant"), ("?v=0", "Brouillon courant"),
    ("?v=1", "Archive V1"), ("?v=2", "Archive V2"),
])
def test_preview_source(client, query, expected):
    response = client.get("/preview/atelier/index.html" + query)
    assert response.status_code == 200
    assert expected in response.text


@pytest.mark.parametrize("accept", ["application/json", "text/html"])
def test_missing_version_never_serves_draft(client, accept):
    response = client.get("/preview/atelier/index.html?v=999", headers={"Accept": accept})
    assert response.status_code == 404
    assert "Brouillon courant" not in response.text
    assert "Version 999 introuvable" in response.text
    assert response.headers["content-type"].startswith(accept)
    assert response.headers["cache-control"] == "no-store"
