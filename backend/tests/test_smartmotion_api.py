import asyncio
import base64
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from lib.smartmotion import camera_state
from models.schemas import SmartMotionRequest
from routers import media


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


def test_video_model_listing_exposes_smartmotion_as_distinct_camera_only_mode():
    models = asyncio.run(media.video_models())
    smartmotion = next(model for model in models if model["key"] == "smartmotion")
    assert smartmotion["durations"] == ["5", "10", "15", "20", "30"]
    assert "objet" in smartmotion["tagline"]


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
