"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

mongo_url = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


class LoopBoundClient:
    """Motor client created inside the running event loop, recreated when the loop changes.

    Motor binds its I/O to the loop that is current when the client is created. A module-level client is
    created at import time, before the server's loop starts, so queries fail with "attached to a different
    loop" (reproduced under uvicorn on Windows in V2-D: media, projects and settings all returned 500).
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: AsyncIOMotorClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def current(self) -> AsyncIOMotorClient:
        loop = asyncio.get_running_loop()
        if self._client is None or self._loop is not loop:
            self.close()
            self._client = AsyncIOMotorClient(self._url)
            self._loop = loop
        return self._client

    def __getitem__(self, name: str):
        return self.current()[name]

    def __getattr__(self, name: str):
        return getattr(self.current(), name)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # the previous loop may already be closed
                pass
        self._client = None
        self._loop = None


class LoopBoundDatabase:
    """Database handle resolved on each access, so `db.media` always uses the running loop's client."""

    def __init__(self, client: LoopBoundClient, name: str) -> None:
        self._client = client
        self._name = name

    def __getitem__(self, collection: str):
        return self._client.current()[self._name][collection]

    def motor(self):
        """The real Motor database of the running loop (required by GridFS)."""
        return self._client.current()[self._name]

    def __getattr__(self, collection: str):
        return getattr(self._client.current()[self._name], collection)


client = LoopBoundClient(mongo_url)
db = LoopBoundDatabase(client, DB_NAME)

logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "projects": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("status", ASCENDING)], name="status"),
        IndexModel([("mode", ASCENDING), ("updated_at", DESCENDING)], name="mode_updated"),
    ],
    "versions": [IndexModel([("project_id", ASCENDING), ("number", DESCENDING)], name="project_number")],
    "media": [
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created"),
        IndexModel([("kind", ASCENDING), ("created_at", DESCENDING)], name="kind_created"),
    ],
    "brands": [IndexModel([("id", ASCENDING)], name="id", unique=True)],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)
