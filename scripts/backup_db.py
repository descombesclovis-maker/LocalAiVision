"""Read-only logical backup of MongoDB databases: one JSON Lines file per collection.

GridFS files are ordinary collections (fs.files, fs.chunks) and are exported too.

Usage:
    python scripts/backup_db.py --out <dir> [--uri mongodb://127.0.0.1:27017] DB [DB ...]
"""

import argparse
import datetime
import json
import pathlib

from bson import json_util
from pymongo import MongoClient


def export(client: MongoClient, name: str, out: pathlib.Path) -> dict:
    db = client[name]
    target = out / name
    target.mkdir(parents=True, exist_ok=True)
    report: dict[str, int] = {}
    for col in sorted(db.list_collection_names()):
        count = 0
        with (target / f"{col}.jsonl").open("w", encoding="utf-8") as fh:
            for doc in db[col].find({}):
                fh.write(json.dumps(doc, default=json_util.default, ensure_ascii=False) + "\n")
                count += 1
        report[col] = count
    manifest = {
        "db": name,
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "collections": report,
    }
    (target / "_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uri", default="mongodb://127.0.0.1:27017")
    ap.add_argument("--out", required=True)
    ap.add_argument("dbs", nargs="+")
    args = ap.parse_args()
    client = MongoClient(args.uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    for name in args.dbs:
        print(name, export(client, name, pathlib.Path(args.out)))


if __name__ == "__main__":
    main()
