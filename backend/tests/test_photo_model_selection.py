"""V2-E: photo model selection from the UI, installed-state detection and real step progress.

No GPU and no installed model is touched: ComfyUI listings are monkeypatched and the websocket
test uses a local websockets server that replays ComfyUI-style progress messages.
"""

import asyncio
import json
import time

import pytest
from pydantic import ValidationError

from lib import comfy
from models.schemas import ImageRequest

BASE = {
    "image_preset": "flux-dev",
    "image_checkpoint": "flux1-dev-fp8.safetensors",
    "base_url": "http://127.0.0.1:8188",
}


# ---------------------------------------------------------------- per-request preset
def test_image_settings_applies_preset_and_checkpoint_without_mutating_input():
    out = comfy.image_settings(BASE, "sdxl")
    assert out["image_preset"] == "sdxl"
    assert out["image_checkpoint"] == "sd_xl_base_1.0.safetensors"
    assert BASE["image_preset"] == "flux-dev"  # saved settings untouched


def test_image_settings_none_keeps_saved_settings():
    assert comfy.image_settings(BASE, None) is BASE


def test_image_settings_rejects_unknown_preset():
    with pytest.raises(ValueError):
        comfy.image_settings(BASE, "not-a-model")


def test_request_schema_rejects_unknown_comfy_preset():
    assert ImageRequest(prompt="un flacon bleu", comfy_preset="sdxl").comfy_preset == "sdxl"
    assert ImageRequest(prompt="un flacon bleu").comfy_preset is None
    with pytest.raises(ValidationError):
        ImageRequest(prompt="un flacon bleu", comfy_preset="../etc")


def test_workflow_uses_the_selected_checkpoint_and_sampler():
    wf = comfy._image_workflow(comfy.image_settings(BASE, "flux-schnell"), "p", 1024, 1024, 1, None)
    assert wf["1"]["inputs"]["ckpt_name"] == "flux1-schnell-fp8.safetensors"
    assert wf["5"]["inputs"]["steps"] == 4  # schnell sampler profile


# ---------------------------------------------------------------- installed state
@pytest.mark.asyncio
async def test_image_model_status_reports_installed_presets(monkeypatch):
    async def fake_choices(c, base, node, field, cache=None):
        assert (node, field) == ("CheckpointLoaderSimple", "ckpt_name")
        return ["sd_xl_base_1.0.safetensors", "flux1-schnell-fp8.safetensors"]

    monkeypatch.setattr(comfy, "_choices", fake_choices)
    rows = {r["key"]: r["installed"] for r in await comfy.image_model_status(BASE)}
    assert rows == {"flux-dev": False, "flux-schnell": True, "sdxl": True}


@pytest.mark.asyncio
async def test_image_model_status_is_unknown_when_comfyui_cannot_list(monkeypatch):
    async def unavailable(*args, **kwargs):
        return None

    monkeypatch.setattr(comfy, "_choices", unavailable)
    rows = await comfy.image_model_status(BASE)
    assert all(r["installed"] is None for r in rows)  # never reported as missing by mistake


# ---------------------------------------------------------------- progress parsing
@pytest.mark.parametrize(
    "msg, expected",
    [
        ({"type": "progress", "data": {"value": 7, "max": 30, "prompt_id": "p1", "node": "5"}}, "étape 7/30"),
        ({"type": "progress", "data": {"value": 3, "max": 30}}, "étape 3/30"),  # older ComfyUI: no prompt_id
        ({"type": "progress", "data": {"value": 1, "max": 30, "prompt_id": "other"}}, None),  # another job
        ({"type": "executing", "data": {"node": None, "prompt_id": "p1"}}, None),
        ({"type": "progress", "data": {"value": 5, "max": 0}}, None),
        ({"type": "progress", "data": {"value": 31, "max": 30}}, None),
        ("not-a-dict", None),
    ],
)
def test_progress_from_ws_only_reports_own_steps(msg, expected):
    label = comfy.progress_from_ws(msg, "p1", 12)
    if expected is None:
        assert label is None
    else:
        assert expected in label and label.endswith("12s")


# ---------------------------------------------------------------- real websocket stream
@pytest.mark.asyncio
async def test_ws_progress_streams_step_labels_from_a_local_comfy_like_server():
    websockets = pytest.importorskip("websockets")
    from websockets.asyncio.server import serve

    async def handler(ws):
        for v in (1, 2, 3):
            await ws.send(json.dumps({"type": "progress", "data": {"value": v, "max": 3, "prompt_id": "p1", "node": "5"}}))
        await ws.send(json.dumps({"type": "progress", "data": {"value": 9, "max": 9, "prompt_id": "other"}}))
        await asyncio.sleep(3)

    async with serve(handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        labels: list[str] = []

        async def progress(label: str) -> None:
            labels.append(label)

        live = {"steps": False}
        task = asyncio.create_task(
            comfy._ws_progress(f"http://127.0.0.1:{port}", "client-x", "p1", progress, time.monotonic(), live)
        )
        for _ in range(200):
            if len(labels) >= 3:
                break
            await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert [("étape " + l.split("étape ")[1].split(" ")[0]) for l in labels] == ["étape 1/3", "étape 2/3", "étape 3/3"]
    assert live["steps"] is True
    assert websockets is not None


@pytest.mark.asyncio
async def test_ws_progress_failure_is_silent_and_leaves_fallback_active():
    live = {"steps": False}
    # Nothing listens on this port: the helper must return quietly, never raise into the render.
    await asyncio.wait_for(
        comfy._ws_progress("http://127.0.0.1:9", "client-y", "p1", None, time.monotonic(), live), timeout=15
    )
    assert live["steps"] is False
