"""Pytest bootstrap for the backend.

`lib.db` reads MONGO_URL / DB_NAME from the environment at import time and builds a (lazy) Motor
client, so the unit tests can import the whole backend with dummy values and no running database.
We also put the backend root on sys.path so `import lib.*` / `import routers.*` works.
"""
import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "localaistudio_test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
os.environ.setdefault("LAS_BOOT_TOKEN", "test-boot-token")

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Motor v3.x requires an event loop to exist when AsyncIOMotorGridFSBucket is created at
# module import time (lib/store.py).  Tests that import `server` indirectly (e.g. TestCorsConfig)
# would fail with "There is no current event loop in thread" if the loop is not pre-created.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
