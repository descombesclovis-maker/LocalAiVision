import json
from pathlib import Path

import pytest

from lib.smartmotion import camera_state, discover_local_depth_model, recommend_mode


def test_smartmotion_only_recommended_for_still_camera_motion():
    assert recommend_mode(still_image=True, requested_motion="product-ad")["mode"] == "SmartMotion"
    assert recommend_mode(still_image=True, requested_motion="character walking")["mode"] == "Cinematic"
    assert recommend_mode(still_image=False, requested_motion="camera")["mode"] == "Cinematic"
    assert recommend_mode(still_image=True, requested_motion="character walking", fast_model_available=True)["mode"] == "FastVideo"


def test_router_explains_2_5d_limits():
    choice = recommend_mode(still_image=True, requested_motion="camera")
    assert "no object motion" in choice["reason"]
    assert "generative" in recommend_mode(still_image=True, requested_motion="object-motion")["reason"]


def test_camera_path_is_smooth_bounded_and_ends_at_seven_percent_push_in():
    states = [camera_state(i, 120, 1024, 1024) for i in range(120)]
    assert states[0]["zoom"] == pytest.approx(1.0)
    assert states[-1]["zoom"] == pytest.approx(1.07)
    assert all(1.0 <= s["zoom"] <= 1.07 for s in states)
    assert max(abs(s["pan_x"]) for s in states) < 18
    assert max(abs(s["pan_y"]) for s in states) < 5
    assert max(abs(states[i+1]["pan_x"] - states[i]["pan_x"]) for i in range(119)) < 1


def test_local_depth_discovery_never_accepts_partial_or_wrong_snapshot(tmp_path: Path):
    incomplete = tmp_path / "bad"
    incomplete.mkdir()
    (incomplete / "config.json").write_text(json.dumps({"model_type":"depth_anything"}), encoding="utf8")
    with pytest.raises(FileNotFoundError, match="no model was downloaded"):
        discover_local_depth_model(tmp_path)
    valid = tmp_path / "valid"
    valid.mkdir()
    (valid / "config.json").write_text(json.dumps({"model_type":"depth_anything"}), encoding="utf8")
    (valid / "model.safetensors").write_bytes(b"local-only-test")
    (valid / "preprocessor_config.json").write_text("{}", encoding="utf8")
    assert discover_local_depth_model(tmp_path) == valid
