"""A fresh edition never adopts or modifies an existing user database."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("las_check_new_db", ROOT / "scripts/check_new_db.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NAME = "las_v2f_0123456789abcdef0123"


class ReadOnlyClient:
    names = []
    calls = 0

    def __init__(self, uri, serverSelectionTimeoutMS):
        type(self).calls += 1

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def list_database_names(self):
        return self.names


def test_unique_new_name_is_claimed_only_with_local_marker(tmp_path):
    ReadOnlyClient.names = []
    marker = tmp_path / "marker"
    assert module.claim_new_database(NAME, "unused", marker, ReadOnlyClient) is True
    assert marker.read_text().strip() == NAME
    # Later launch needs no Mongo read because it was already claimed.
    ReadOnlyClient.calls = 0
    assert module.claim_new_database(NAME, "unused", marker, ReadOnlyClient) is False
    assert ReadOnlyClient.calls == 0


def test_existing_database_is_refused(tmp_path):
    ReadOnlyClient.names = [NAME]
    marker = tmp_path / "marker"
    with pytest.raises(ValueError, match="existe deja"):
        module.claim_new_database(NAME, "unused", marker, ReadOnlyClient)
    assert not marker.exists()


def test_marker_cannot_be_reused_for_other_database(tmp_path):
    marker = tmp_path / "marker"
    marker.write_text("las_v2f_aaaaaaaaaaaaaaaaaaaa")
    with pytest.raises(ValueError, match="marqueur"):
        module.claim_new_database(NAME, "unused", marker, ReadOnlyClient)


@pytest.mark.parametrize("name", ["localaistudio_nextgen_original", "", "las_v2f_../../bad"])
def test_existing_user_database_names_are_rejected(tmp_path, name):
    with pytest.raises(ValueError, match="invalide"):
        module.claim_new_database(name, "unused", tmp_path / "marker", ReadOnlyClient)
