"""Integration test against an isolated database on a disposable MongoDB server."""
import os
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import MongoClient

from lib.db import LoopBoundClient, LoopBoundDatabase
from routers import projects


def test_reference_lifecycle(monkeypatch):
    uri = os.getenv("LAS_TEST_MONGO_URL")
    if not uri:
        pytest.skip("Set LAS_TEST_MONGO_URL to run the MongoDB reference lifecycle")
    name = "reference_test_" + uuid4().hex
    with MongoClient(uri) as client:
        db = client[name]
        project = dict(id="p", name="Studio", prompt="Projet témoin", mode="libre", llm="local",
                       status="ready", created_at="2026-11-18", updated_at="2026-11-18")
        db.projects.insert_one(project)
        for pid, sid, number in [("p", "one", 1), ("p", "two", 2), ("other", "foreign", 1)]:
            db.versions.insert_one(dict(project_id=pid, id=sid, number=number, files=[]))
        app = FastAPI()
        app.include_router(projects.router)
        motor = LoopBoundClient(uri)
        monkeypatch.setattr(projects, "db", LoopBoundDatabase(motor, name))
        try:
            with TestClient(app) as api:
                def choose(sid, previous=None):
                    return api.put("/projects/p/preview-reference", json={
                        "snapshot_id": sid, "previous_snapshot_id": previous,
                    })

                assert api.get("/projects/p").json()["preview_reference"] is None
                first = choose("one").json()["preview_reference"]
                assert first["number"] == 1 and first["validated_at"]
                assert choose("one").json()["preview_reference"] == first
                assert db.projects.find_one({"id": "p"})["preview_reference"] == first
                for sid in ("foreign", "missing"):
                    assert choose(sid, "one").status_code == 404
                assert choose("two").status_code == 409
                assert api.get("/projects/p").json()["preview_reference"] == first
                assert choose("two", "one").json()["preview_reference"]["number"] == 2
                assert db.versions.count_documents({"project_id": "p"}) == 2
        finally:
            motor.close()
            client.drop_database(name)


def test_snapshot_pages_and_assets_stay_in_their_snapshot(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    files = {
        "index.html": '<a href="pages/suite.html">Suite</a>',
        "pages/suite.html": '<link href="/style.css"><script src="../app.js"></script>',
        "style.css": 'body { background: url(/image.svg) }',
        "image.svg": "<svg/>",
        "app.js": "document.title='V1'",
    }
    async def lookup(query):
        if query == {"project_id": "p", "id": "one"}:
            return {"files": [{"path": path, "content": text} for path, text in files.items()]}

    monkeypatch.setattr(projects, "db", SimpleNamespace(versions=SimpleNamespace(find_one=lookup)))
    draft = AsyncMock(side_effect=AssertionError("Lecture accidentelle du brouillon"))
    monkeypatch.setattr(projects, "_get", draft)
    app = FastAPI()
    app.include_router(projects.router)
    root = "/preview/snapshots/p/one/"
    with TestClient(app) as api:
        assert 'href="pages/suite.html"' in api.get(root + "index.html").text
        page = api.get(root + "pages/suite.html").text
        assert "/api" + root + "style.css" in page and 'src="../app.js"' in page
        assert root + "image.svg" in api.get(root + "style.css").text
        assert api.get(root + "app.js").text == files["app.js"]
        assert api.get(root + "missing.css").status_code == 404
        assert api.get("/preview/snapshots/other/one/index.html").status_code == 404
