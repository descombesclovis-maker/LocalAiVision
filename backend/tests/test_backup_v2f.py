"""Logical backup round-trip and verification without connecting to a database."""

import datetime
import importlib.util
from pathlib import Path

from bson import Binary, Int64, ObjectId, json_util
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/backup_db.py"
spec = importlib.util.spec_from_file_location("las_backup_db", SCRIPT)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class Collection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, _query):
        return iter(self.documents)


class Database:
    def __init__(self, collections):
        self.collections = {name: Collection(docs) for name, docs in collections.items()}

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        return self.collections[name]


@pytest.fixture
def client():
    return {"isolated": Database({
        "projects": [{"_id": ObjectId("1234567890abcdef12345678"), "num": Int64(7),
                      "date": datetime.datetime(2026, 1, 2, 3, 4, 5), "name": "test"}],
        "mediafs.files": [{"_id": ObjectId("abcdef1234567890abcdef12"), "length": Int64(4)}],
        "mediafs.chunks": [{"_id": ObjectId("abcdef1234567890abcdef13"), "data": Binary(b"\x00\x01\x80\xff", 0)}],
    })}


def test_backup_roundtrips_bson_and_gridfs_and_verifies(client, tmp_path):
    counts = backup.export(client, "isolated", tmp_path)
    assert counts == {"mediafs.chunks": 1, "mediafs.files": 1, "projects": 1}
    saved = json_util.loads((tmp_path / "isolated/projects.jsonl").read_text(encoding="utf-8"))
    assert isinstance(saved["num"], Int64) and saved["num"] == 7
    chunk = json_util.loads((tmp_path / "isolated/mediafs.chunks.jsonl").read_text(encoding="utf-8"))
    assert bytes(chunk["data"]) == b"\x00\x01\x80\xff"
    verified = backup.verify_export(client, "isolated", tmp_path)
    assert {k: v["documents"] for k, v in verified.items()} == counts
    assert (tmp_path / "isolated/_verification.json").is_file()


def test_backup_never_overwrites_existing_folder(client, tmp_path):
    backup.export(client, "isolated", tmp_path)
    path = tmp_path / "isolated/projects.jsonl"
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        backup.export(client, "isolated", tmp_path)
    assert path.read_bytes() == original


def test_verification_detects_changed_data(client, tmp_path):
    backup.export(client, "isolated", tmp_path)
    client["isolated"]["projects"].documents[0]["name"] = "changed"
    with pytest.raises(ValueError, match="verification failed"):
        backup.verify_export(client, "isolated", tmp_path)
    assert not (tmp_path / "isolated/_verification.json").exists()


def test_verification_detects_missing_collection(client, tmp_path):
    backup.export(client, "isolated", tmp_path)
    del client["isolated"].collections["projects"]
    with pytest.raises(ValueError, match="Collection list changed"):
        backup.verify_export(client, "isolated", tmp_path)


@pytest.mark.parametrize("unsafe", ["../user", "a/b", "a\\b", "..", ""])
def test_backup_rejects_path_traversal(unsafe):
    with pytest.raises(ValueError):
        backup._safe_component(unsafe)
