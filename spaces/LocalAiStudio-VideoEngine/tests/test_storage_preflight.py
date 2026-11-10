import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage_preflight import MODEL_ARTIFACT_BYTES, storage_report


def test_artifact_estimate_covers_remote_sana_dependencies():
    assert MODEL_ARTIFACT_BYTES > 23 * 1024**3
    result = storage_report()
    assert result["required_artifact_bytes"] == MODEL_ARTIFACT_BYTES
    assert result["sufficient"] == (result["free_bytes"] >= 30 * 1024**3)


def test_storage_path_is_created_only_as_probe_not_as_download(monkeypatch, tmp_path):
    missing_cache = tmp_path / "not-created" / "hf-cache"
    result = storage_report(missing_cache)
    assert not missing_cache.exists()
    assert result["free_bytes"] > 0
