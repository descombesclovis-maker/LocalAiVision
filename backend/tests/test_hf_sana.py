import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from lib import hf_sana
from fastapi import HTTPException
from models.schemas import VideoRequest
from routers import media


def _box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def _valid_mp4() -> bytes:
    ftyp = _box(b"ftyp", b"isom\x00\x00\x02\x00isom")
    mvhd = b"\x00\x00\x00\x00" + b"\x00" * 8 + (1000).to_bytes(4, "big") + (5062).to_bytes(4, "big")
    tkhd = b"\x00" * 16 + (1280 << 16).to_bytes(4, "big") + (736 << 16).to_bytes(4, "big")
    return ftyp + _box(b"moov", _box(b"mvhd", mvhd) + _box(b"trak", _box(b"tkhd", tkhd))) + _box(b"mdat", b"x" * 32)


def test_sana_generation_contract_preserves_prompt_and_only_validated_profiles():
    prompt = "Un renard roux court de gauche à droite puis saute par-dessus une branche."
    assert hf_sana.generation_data(prompt, "5", 17) == [prompt, "5 seconds", 0.7, 20, 17, False]
    assert hf_sana.PROFILES["5"] == ("5 seconds", 81, 16)
    assert hf_sana.PROFILES["8"] == ("8 seconds", 193, 24)
    with pytest.raises(hf_sana.SanaSpaceError, match="5 ou 8"):
        hf_sana.generation_data(prompt, "3")
    assert not hf_sana._trusted_file_url("https://example.com/gradio_api/file=/tmp/x.mp4")
    assert hf_sana._trusted_file_url(hf_sana.BASE_URL + "/gradio_api/file=/tmp/x.mp4")


def test_private_space_mp4_download_uses_server_token_and_records_metrics(monkeypatch):
    token = "hf_test_server_secret_not_for_logs"
    mp4 = _valid_mp4()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers.get("authorization") == f"Bearer {token}"
        if request.url.path == "/gradio_api/info":
            return httpx.Response(200, json={"named_endpoints": {"/generate": {"parameters": [
                {"parameter_name": name} for name in ("prompt", "video_duration", "rl_lora_scale", "motion_score", "seed", "randomize_seed")
            ]}}})
        if request.url.path == "/gradio_api/call/generate" and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["data"] == ["Prompt original français", "5 seconds", 0.7, 20, 42, False]
            return httpx.Response(200, json={"event_id": "evt-safe"})
        if request.url.path == "/gradio_api/call/generate/evt-safe":
            file_url = hf_sana.BASE_URL + "/gradio_api/file=/tmp/generated.mp4"
            body = f'event: complete\ndata: [[{{"path":"/tmp/generated.mp4","url":"{file_url}"}},42]]\n\n'
            return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
        if request.url.path == "/gradio_api/file=/tmp/generated.mp4":
            return httpx.Response(200, content=mp4, headers={"content-type": "video/mp4"})
        return httpx.Response(404)

    original = hf_sana.httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(hf_sana.httpx, "AsyncClient", client_factory)
    progress = []

    async def on_progress(text: str):
        progress.append(text)

    data, report = asyncio.run(hf_sana.generate("Prompt original français", "5", token, on_progress))
    assert data == mp4
    assert report["model"] == hf_sana.MODEL
    assert report["duration_seconds"] == 5.062
    assert report["video_tracks"] == [{"width": 1280, "height": 736}]
    assert report["output_fps"] == 16
    assert report["output_frames_expected"] == 81
    assert report["requested_prompt_verbatim"] == "Prompt original français"
    assert any("récupération" in text for text in progress)
    assert len(seen) == 4
    assert token not in repr(report)


def test_private_sana_route_refuses_i2v_and_unvalidated_profiles_before_any_submission(monkeypatch):
    def no_network(*_args, **_kwargs):
        raise AssertionError("unsupported profiles must be rejected before remote calls")
    monkeypatch.setattr(media.hf_sana, "status", no_network)
    for body in (
        VideoRequest(prompt="Animate the reference", model="hf_sana", mode="image", duration="5", aspect_ratio="16:9"),
        VideoRequest(prompt="A fox runs", model="hf_sana", mode="text", duration="3", aspect_ratio="16:9"),
        VideoRequest(prompt="A fox runs", model="hf_sana", mode="text", duration="5", aspect_ratio="1:1"),
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(media.create_video(body))
        assert exc.value.status_code == 400
    with pytest.raises(hf_sana.SanaSpaceError, match="prompt"):
        hf_sana.generation_data("   ", "5")


def test_private_sana_route_checks_server_credential_and_remote_status(monkeypatch):
    async def token():
        return "hf_private_server_token"
    async def unavailable(_token):
        return {"available": False, "reason": "engine is cold"}
    monkeypatch.setattr(media, "_saved_hf_token", token)
    monkeypatch.setattr(media.hf_sana, "status", unavailable)
    body = VideoRequest(prompt="A fox crosses a forest", model="hf_sana", mode="text", duration="5", aspect_ratio="16:9")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(media.create_video(body))
    assert exc.value.status_code == 503 and "engine is cold" in exc.value.detail


def test_private_sana_api_saves_verified_result_through_existing_media_library(monkeypatch):
    updates = []
    saved = []
    document = {"id": "generated-1", "kind": "video", "source": "hf-private-space", "prompt": "A fox runs", "model": hf_sana.MODEL, "status": "pending", "created_at": "now", "updated_at": "now"}

    async def token():
        return "hf_private_server_token"
    async def ready(_token):
        return {"available": True}
    async def create_media(*args, **kwargs):
        assert args[:4] == ("video", "hf-private-space", "A fox runs", hf_sana.MODEL)
        assert kwargs == {"aspect_ratio": "16:9", "duration": "5s"}
        return document.copy()
    async def generate(prompt, seconds, _token, _progress):
        assert prompt == "A fox runs" and seconds == "5"
        return _valid_mp4(), {"provider": "private Space", "duration_seconds": 5.062}
    async def update_one(query, update):
        updates.append((query, update))
    async def find_one(query, projection=None):
        return {"status": "running"}
    async def finish(mid, data, mime):
        saved.append((mid, data, mime))
    monkeypatch.setattr(media, "_saved_hf_token", token)
    monkeypatch.setattr(media.hf_sana, "status", ready)
    monkeypatch.setattr(media.hf_sana, "generate", generate)
    monkeypatch.setattr(media, "create_media", create_media)
    monkeypatch.setattr(media, "finish_media", finish)
    monkeypatch.setattr(media, "db", SimpleNamespace(media=SimpleNamespace(update_one=update_one, find_one=find_one)))
    body = VideoRequest(prompt="A fox runs", model="hf_sana", mode="text", duration="5", aspect_ratio="16:9")

    async def exercise():
        result = await media.create_video(body)
        assert result["id"] == "generated-1" and result["status"] == "pending"
        task = media._SANA_CLOUD_TASKS["generated-1"]
        await task

    asyncio.run(exercise())
    assert saved == [("generated-1", _valid_mp4(), "video/mp4")]
    assert any("generation_metrics" in update.get("$set", {}) for _, update in updates)
    assert "generated-1" not in media._SANA_CLOUD_TASKS


def test_private_sana_is_not_exposed_to_the_existing_ui_model_list():
    models = asyncio.run(media.video_models())
    assert "hf_sana" not in {model["key"] for model in models}
    assert any(model["key"] == "hf_ltx" for model in models)
    assert any(model["key"] == "comfy" for model in models)
