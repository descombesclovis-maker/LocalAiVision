"""V1-D: workflow-scoped discovery and the direct LocalAiWeb hero-video caller.

All HTTP/DB/render operations are simulated; these are not GPU/visual quality tests.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from lib import comfy


LOADERS = {
    "CheckpointLoaderSimple": {"ckpt_name": [comfy.DEFAULTS["image_checkpoint"]]},
    "UNETLoader": {"unet_name": [comfy.DEFAULTS["video_model"]]},
    "CLIPLoader": {"clip_name": [comfy.DEFAULTS["video_text_encoder"]]},
    "VAELoader": {"vae_name": [comfy.DEFAULTS["video_vae"]]},
}


def mock_comfy(monkeypatch, loaders):
    calls = []

    def respond(request):
        calls.append(request.url.path)
        if request.url.path == "/system_stats":
            return httpx.Response(200, json={"devices": []})
        node = request.url.path.rsplit("/", 1)[-1]
        fields = loaders.get(node)
        if fields is None:
            return httpx.Response(503)
        return httpx.Response(200, json={node: {"input": {"required": {
            field: [values] for field, values in fields.items()
        }}}})

    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(comfy, "_client", lambda timeout=30: httpx.AsyncClient(transport=transport))
    return calls


@pytest.mark.parametrize("preset", ["sdxl", "flux-dev", "flux-schnell"])
async def test_image_only_requests_checkpoint(monkeypatch, preset):
    s = {**comfy.DEFAULTS, "image_preset": preset, "image_checkpoint": comfy.IMAGE_PRESETS[preset]["checkpoint"]}
    calls = mock_comfy(monkeypatch, {"CheckpointLoaderSimple": {"ckpt_name": [s["image_checkpoint"]]}})
    await comfy.verify_ready(s)
    assert calls == ["/system_stats", "/object_info/CheckpointLoaderSimple"]
    assert comfy._lists_unavailable({"checkpoints": [s["image_checkpoint"]], "vae": None}, False, s) == []


@pytest.mark.parametrize("preset,expected", [
    ("wan22", ["UNETLoader", "CLIPLoader", "VAELoader"]),
    ("ltxv", ["CheckpointLoaderSimple", "CLIPLoader"]),
])
async def test_video_uses_its_own_model_pool_without_photo_or_unused_vae(monkeypatch, preset, expected):
    s = {**comfy.DEFAULTS, "video_preset": preset, "image_checkpoint": "absent-photo.safetensors"}
    s.update({"video_" + key: value for key, value in comfy.VIDEO_PRESETS[preset].items() if key != "label"})
    # A stale VAE setting must not make LTX depend on an external VAE.
    s["video_vae"] = "unused.safetensors" if preset == "ltxv" else s["video_vae"]
    loaders = {
        "UNETLoader" if preset == "wan22" else "CheckpointLoaderSimple": {
            "unet_name" if preset == "wan22" else "ckpt_name": [s["video_model"]]
        },
        "CLIPLoader": {"clip_name": [s["video_text_encoder"]]},
    }
    if preset == "wan22":
        loaders["VAELoader"] = {"vae_name": [s["video_vae"]]}
    calls = mock_comfy(monkeypatch, loaders)
    await comfy.verify_ready(s, video=True)
    assert calls == ["/system_stats"] + [f"/object_info/{node}" for node in expected]


@pytest.mark.parametrize("video", [False, True])
async def test_only_required_unavailable_lists_are_reported(monkeypatch, video):
    calls = mock_comfy(monkeypatch, {})
    s = {**comfy.DEFAULTS}
    with pytest.raises(comfy.ModelListUnavailable) as error:
        await comfy.verify_ready(s, video)
    message = str(error.value)
    assert "inaccessible" in message
    assert ("checkpoints" in message) is not video
    assert ("vae" in message) is video
    assert len(calls) == (4 if video else 2)
    assert comfy._missing_files(s, {}, video) == []


async def test_confirmed_missing_is_not_hidden_by_another_unavailable_list(monkeypatch):
    mock_comfy(monkeypatch, {"UNETLoader": {"unet_name": []}})
    with pytest.raises(comfy.MissingModel, match=comfy.DEFAULTS["video_model"]):
        await comfy.verify_ready(dict(comfy.DEFAULTS), video=True)


async def test_unsupported_video_preset_is_refused(monkeypatch):
    mock_comfy(monkeypatch, {})
    s = {**comfy.DEFAULTS, "video_preset": "nonexistent-preset"}
    with pytest.raises(comfy.WorkflowError, match="non pris en charge"):
        comfy._video_workflow(s, "prompt", 832, 480, 73, 1, None)


async def test_wan21_fun_camera_requires_image(monkeypatch):
    mock_comfy(monkeypatch, {})
    s = {**comfy.DEFAULTS, "video_preset": "wan21_fun_camera"}
    s.update({k: v for k, v in comfy.VIDEO_PRESETS["wan21_fun_camera"].items() if k != "label"})
    with pytest.raises(comfy.WorkflowError, match="Image-to-Video"):
        comfy._video_workflow(s, "prompt", 832, 480, 73, 1, None)


async def test_wan21_fun_camera_builds_i2v_camera_workflow(monkeypatch):
    mock_comfy(monkeypatch, {
        "UNETLoader": {"unet_name": [comfy.VIDEO_PRESETS["wan21_fun_camera"]["model"]]},
        "CLIPLoader": {"clip_name": [comfy.VIDEO_PRESETS["wan21_fun_camera"]["text_encoder"]]},
        "VAELoader": {"vae_name": [comfy.VIDEO_PRESETS["wan21_fun_camera"]["vae"]]},
        "CLIPVisionLoader": {"clip_name": ["clip_vision_h.safetensors"]},
    })
    s = {**comfy.DEFAULTS, "video_preset": "wan21_fun_camera"}
    s.update({k: v for k, v in comfy.VIDEO_PRESETS["wan21_fun_camera"].items() if k != "label"})
    wf = comfy._video_workflow(s, "un flacon bleu sur marbre", 832, 480, 25, 42, "ref.png", camera_pose="Zoom In")
    classes = {n["class_type"] for n in wf.values()}
    assert "UNETLoader" in classes
    assert "CLIPLoader" in classes
    assert "VAELoader" in classes
    assert "CLIPVisionLoader" in classes
    assert "WanCameraEmbedding" in classes
    assert "WanCameraImageToVideo" in classes
    assert "VAEDecode" in classes
    assert "CreateVideo" in classes
    assert "SaveVideo" in classes
    # WanCameraImageToVideo must receive camera_conditions and clip_vision_output
    i2v = next(n for n in wf.values() if n["class_type"] == "WanCameraImageToVideo")
    assert i2v["inputs"]["camera_conditions"] == ["8", 0]
    assert i2v["inputs"]["clip_vision_output"] == ["10", 0]
    assert i2v["inputs"]["start_image"] == ["9", 0]
    assert i2v["inputs"]["width"] == 832
    assert i2v["inputs"]["height"] == 480
    assert i2v["inputs"]["length"] == 25
    # WanCameraEmbedding receives the camera pose
    cam = next(n for n in wf.values() if n["class_type"] == "WanCameraEmbedding")
    assert cam["inputs"]["camera_pose"] == "Zoom In"
    assert cam["inputs"]["width"] == 832
    assert cam["inputs"]["height"] == 480
    assert cam["inputs"]["length"] == 25
    # KSampler receives the latent from WanCameraImageToVideo
    ksampler = next(n for n in wf.values() if n["class_type"] == "KSampler")
    assert ksampler["inputs"]["latent_image"] == ["11", 2]
    assert ksampler["inputs"]["positive"] == ["11", 0]
    assert ksampler["inputs"]["negative"] == ["11", 1]
    assert ksampler["inputs"]["model"] == ["4", 0]


@pytest.mark.parametrize("video", [False, True])
async def test_custom_workflow_uses_custom_models_not_preset_defaults(monkeypatch, video):
    workflow = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "custom.gguf"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{PROMPT}}", "clip": ["1", 0]}},
    }
    key = "custom_video_workflow" if video else "custom_image_workflow"
    s = {**comfy.DEFAULTS, key: json.dumps(workflow)}
    calls = mock_comfy(monkeypatch, {"UNETLoader": {"unet_name": ["custom.gguf"]}})
    await comfy.verify_ready(s, video)
    assert calls == ["/system_stats", "/object_info/UNETLoader"]
    assert comfy._missing_files(s, {"diffusion_models": []}, video) == ["custom.gguf"]


async def test_custom_multifield_loader_and_optional_models_share_one_request(monkeypatch):
    wf = {
        "1": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "a.safetensors", "clip_name2": "b.safetensors"}},
        "2": {"class_type": "LoraLoader", "inputs": {"lora_name": "detail.safetensors"}},
        "3": {"class_type": "LoraLoader", "inputs": {"lora_name": "detail.safetensors"}},
    }
    calls = mock_comfy(monkeypatch, {
        "DualCLIPLoader": {"clip_name1": ["a.safetensors"], "clip_name2": ["b.safetensors"]},
        "LoraLoader": {"lora_name": ["detail.safetensors"]},
    })
    s = {**comfy.DEFAULTS, "custom_image_workflow": json.dumps(wf)}
    await comfy.verify_ready(s)
    assert calls == ["/system_stats", "/object_info/DualCLIPLoader", "/object_info/LoraLoader"]
    assert comfy._model_requirements(s, False)["LoraLoader.lora_name"][2] == ["detail.safetensors"]


async def test_custom_unknown_loader_is_checked_using_its_own_schema(monkeypatch):
    wf = {"1": {"class_type": "MyVideoLoader", "inputs": {"weights": "custom.gguf"}}}
    calls = mock_comfy(monkeypatch, {"MyVideoLoader": {"weights": ["custom.gguf"]}})
    await comfy.verify_ready({**comfy.DEFAULTS, "custom_video_workflow": json.dumps(wf)}, True)
    assert calls == ["/system_stats", "/object_info/MyVideoLoader"]


@pytest.mark.parametrize("value", ["{{MODEL}}", ["2", 0]])
async def test_dynamic_custom_inputs_do_not_imply_default_models(monkeypatch, value):
    wf = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": value}}}
    calls = mock_comfy(monkeypatch, {})
    await comfy.verify_ready({**comfy.DEFAULTS, "custom_video_workflow": json.dumps(wf)}, True)
    assert calls == ["/system_stats"]


@pytest.mark.parametrize("custom", ["not JSON", "[]", '{"nodes": []}'])
async def test_invalid_custom_workflow_is_explicit_before_any_request(monkeypatch, custom):
    calls = mock_comfy(monkeypatch, {})
    with pytest.raises(comfy.WorkflowError, match="Workflow personnalisé invalide"):
        await comfy.verify_ready({**comfy.DEFAULTS, "custom_image_workflow": custom})
    assert calls == []


@pytest.mark.parametrize("spec", [["STRING"], [123], [["ok.safetensors", 123]], []])
async def test_non_enumerable_or_malformed_schema_never_proves_absence(spec):
    def respond(request):
        return httpx.Response(200, json={"Loader": {"input": {"required": {"name": spec}}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await comfy._choices(client, "http://comfy", "Loader", "name") is None


async def test_optional_loader_field_is_a_valid_model_list():
    def respond(request):
        return httpx.Response(200, json={"Loader": {"input": {"optional": {"name": [["ok.safetensors"]]}}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await comfy._choices(client, "http://comfy", "Loader", "name") == ["ok.safetensors"]


async def test_unavailable_multifield_loader_is_not_requested_twice(monkeypatch):
    calls = mock_comfy(monkeypatch, {})
    wf = {"1": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "a.pt", "clip_name2": "b.pt"}}}
    with pytest.raises(comfy.ModelListUnavailable):
        await comfy.verify_ready({**comfy.DEFAULTS, "custom_image_workflow": json.dumps(wf)})
    assert calls == ["/system_stats", "/object_info/DualCLIPLoader"]


@pytest.fixture
async def hero(monkeypatch):
    from lib import pipeline

    db = MagicMock()
    db.media.update_one = AsyncMock()
    monkeypatch.setattr(pipeline, "db", db)
    monkeypatch.setattr(pipeline, "create_media", AsyncMock(return_value={"id": "hero1"}))
    monkeypatch.setattr(pipeline, "finish_media", AsyncMock())
    monkeypatch.setattr(pipeline, "_step", AsyncMock())
    monkeypatch.setattr(comfy, "get_settings", AsyncMock(return_value=dict(comfy.DEFAULTS)))
    monkeypatch.setattr(comfy, "verify_ready", AsyncMock())
    monkeypatch.setattr(comfy, "reachable", AsyncMock(side_effect=AssertionError("redundant reachability request")))
    monkeypatch.setattr(comfy, "generate_video", AsyncMock(return_value=(b"video", "video/mp4")))
    return pipeline


async def test_hero_has_one_preflight_and_preserves_generation_arguments(hero):
    result = await hero._hero_video("project1", {}, {"image_briefs": [{"prompt": "forest"}]}, (b"image", "image/png"))
    assert result["slot"] == "hero_video"
    comfy.verify_ready.assert_awaited_once_with(comfy.DEFAULTS, video=True)
    comfy.reachable.assert_not_awaited()
    args = comfy.generate_video.await_args.args
    assert args[1:4] == ("3", "16:9", (b"image", "image/png"))
    assert "slow camera push-in" in args[0]  # Existing hero prompt is not changed in V1-D.
    hero.finish_media.assert_awaited_once_with("hero1", b"video", "video/mp4")


async def test_hero_list_discovery_failure_warns_but_preserves_working_generation(hero, caplog):
    comfy.verify_ready.side_effect = comfy.ModelListUnavailable("object_info indisponible")
    result = await hero._hero_video("project1", {}, {}, (b"image", "image/png"))
    assert result is not None
    comfy.verify_ready.assert_awaited_once()
    comfy.generate_video.assert_awaited_once()
    assert "object_info indisponible" in caplog.text
    assert any("sans confirmation" in call.args[-1] for call in hero._step.await_args_list)


@pytest.mark.parametrize("error,label,stage", [
    (comfy.ComfyUnreachable("server down"), "ComfyUI inaccessible", "verify"),
    (comfy.MissingModel("required.pt absent"), "Modèle manquant", "verify"),
    (comfy.WorkflowError("invalid node"), "Workflow incompatible", "render"),
    (comfy.GenerationError("out of memory"), "Échec du rendu local", "render"),
])
async def test_optional_hero_failure_records_explicit_diagnostic_without_stopping_site(hero, error, label, stage):
    if stage == "verify":
        comfy.verify_ready.side_effect = error
    else:
        comfy.generate_video.side_effect = error
    assert await hero._hero_video("project1", {}, {}, (b"image", "image/png")) is None
    fields = hero.db.media.update_one.await_args.args[1]["$set"]
    assert fields["status"] == "error"
    assert fields["error"] == str(error)
    assert fields["progress_label"] == label
    assert "ignorée" in hero._step.await_args.args[-1]
    hero.finish_media.assert_not_awaited()
    comfy.verify_ready.assert_awaited_once()
    if stage == "verify":
        comfy.generate_video.assert_not_awaited()
