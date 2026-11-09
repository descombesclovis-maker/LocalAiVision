"""V2-D: Motor client must be created in the loop that runs the request.

Regression for "got Future attached to a different loop" (media, projects and settings returned 500 under
uvicorn). No MongoDB needed: Motor is replaced by a fake that records which loop created each client.
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")
os.environ.setdefault("DB_NAME", "localaistudio_loop_tests")

import lib.db as dbmod  # noqa: E402


class _FakeCollection:
    def __init__(self, name, owner):
        self.name = name
        self.owner = owner

    async def count_documents(self, _filter):
        return 7


class _FakeMotorDb:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def __getitem__(self, collection):
        return _FakeCollection(collection, self)

    def __getattr__(self, collection):
        return _FakeCollection(collection, self)


class _FakeMotorClient:
    created_in = []

    def __init__(self, url):
        self.url = url
        self.closed = False
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        _FakeMotorClient.created_in.append(self)

    def __getitem__(self, name):
        return _FakeMotorDb(self, name)

    def close(self):
        self.closed = True


def _fresh(monkeypatch):
    _FakeMotorClient.created_in = []
    monkeypatch.setattr(dbmod, "AsyncIOMotorClient", _FakeMotorClient)
    client = dbmod.LoopBoundClient("mongodb://fake")
    return client, dbmod.LoopBoundDatabase(client, "nextgen_test")


def test_client_is_created_inside_the_running_loop(monkeypatch):
    client, db = _fresh(monkeypatch)

    async def op():
        return await db["media"].count_documents({})

    assert asyncio.run(op()) == 7
    assert len(_FakeMotorClient.created_in) == 1
    assert _FakeMotorClient.created_in[0].loop is not None  # created while a loop was running


def test_second_loop_gets_a_fresh_client_and_old_one_is_closed(monkeypatch):
    client, db = _fresh(monkeypatch)

    async def op():
        return await db.media.count_documents({})

    assert asyncio.run(op()) == 7  # loop 1 (e.g. lifespan)
    first = _FakeMotorClient.created_in[0]
    assert asyncio.run(op()) == 7  # loop 2 (e.g. request handling)
    assert len(_FakeMotorClient.created_in) == 2
    assert first.closed is True


def test_same_loop_reuses_one_client(monkeypatch):
    client, db = _fresh(monkeypatch)

    async def many():
        for _ in range(3):
            await db.projects.count_documents({})
        return await db["versions"].count_documents({})

    assert asyncio.run(many()) == 7
    assert len(_FakeMotorClient.created_in) == 1


def test_gridfs_bucket_receives_a_real_motor_database(monkeypatch):
    """lib.store builds a GridFS bucket per use; it must get a MotorDatabase, not the proxy."""
    client, db = _fresh(monkeypatch)
    import lib.store as store
    monkeypatch.setattr(store, "db", db)

    seen = {}

    class _Bucket:
        def __init__(self, database, bucket_name):
            seen["database"] = database
            seen["bucket_name"] = bucket_name

        async def open_download_stream(self, _id):
            return "stream"

    monkeypatch.setattr(store, "AsyncIOMotorGridFSBucket", _Bucket)

    async def op():
        return await store.bucket.open_download_stream("x")

    assert asyncio.run(op()) == "stream"
    assert seen["bucket_name"] == "mediafs"
    assert isinstance(seen["database"], _FakeMotorDb)


def test_proxy_is_a_module_level_handle_used_by_routers():
    """Importers keep their `from lib.db import db` lines; the proxy must stay the exported object."""
    assert isinstance(dbmod.db, dbmod.LoopBoundDatabase)
    assert isinstance(dbmod.client, dbmod.LoopBoundClient)
