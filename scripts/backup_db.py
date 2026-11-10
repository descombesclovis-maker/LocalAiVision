"""Read-only MongoDB backup with GridFS, canonical Extended JSON and optional verification.

This is not an atomic MongoDB snapshot. For reliable results, stop writes first. Verification
compares every exported BSON document with the live collections (including GridFS chunks);
it does not restore or modify a database. Existing backups are never overwritten.

Usage:
    python scripts/backup_db.py --out <new-dir> --verify DB [DB ...]
"""

import argparse
from collections import Counter
import datetime
import hashlib
import json
import pathlib

from bson import json_util
from pymongo import MongoClient


def _safe_component(name: str) -> str:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("Unsafe database/collection name for backup")
    return name


def _canonical(doc: dict) -> str:
    # Canonical Extended JSON keeps BSON Int64, ObjectId, dates and binary subtypes intact.
    return json_util.dumps(doc, json_options=json_util.CANONICAL_JSON_OPTIONS, ensure_ascii=False, sort_keys=True)


def _digest(doc: dict) -> str:
    return hashlib.sha256(_canonical(doc).encode("utf-8")).hexdigest()


def export(client: MongoClient, name: str, out: pathlib.Path) -> dict:
    db = client[name]
    target = pathlib.Path(out) / _safe_component(name)
    target.mkdir(parents=True, exist_ok=False)
    report: dict[str, int] = {}
    for col in sorted(db.list_collection_names()):
        count = 0
        with (target / f"{_safe_component(col)}.jsonl").open("x", encoding="utf-8") as fh:
            for doc in db[col].find({}):
                fh.write(_canonical(doc) + "\n")
                count += 1
        report[col] = count
    manifest = {
        "db": name,
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "format": "canonical-extended-json-lines",
        "collections": report,
    }
    (target / "_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def verify_export(client: MongoClient, name: str, out: pathlib.Path) -> dict:
    """Compare every exported document with a fresh read of the source DB, without writes to MongoDB."""
    target = pathlib.Path(out) / _safe_component(name)
    manifest = json.loads((target / "_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("db") != name:
        raise ValueError("Backup manifest database does not match")
    db = client[name]
    expected = manifest["collections"]
    if set(expected) != set(db.list_collection_names()):
        raise ValueError("Collection list changed since export")
    verified = {}
    for col, count in sorted(expected.items()):
        saved: Counter[str] = Counter()
        with (target / f"{_safe_component(col)}.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                saved[_digest(json_util.loads(line))] += 1
        live = Counter(_digest(doc) for doc in db[col].find({}))
        if saved != live or sum(saved.values()) != count:
            raise ValueError(f"Backup verification failed for collection {col}")
        aggregate = hashlib.sha256("\n".join(sorted(saved.elements())).encode("ascii")).hexdigest()
        verified[col] = {"documents": count, "sha256": aggregate}
    report = {
        "db": name,
        "verified_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "method": "canonical BSON document hashes compared to live source; not a restore or atomic snapshot",
        "collections": verified,
    }
    with (target / "_verification.json").open("x", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    return verified


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uri", default="mongodb://127.0.0.1:27017")
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true", help="compare the export with the live source (read-only)")
    ap.add_argument("dbs", nargs="+")
    args = ap.parse_args()
    client = MongoClient(args.uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    for name in args.dbs:
        print(name, "exported:", export(client, name, pathlib.Path(args.out)))
        if args.verify:
            print(name, "verified:", {k: v["documents"] for k, v in verify_export(client, name, pathlib.Path(args.out)).items()})


if __name__ == "__main__":
    main()
