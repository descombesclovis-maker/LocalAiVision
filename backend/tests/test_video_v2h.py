"""V2-H video UI and diagnostics regression tests (no GPU or ComfyUI required)."""
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from lib import comfy
from models.schemas import VideoRequest


def wan21_settings():
    s = {**comfy.DEFAULTS, "video_preset": "wan21_fun_camera"}
    s.update({"video_" + k: v for k, v in comfy.VIDEO_PRESETS["wan21_fun_camera"].items() if k != "label"})
    return s


def test_wan21_preflight_includes_clip_vision_checkpoint():
    req = comfy._model_requirements(wan21_settings(), video=True)
    assert req["diffusion_models"][2] == ["wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors"]
    assert req["text_encoders"][2] == ["umt5_xxl_fp8_e4m3fn_scaled.safetensors"]
    assert req["vae"][2] == ["wan_2.1_vae.safetensors"]
    assert req["CLIPVisionLoader.clip_name"][2] == ["clip_vision_h.safetensors"]


@pytest.mark.asyncio
async def test_wan21_missing_clip_vision_fails_preflight_before_render(monkeypatch):
    settings = wan21_settings()

    def respond(req):
        node = req.url.path.rsplit("/", 1)[-1]
        if req.url.path == "/system_stats":
            return httpx.Response(200, json={"devices": []})
        choices = {
            "UNETLoader": {"unet_name": [settings["video_model"]]},
            "CLIPLoader": {"clip_name": [settings["video_text_encoder"]]},
            "VAELoader": {"vae_name": [settings["video_vae"]]},
            "CLIPVisionLoader": {"clip_name": ["other_vision.safetensors"]},
        }.get(node, {})
        return httpx.Response(200, json={node: {"input": {"required": {k: [v] for k, v in choices.items()}}}})

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    with pytest.raises(comfy.MissingModel, match="clip_vision_h.safetensors"):
        await comfy.verify_ready(settings, video=True)


def test_video_request_carries_preset_camera_and_ref_mode():
    body = VideoRequest(
        prompt="Animate a glass perfume bottle", model="comfy", mode="image", duration="3",
        ref_media_id="source-image-id", comfy_preset="wan21_fun_camera", camera_pose="Zoom In",
    )
    assert body.comfy_preset == "wan21_fun_camera"
    assert body.camera_pose == "Zoom In"
    with pytest.raises(ValidationError):
        VideoRequest(prompt="a valid prompt", camera_pose="Dolly Through Wall")


def test_wan_camera_workflow_rejects_unsupported_camera_pose():
    with pytest.raises(comfy.WorkflowError, match="Pose caméra"):
        comfy._video_workflow(wan21_settings(), "prompt", 832, 480, 73, 1, "reference.png", camera_pose="Tilt 45")


def test_video_metrics_report_sampling_encode_and_gpu_scopes():
    live = {
        "execution_started": 10.0, "first_step_at": 12.0, "last_step_at": 32.0,
        "first_step_value": 1, "last_step_value": 20, "step_total": 20,
        "sampler_finished": 33.0, "video_encode_started": 34.0,
        "video_encode_finished": 36.0, "execution_finished": 36.5,
        "vram_baseline_mib": 3400, "vram_peak_mib": 10100, "vram_total_mib": 12288,
    }
    report = comfy._video_metrics(live, 8.0, 37.0, {"preset": "wan21_fun_camera", "width": 832, "height": 480, "fps": 24, "frames": 73})
    assert report["timing_seconds"]["comfy_total"] == 29.0
    assert report["timing_seconds"]["setup_before_first_step_includes_model_loading"] == 2.0
    assert report["timing_seconds"]["sampling_interval"] == 20.0
    assert report["timing_seconds"]["steps_observed"] == 20
    assert report["timing_seconds"]["video_encode_node"] == 2.0
    assert report["timing_seconds"]["post_last_step_before_encode_includes_decode"] == 2.0
    assert report["gpu_memory_mib"]["peak_delta"] == 6700
    assert report["width"] == 832 and report["frames"] == 73
    assert "whole GPU" in report["gpu_memory_mib"]["sampling_scope"]


def test_video_metrics_report_wall_clock_fallback_for_missed_ws_start():
    report = comfy._video_metrics(
        {"execution_started": 10.0, "execution_finished": 37.0, "first_step_at": 12.0,
         "last_step_at": 32.0, "first_step_value": 1, "last_step_value": 20,
         "video_encode_started": 34.0, "video_encode_finished": 36.0},
        10.0, 37.0, {},
    )
    assert report["timing_seconds"]["execution_total"] == 27.0
    assert report["timing_seconds"]["setup_before_first_step_includes_model_loading"] == 2.0


@pytest.mark.parametrize(("duration", "frames"), [("3", 73), ("3s", 73), ("5", 121), ("5s", 121)])
def test_video_duration_maps_to_exact_valid_frame_count(duration, frames):
    assert comfy._video_frame_count(duration) == frames


def test_unknown_video_duration_is_rejected_instead_of_silently_becoming_three_seconds():
    with pytest.raises(comfy.WorkflowError, match="Durée vidéo non prise en charge"):
        comfy._video_frame_count("7")


@pytest.mark.asyncio
async def test_gpu_sampler_handles_initial_none_peak_and_records_peak(monkeypatch):
    stop = __import__("asyncio").Event()

    class FakeProcess:
        async def communicate(self):
            stop.set()
            return b"3890, 12288\n", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        assert args[0] == "nvidia-smi"
        return FakeProcess()

    monkeypatch.setattr(comfy.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    live = {"vram_peak_mib": None}
    await comfy._gpu_memory_sampler(live, stop)
    assert live["vram_baseline_mib"] == 3890
    assert live["vram_peak_mib"] == 3890
    assert live["vram_total_mib"] == 12288


def test_video_studio_sends_selected_preset_camera_and_enforces_i2v():
    src = Path(__file__).parents[2].joinpath("frontend/src/components/vision.tsx").read_text(encoding="utf-8")
    assert 'comfy_preset: model === "comfy" ? comfyPreset : null' in src
    assert 'camera_pose: model === "comfy" ? cameraPose : "Static"' in src
    assert 'const needsImage = model === "comfy" && comfyPreset === "wan21_fun_camera"' in src
    assert '|| comfyUnavailable}' in src
    assert 'video-comfy-preset' in src and 'video-camera-pose' in src
    assert 'const [duration, setDuration] = useState("3")' in src
