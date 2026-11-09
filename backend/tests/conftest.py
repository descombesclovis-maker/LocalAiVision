"""Pytest bootstrap for the backend.

`lib.db` reads MONGO_URL / DB_NAME from the environment at import time and builds a (lazy) Motor
client, so the unit tests can import the whole backend with dummy values and no running database.
We also put the backend root on sys.path so `import lib.*` / `import routers.*` works.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "localaistudio_test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
