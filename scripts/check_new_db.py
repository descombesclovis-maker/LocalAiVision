"""Claim a random, new edition database without modifying MongoDB.

On first launch refuse an existing MongoDB database, then create a local ownership marker.
Subsequent launches only accept that same marker. This is not a migration or a backup.
"""
import os
from pathlib import Path
import re
import sys

from pymongo import MongoClient


NAME = re.compile(r"las_v2f_[0-9a-f]{20}\Z")


def claim_new_database(name: str, uri: str, marker: Path, client_factory=MongoClient) -> bool:
    if not NAME.fullmatch(name):
        raise ValueError("Nom de base V2-F invalide")
    marker = Path(marker)
    if marker.exists():
        if marker.read_text(encoding="ascii").strip() != name:
            raise ValueError("Le marqueur local ne correspond pas a la base")
        return False
    with client_factory(uri, serverSelectionTimeoutMS=4000) as client:
        if name in client.list_database_names():
            raise ValueError("La base existe deja : installation refusee pour proteger les donnees")
    with marker.open("x", encoding="ascii") as fh:
        fh.write(name + "\n")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_new_db.py <local-marker>", file=sys.stderr)
        return 2
    try:
        claim_new_database(os.environ.get("DB_NAME", ""), os.environ.get("MONGO_URL", ""), Path(sys.argv[1]))
    except Exception as exc:
        print(f"Base non initialisee : {type(exc).__name__}. Verifiez MongoDB et le nom de base.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
