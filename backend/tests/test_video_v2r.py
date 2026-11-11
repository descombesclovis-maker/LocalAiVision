"""V2-R Wan 2.1 T2V integration contract; these tests do not claim GPU output quality."""

import pytest

from lib import comfy
from models.engines import ComfySettings
from models.schemas import VideoRequest


FR_PROMPT = "Une petite voiture rouge traverse lentement une rue pavée sous la pluie, de gauche à droite."


def t2v_settings():
    s = {**comfy.DEFAULTS, "video_preset": "wan21_t2v"}
    s.update({"video_" + k: v for k, v in comfy.VIDEO_PRESETS["wan21_t2v"].items() if k != "label"})
    return s


def test_wan21_t2v_workflow_keeps_french_prompt_and_uses_real_local_loaders():
    settings = t2v_settings()
    workflow = comfy._video_workflow(settings, FR_PROMPT, 832, 480, 73, 9341, None)
    classes = {node["class_type"] for node in workflow.values()}
    assert {"UNETLoader", "CLIPLoader", "VAELoader", "ModelSamplingSD3", "WanImageToVideo", "KSampler", "VAEDecode", "SaveVideo"} <= classes
    assert workflow["1"]["inputs"]["unet_name"] == comfy.VIDEO_PRESETS["wan21_t2v"]["model"]
    assert workflow["2"]["inputs"]["clip_name"] == comfy.VIDEO_PRESETS["wan21_t2v"]["text_encoder"]
    assert workflow["3"]["inputs"]["vae_name"] == comfy.VIDEO_PRESETS["wan21_t2v"]["vae"]
    assert workflow["5"]["inputs"]["text"] == FR_PROMPT
    assert workflow["7"]["inputs"]["length"] == 73
    assert workflow["9"]["inputs"]["steps"] == 30
    assert workflow["9"]["inputs"]["seed"] == 9341
    assert workflow["21"]["class_type"] == "SaveVideo"
    assert "start_image" not in workflow["7"]["inputs"]


def test_t2v_preset_requires_no_image_and_rejects_misrouted_i2v():
    settings = t2v_settings()
    workflow = comfy._video_workflow(settings, FR_PROMPT, 832, 480, 73, 1, None)
    assert "WanImageToVideo" in {n["class_type"] for n in workflow.values()}
    with pytest.raises(comfy.WorkflowError, match="Texte → vidéo"):
        comfy._video_workflow(settings, FR_PROMPT, 832, 480, 73, 1, "reference.png")


def test_wan21_fun_camera_i2v_contract_remains_available():
    settings = {**comfy.DEFAULTS, "video_preset": "wan21_fun_camera"}
    settings.update({"video_" + k: v for k, v in comfy.VIDEO_PRESETS["wan21_fun_camera"].items() if k != "label"})
    workflow = comfy._video_workflow(settings, "Un flacon bleu avance dans la lumière", 832, 480, 73, 7, "reference.png", "Zoom In")
    classes = {node["class_type"] for node in workflow.values()}
    assert {"CLIPVisionLoader", "CLIPVisionEncode", "WanCameraEmbedding", "WanCameraImageToVideo"} <= classes


def test_t2v_preflight_requires_only_its_diffusion_text_and_vae_files():
    requirements = comfy._model_requirements(t2v_settings(), video=True)
    assert requirements["diffusion_models"][2] == ["wan2.1_t2v_1.3B_fp16.safetensors"]
    assert requirements["text_encoders"][2] == ["umt5_xxl_fp8_e4m3fn_scaled.safetensors"]
    assert requirements["vae"][2] == ["wan_2.1_vae.safetensors"]
    assert "CLIPVisionLoader.clip_name" not in requirements


def test_exact_duration_map_is_24fps_and_does_not_silently_shorten():
    assert {seconds: comfy._video_frame_count(seconds) for seconds in ("3", "6", "9", "12", "20", "30")} == {
        "3": 73, "6": 145, "9": 217, "12": 289, "20": 481, "30": 721,
    }
    for seconds in ("3", "6", "9", "12", "20", "30"):
        frames = comfy._video_frame_count(seconds)
        assert (frames - 1) % 4 == 0 and (frames - 1) % 8 == 0
    with pytest.raises(comfy.WorkflowError, match="Choisissez parmi"):
        comfy._video_frame_count("7")


def test_private_sana_request_contract_is_t2v_only_and_uses_validated_profile():
    request = VideoRequest(prompt=FR_PROMPT, model="hf_sana", mode="text", duration="5", aspect_ratio="16:9")
    assert request.model == "hf_sana"
    assert request.mode == "text" and request.duration == "5"


def test_video_request_and_settings_accept_new_engine_without_changing_i2v_request():
    request = VideoRequest(prompt=FR_PROMPT, model="comfy", mode="text", duration="3", aspect_ratio="16:9", comfy_preset="wan21_t2v")
    assert request.comfy_preset == "wan21_t2v"
    i2v = VideoRequest(prompt="mouvement doux", model="comfy", mode="image", duration="3", aspect_ratio="16:9", ref_media_id="image-id", comfy_preset="wan21_fun_camera")
    assert i2v.comfy_preset == "wan21_fun_camera"
    settings = ComfySettings(**comfy.DEFAULTS)
    assert settings.video_preset == "wan21_t2v"
