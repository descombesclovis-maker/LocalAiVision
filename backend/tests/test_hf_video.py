import base64
import pytest

from lib import hf_video, secure_secret


def _box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def _valid_mp4() -> bytes:
    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isom")
    mvhd_payload = b"\x00\x00\x00\x00" + b"\x00" * 8 + (1000).to_bytes(4, "big") + (1900).to_bytes(4, "big")
    tkhd_payload = b"\x00" * 16 + (256 << 16).to_bytes(4, "big") + (256 << 16).to_bytes(4, "big")
    trak = _box(b"trak", _box(b"tkhd", tkhd_payload))
    moov = _box(b"moov", _box(b"mvhd", mvhd_payload) + trak)
    mdat = _box(b"mdat", b"x" * 32)
    return ftyp + moov + mdat


def test_verify_mp4_extracts_duration_and_dimensions():
    result = hf_video.verify_mp4(_valid_mp4())
    assert result["container"] == "mp4"
    assert result["duration_seconds"] == 1.9
    assert result["video_tracks"] == [{"width": 256, "height": 256}]
    assert {"ftyp", "moov", "mdat"}.issubset(result["top_level_boxes"])


def test_verify_mp4_rejects_html_and_truncated_atoms():
    with pytest.raises(hf_video.HfVideoError, match="signature"):
        hf_video.verify_mp4(b"<html>not a movie" * 10)
    good = _valid_mp4()
    with pytest.raises(hf_video.HfVideoError, match="incomplet"):
        hf_video.verify_mp4(good[:-4])


def test_dpapi_envelope_roundtrip_is_delegated_to_windows_dpapi(monkeypatch):
    def fake_dpapi(data: bytes, *, protect: bool) -> bytes:
        return b"encrypted:" + data if protect else data.removeprefix(b"encrypted:")
    monkeypatch.setattr(secure_secret, "_dpapi", fake_dpapi)
    saved = secure_secret.encrypt_secret("hf_example_private_secret")
    assert "hf_example_private_secret" not in saved
    assert secure_secret.decrypt_secret(saved) == "hf_example_private_secret"
    assert base64.b64decode(saved).startswith(b"encrypted:")


def test_only_truly_validated_cloud_configuration_is_available():
    assert hf_video.FREE_QUOTA.startswith("Ce connecteur appelle le Space sans jeton")
    assert hf_video.MODEL_LABEL.startswith("Hugging Face ZeroGPU")
