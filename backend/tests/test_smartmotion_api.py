import asyncio
import base64
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from lib import hf_video
from lib.smartmotion import camera_state
from models.schemas import SmartMotionRequest, VideoRequest
from routers import media


def test_smartmotion_progress_distinguishes_rendering_from_full_mp4_verification():
    assert media._smartmotion_progress_label({"frames_done": 60, "frames_total": 120}) == "SmartMotion · rendu 60/120 images (50%)"
    assert media._smartmotion_progress_label({"phase": "verification", "frames_done": 120, "frames_total": 120}) == "SmartMotion · vérification complète du MP4…"


def test_camera_profiles_are_bounded_and_explicit():
    for motion in ("push_in", "pan_left", "pan_right", "tilt_up", "tilt_down", "orbit_subtle", "static"):
        states = [camera_state(i, 120, 1920, 1080, motion) for i in range(120)]
        assert all(0.97 <= state["zoom"] <= 1.08 for state in states)
        assert max(abs(state["pan_x"]) for state in states) <= 35
        assert max(abs(state["pan_y"]) for state in states) <= 20
        assert states[0]["t"] == 0 and states[-1]["t"] == 1
    with pytest.raises(ValueError, match="unsupported"):
        camera_state(0, 120, 1920, 1080, "unbounded_pan")


def test_smartmotion_request_limits_duration_fps_resolution_and_motion():
    body = SmartMotionRequest(prompt="Subtle product camera move", ref_media_id="img-1", seconds=30, output_size="1920x1080", motion="orbit_subtle")
    assert body.seconds == 30 and body.fps == 24
    for kwargs in ({"seconds": 31}, {"seconds": 4}, {"fps": 30}, {"output_size": "3840x2160"}, {"motion": "walk"}):
        with pytest.raises(ValidationError):
            SmartMotionRequest(prompt="Local camera move", ref_media_id="img-1", **kwargs)


def test_video_model_listing_exposes_cloud_and_keeps_local_and_smartmotion_distinct():
    models = asyncio.run(media.video_models())
    smartmotion = next(model for model in models if model["key"] == "smartmotion")
    cloud = next(model for model in models if model["key"] == "hf_ltx")
    local = next(model for model in models if model["key"] == "comfy")
    assert smartmotion["durations"] == ["5", "10", "15", "20", "30"]
    assert "objet" in smartmotion["tagline"]
    assert cloud["durations"] == ["2"] and cloud["aspects"] == ["1:1"]
    assert "gratuit" in cloud["label"].lower() and "distant" in cloud["tagline"].lower()
    assert "ZeroGPU" not in cloud["label"] + cloud["tagline"]
    assert "ZeroGPU" in hf_video.MODEL_LABEL
    assert local["label"] == "LocalAi Video Engine — Gratuit" and "Wan 2.1" in local["tagline"]


def test_hf_cloud_i2v_is_rejected_until_real_video_is_validated(monkeypatch):
    async def available():
        return {"available": True}
    monkeypatch.setattr(media.hf_video, "status", available)
    body = VideoRequest(prompt="Animer cette image", model="hf_ltx", mode="image", duration="2", aspect_ratio="1:1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(media.create_video(body))
    assert exc.value.status_code == 400
    assert "aucun rendu I2V" in exc.value.detail


def test_smartmotion_create_uses_local_reference_and_never_overwrites(monkeypatch):
    monkeypatch.setattr(media, "_smartmotion_runtime", lambda: (Path("local-python.exe"), Path("cached-depth")))
    monkeypatch.setattr(media, "_ref_b64", lambda _mid: asyncio.sleep(0, result=(base64.b64encode(b"image-bytes").decode(), "image/png")))
    captured = {}

    async def create_media(*args, **kwargs):
        captured["media_args"] = args
        captured["media_kwargs"] = kwargs
        return {"id": "new-id", "kind": "video", "source": "smartmotion", "prompt": args[2], "model": args[3], "status": "pending", "created_at": "now", "updated_at": "now"}

    def spawn(coro):
        captured["task"] = coro

    monkeypatch.setattr(media, "create_media", create_media)
    monkeypatch.setattr(media, "spawn", spawn)
    body = SmartMotionRequest(prompt="Slow camera push", ref_media_id="existing-image", seconds=5, motion="push_in")
    result = asyncio.run(media.create_smartmotion(body))
    assert result["id"] == "new-id"
    assert captured["media_kwargs"]["duration"] == "5s"
    assert captured["media_kwargs"]["aspect_ratio"] == "source"
    assert captured["task"].cr_frame.f_locals["image_bytes"] == b"image-bytes"
    captured["task"].close()


def test_smartmotion_create_fails_closed_without_existing_local_runtime(monkeypatch):
    def unavailable():
        raise RuntimeError("runtime not installed")

    monkeypatch.setattr(media, "_smartmotion_runtime", unavailable)
    body = SmartMotionRequest(prompt="Camera move", ref_media_id="img-1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(media.create_smartmotion(body))
    assert exc.value.status_code == 503
    assert "runtime not installed" in exc.value.detail


def test_paid_video_is_rejected_before_provider_submission_without_explicit_ack(monkeypatch):
    def must_not_submit(*_args, **_kwargs):
        raise AssertionError("paid provider submission must not be reached")

    monkeypatch.setattr(media.fal, "build_payload", must_not_submit)
    monkeypatch.setattr(media, "create_media", must_not_submit)
    body = VideoRequest(prompt="Publicité cinématique", model="veo", mode="text", duration="4s", aspect_ratio="16:9")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(media.create_video(body))
    assert exc.value.status_code == 402
    assert "aucun appel n'a été soumis" in exc.value.detail
    assert media.fal.estimated_cost_usd("veo", "4s") == 0.6
