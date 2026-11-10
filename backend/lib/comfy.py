"""Local, free image & video generation through a ComfyUI server (FLUX / SDXL images, Wan 2.2 / LTX-Video videos).

Built-in workflows use ComfyUI core nodes. Users may also paste their own workflow exported with
"Export (API)" and use the placeholders {{PROMPT}} {{NEGATIVE}} {{WIDTH}} {{HEIGHT}} {{SEED}} {{LENGTH}} {{IMAGE}}.
"""
import asyncio
import json
import logging
import random
import re
import time
import uuid
from typing import Any, Awaitable, Callable, Optional

import httpx

from lib.db import db

_log = logging.getLogger("localaistudio.comfy")

IMAGE_PRESETS = {
    "flux-dev": {"label": "FLUX.1 dev (fp8)", "checkpoint": "flux1-dev-fp8.safetensors"},
    "flux-schnell": {"label": "FLUX.1 schnell (fp8, rapide)", "checkpoint": "flux1-schnell-fp8.safetensors"},
    "sdxl": {"label": "SDXL", "checkpoint": "sd_xl_base_1.0.safetensors"},
}
# Presets vidéo basés sur UNETLoader (modèle dans diffusion_models/, pas CheckpointLoaderSimple).
UNET_BASED_VIDEO_PRESETS = {"wan22", "wan21_fun_camera"}

VIDEO_PRESETS = {
    "wan22": {"label": "Wan 2.2 TI2V 5B", "model": "wan2.2_ti2v_5B_fp16.safetensors", "text_encoder": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae": "wan2.2_vae.safetensors"},
    "wan21_fun_camera": {"label": "Wan 2.1 Fun Camera 1.3B (RTX 3060 12 Go)", "model": "wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors", "text_encoder": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae": "wan_2.1_vae.safetensors"},
    "ltxv": {"label": "LTX-Video 2B", "model": "ltx-video-2b-v0.9.5.safetensors", "text_encoder": "t5xxl_fp16.safetensors", "vae": ""},
}
DEFAULTS = {
    "base_url": "http://127.0.0.1:8188",
    "image_preset": "flux-dev",
    "image_checkpoint": IMAGE_PRESETS["flux-dev"]["checkpoint"],
    "video_preset": "wan22",
    "video_model": VIDEO_PRESETS["wan22"]["model"],
    "video_text_encoder": VIDEO_PRESETS["wan22"]["text_encoder"],
    "video_vae": VIDEO_PRESETS["wan22"]["vae"],
    "custom_image_workflow": "",
    "custom_video_workflow": "",
}
IMAGE_SIZES = {"1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344), "4:5": (896, 1120)}
VIDEO_SIZES = {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)}
VIDEO_LENGTHS = {"3": 73, "5": 121}  # 24 fps, valid for both Wan (4n+1) and LTX (8n+1)
WAN_CAMERA_POSES = ("Static", "Pan Up", "Pan Down", "Pan Left", "Pan Right", "Zoom In", "Zoom Out", "Anti Clockwise (ACW)", "ClockWise (CW)")
NEGATIVE = "blurry, low quality, deformed, watermark, text, logo, jpeg artifacts, oversaturated"

Progress = Optional[Callable[[str], Awaitable[None]]]
MetricsCallback = Optional[Callable[[dict[str, Any]], Awaitable[None]]]


async def _gpu_memory_sampler(live: dict[str, Any], stop: asyncio.Event) -> None:
    """Best-effort global GPU memory sampling via nvidia-smi; values are not process-specific."""
    while not stop.is_set():
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=4)
            line = out.decode("ascii", errors="ignore").splitlines()[0]
            used, total = (int(v.strip().split()[0]) for v in line.split(",", 1))
            if live.get("vram_baseline_mib") is None:
                live["vram_baseline_mib"] = used
            previous_peak = live.get("vram_peak_mib")
            live["vram_peak_mib"] = used if previous_peak is None else max(used, previous_peak)
            live["vram_total_mib"] = total
        except (FileNotFoundError, IndexError, ValueError, OSError, asyncio.TimeoutError):
            if live.get("vram_peak_mib") is None:
                live["vram_unavailable"] = True
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.75)
        except asyncio.TimeoutError:
            pass


def _record_video_ws_event(msg: Any, pid: str, live: dict[str, Any], workflow: dict, now: float) -> None:
    if not isinstance(msg, dict) or not isinstance(msg.get("data"), dict):
        return
    data = msg["data"]
    if data.get("prompt_id", pid) != pid:
        return
    node_classes = {str(k): n.get("class_type") for k, n in workflow.items() if isinstance(n, dict)}
    event = msg.get("type")
    if event == "execution_start":
        live.setdefault("execution_started", now)
    elif event == "progress":
        value, maximum = data.get("value"), data.get("max")
        if isinstance(value, int) and isinstance(maximum, int) and maximum > 0:
            live.setdefault("first_step_at", now)
            live["last_step_at"] = now
            live["first_step_value"] = live.get("first_step_value", value)
            live["last_step_value"] = value
            live["step_total"] = maximum
    elif event == "executing":
        node = str(data.get("node") or "")
        if node_classes.get(node) == "SaveVideo":
            live["video_encode_started"] = now
    elif event == "executed":
        node = str(data.get("node") or "")
        kind = node_classes.get(node)
        if kind in ("KSampler", "SamplerCustom"):
            live["sampler_finished"] = now
        if kind == "SaveVideo":
            live["video_encode_finished"] = now
    elif event == "execution_success":
        live["execution_finished"] = now


def _video_frame_count(duration: str) -> int:
    """Map the UI/API duration to the exact frame count required by each video latent workflow."""
    value = str(duration).strip().lower()
    if value.endswith("s"):
        value = value[:-1].strip()
    if value not in VIDEO_LENGTHS:
        raise WorkflowError(f"Durée vidéo non prise en charge : {duration}. Choisissez 3 ou 5 secondes.")
    return VIDEO_LENGTHS[value]


def _video_metrics(live: dict[str, Any], started: float, finished: float, context: dict[str, Any]) -> dict[str, Any]:
    def span(a: str, b: str) -> Optional[float]:
        return round(max(0.0, live[b] - live[a]), 3) if a in live and b in live else None

    first_value, last_value = live.get("first_step_value"), live.get("last_step_value")
    steps = (last_value - first_value + 1) if isinstance(first_value, int) and isinstance(last_value, int) else None
    sampling = span("first_step_at", "last_step_at")
    baseline, peak = live.get("vram_baseline_mib"), live.get("vram_peak_mib")
    return {
        **context,
        "timing_seconds": {
            "comfy_total": round(finished - started, 3),
            "execution_total": span("execution_started", "execution_finished"),
            "setup_before_first_step_includes_model_loading": span("execution_started", "first_step_at"),
            "sampling_interval": sampling,
            "steps_observed": steps,
            "mean_seconds_per_observed_step": round(sampling / max(steps - 1, 1), 3) if sampling is not None and steps else None,
            "post_sampler_before_encode": span("sampler_finished", "video_encode_started"),
            "post_last_step_before_encode_includes_decode": span("last_step_at", "video_encode_started"),
            "video_encode_node": span("video_encode_started", "video_encode_finished"),
        },
        "gpu_memory_mib": {
            "sampling_scope": "whole GPU; nvidia-smi",
            "baseline_used": baseline,
            "peak_used": peak,
            "peak_delta": max(0, peak - baseline) if peak is not None and baseline is not None else None,
            "total": live.get("vram_total_mib"),
        },
        "measurement_note": "ComfyUI websocket timings; pre-step setup includes model loading and other nodes. GPU VRAM is system-wide, sampled every ~0.75s.",
    }


class ComfyError(RuntimeError):
    """Base error for any ComfyUI failure (kept so existing `except comfy.ComfyError` still catches all)."""


class ComfyUnreachable(ComfyError):
    """ComfyUI server is not running or not reachable."""


class MissingModel(ComfyError):
    """A required model file is absent from ComfyUI's models folder."""


class ModelListUnavailable(ComfyError):
    """ComfyUI is reachable but the model list endpoint failed — cannot confirm presence or absence of models.

    V1-C: distinguishes 'model absent' (MissingModel) from 'list unavailable' (this class).
    A generation is *not* blocked on this error alone; callers may retry or proceed with a warning.
    """


class WorkflowError(ComfyError):
    """ComfyUI rejected the workflow (incompatible nodes, invalid custom JSON)."""


class GenerationError(ComfyError):
    """ComfyUI accepted the workflow but execution failed (OOM, timeout, no output)."""


async def get_settings() -> dict:
    doc = await db.settings.find_one({"id": "comfyui"}, {"_id": 0, "id": 0}) or {}
    return {**DEFAULTS, **doc}


async def save_settings(data: dict) -> dict:
    for key in ("custom_image_workflow", "custom_video_workflow"):
        if data.get(key, "").strip():
            try:
                json.loads(data[key])
            except ValueError as exc:
                raise WorkflowError(f"Workflow personnalisé invalide (JSON attendu, export « API » de ComfyUI) : {exc}") from exc
    data = {**data, "base_url": data["base_url"].rstrip("/")}
    await db.settings.update_one({"id": "comfyui"}, {"$set": data}, upsert=True)
    return await get_settings()


def unreachable(s: dict) -> str:
    return (
        f"ComfyUI injoignable à {s['base_url']}. Lancez ComfyUI (Desktop ou « python main.py --listen ») sur la machine "
        "qui exécute LocalAiStudio, puis réessayez."
    )


def _client(timeout: float = 30) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5))


async def _choices(
    c: httpx.AsyncClient, base: str, node: str, field: str,
    cache: Optional[dict[str, Any]] = None,
) -> Optional[list[str]]:
    """Return a verified combo list, [] if empty, or None if it cannot be verified.

    A STRING socket is not a model list. Cache object_info per node for loaders with
    several model fields (e.g. DualCLIPLoader); failed requests are cached too.
    """
    cache = cache if cache is not None else {}
    if node not in cache:
        try:
            r = await c.get(f"{base}/object_info/{node}")
            r.raise_for_status()
            cache[node] = r.json()
        except Exception:
            cache[node] = None
    try:
        inputs = cache[node][node]["input"]
        spec = inputs.get("required", {}).get(field) or inputs.get("optional", {}).get(field)
        choices = spec[0]
        if isinstance(choices, list) and all(isinstance(v, str) for v in choices):
            return list(choices)
    except (KeyError, TypeError, IndexError, AttributeError):
        pass
    return None


async def reachable() -> bool:
    s = await get_settings()
    try:
        async with _client(4) as c:
            return (await c.get(f"{s['base_url']}/system_stats")).status_code == 200
    except Exception:
        return False


async def test(s: dict) -> dict:
    base = s["base_url"].rstrip("/")
    try:
        async with _client(8) as c:
            r = await c.get(f"{base}/system_stats")
            r.raise_for_status()
            dev = (r.json().get("devices") or [{}])[0]
            ckpts = await _choices(c, base, "CheckpointLoaderSimple", "ckpt_name")
            unets = await _choices(c, base, "UNETLoader", "unet_name")
            clips = await _choices(c, base, "CLIPLoader", "clip_name")
    except Exception:
        return {"ok": False, "message": unreachable(s), "gpu": "", "checkpoints": [], "diffusion_models": [], "text_encoders": []}
    # V1-C: _choices returns None when the list endpoint failed; treat as unavailable (not empty).
    lists_unavailable = ckpts is None or unets is None or clips is None
    ckpts_safe = ckpts or []
    unets_safe = unets or []
    clips_safe = clips or []
    gpu = f"{dev.get('name', 'GPU')} · {round((dev.get('vram_total') or 0) / 1024**3, 1)} Go VRAM"
    if lists_unavailable:
        msg = (
            f"ComfyUI joignable ({gpu}) mais la liste des modèles est inaccessible "
            "(endpoint object_info indisponible). La génération peut fonctionner si les modèles sont installés."
        )
        return {"ok": True, "message": msg, "gpu": gpu, "checkpoints": ckpts_safe, "diffusion_models": unets_safe, "text_encoders": clips_safe}
    missing = [f for f in (s["image_checkpoint"],) if f not in ckpts_safe]
    vid_needed = [s["video_model"], s["video_text_encoder"]]
    vid_have = (unets_safe if s["video_preset"] in UNET_BASED_VIDEO_PRESETS else ckpts_safe) + clips_safe
    missing += [f for f in vid_needed if f and f not in vid_have]
    msg = f"ComfyUI prêt ({gpu})" if not missing else f"ComfyUI joignable ({gpu}), fichiers manquants : {', '.join(missing)}"
    return {"ok": not missing, "message": msg, "gpu": gpu, "checkpoints": ckpts_safe, "diffusion_models": unets_safe, "text_encoders": clips_safe}


# ------------------------------------------------------------------ pre-flight model verification

# File extensions ComfyUI accepts as model weights — used to recognise a missing-file error.
_MISSING_FILE_RE = re.compile(r"\.(safetensors|ckpt|pt|bin|gguf|pth|sftensors)\b", re.I)


# Standard categories retain their historical keys for diagnostics and callers.
_MODEL_LIST_FIELDS = {
    ("CheckpointLoaderSimple", "ckpt_name"): "checkpoints",
    ("UNETLoader", "unet_name"): "diffusion_models",
    ("CLIPLoader", "clip_name"): "text_encoders",
    ("VAELoader", "vae_name"): "vae",
}
_MODEL_FIELDS = {
    "ckpt_name", "unet_name", "clip_name", "clip_name1", "clip_name2", "clip_name3",
    "vae_name", "lora_name", "control_net_name", "style_model_name", "upscale_model_name",
}
ModelRequirements = dict[str, tuple[str, str, list[str]]]


def _model_requirements(s: dict, video: bool) -> ModelRequirements:
    """Only concrete model files used by the selected workflow, never inactive defaults.

    Custom API graphs can use other loaders: inspect their literal model inputs using
    their own object_info schema. Linked/dynamic/opaque inputs remain ComfyUI's job;
    they must never be diagnosed as absent using an unrelated preset's lists.
    """
    custom = s.get("custom_video_workflow" if video else "custom_image_workflow", "").strip()
    if custom:
        try:
            workflow = json.loads(custom)
        except ValueError as exc:
            raise WorkflowError(f"Workflow personnalisé invalide (JSON API attendu) : {exc}") from exc
        if not isinstance(workflow, dict) or not all(
            isinstance(node, dict) and isinstance(node.get("class_type"), str)
            and isinstance(node.get("inputs"), dict) for node in workflow.values()
        ):
            raise WorkflowError("Workflow personnalisé invalide : export API de ComfyUI attendu.")
    elif not video:
        workflow = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": s["image_checkpoint"]}}}
    else:
        node, field = ("UNETLoader", "unet_name") if s["video_preset"] in UNET_BASED_VIDEO_PRESETS else ("CheckpointLoaderSimple", "ckpt_name")
        workflow = {
            "1": {"class_type": node, "inputs": {field: s["video_model"]}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"]}},
        }
        # LTX uses the checkpoint's VAE, even if settings contain a stale external VAE.
        # Wan 2.2 and Wan 2.1 Fun Camera use an external VAE.
        if s["video_preset"] in UNET_BASED_VIDEO_PRESETS:
            workflow["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": s.get("video_vae", "")}}
        if s["video_preset"] == "wan21_fun_camera":
            # This I2V graph also requires the vision encoder; checking only UNET/UMT5/VAE
            # lets preflight pass and then fail after occupying the GPU queue.
            workflow["4"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}}
    required: ModelRequirements = {}
    for node in workflow.values():
        loader = node["class_type"]
        for field, value in node["inputs"].items():
            if not isinstance(value, str) or not value or "{{" in value or value.lower() == "none":
                continue
            model_field = field in _MODEL_FIELDS
            loader_file = "loader" in loader.lower() and bool(re.search(r"\.(?:safetensors|ckpt|pt|bin|gguf|pth|sftensors)$", value, re.I))
            if not (model_field or loader_file):
                continue
            key = _MODEL_LIST_FIELDS.get((loader, field), f"{loader}.{field}")
            files = required.setdefault(key, (loader, field, []))[2]
            if value not in files:
                files.append(value)
    return required


async def _model_lists(
    c: httpx.AsyncClient, base: str, required: Optional[ModelRequirements] = None,
) -> dict[str, Optional[list[str]]]:
    """Fetch only the needed lists, once per loader node, with no cross-render cache."""
    if required is None:  # compatibility for callers requesting the complete catalogue
        required = {key: (node, field, []) for (node, field), key in _MODEL_LIST_FIELDS.items()}
    cache: dict[str, Any] = {}
    return {
        key: await _choices(c, base, node, field, cache)
        for key, (node, field, _) in required.items()
    }


def _missing_files(s: dict, lists: dict[str, Optional[list[str]]], video: bool) -> list[str]:
    """Confirmed absences only: an unavailable or non-enumerable list proves nothing."""
    return list(dict.fromkeys(
        filename
        for key, (_, _, files) in _model_requirements(s, video).items()
        if lists.get(key) is not None
        for filename in files if filename not in lists[key]
    ))


def _lists_unavailable(lists: dict[str, Optional[list[str]]], video: bool, s: dict) -> list[str]:
    """Only unavailable lists required by this preset/custom workflow, not other engines."""
    return [key for key in _model_requirements(s, video) if lists.get(key) is None]


def _is_missing_model_error(detail: Any, hint: str) -> bool:
    """True when a workflow-rejection error clearly points at an absent model file (not a malformed graph)."""
    blob = f"{detail} {hint}".lower()
    return "not in list" in blob or "file not found" in blob or "no such file" in blob or bool(_MISSING_FILE_RE.search(f"{detail} {hint}"))


async def verify_ready(s: dict, video: bool = False) -> None:
    """Pre-flight check: ComfyUI must be reachable AND every required model file must be present.

    Raises:
        ComfyUnreachable      — ComfyUI server is not running or not reachable.
        ModelListUnavailable  — ComfyUI is reachable but the model list endpoint failed.
                                Cannot confirm presence or absence; the caller may still
                                proceed if it trusts that models are installed.
        MissingModel          — A required model file is confirmed absent from ComfyUI.

    V1-C: distinguishes the three failure modes so callers can give precise diagnostics.
    Never downloads or deletes anything.
    """
    base = s["base_url"].rstrip("/")
    required = _model_requirements(s, video)
    try:
        async with _client(8) as c:
            r = await c.get(f"{base}/system_stats")
            r.raise_for_status()
            lists = await _model_lists(c, base, required)
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise ComfyUnreachable(unreachable(s)) from exc

    # A confirmed missing file remains an explicit error, even if another list failed.
    missing = _missing_files(s, lists, video)
    if missing:
        pool = list(dict.fromkeys(name for values in lists.values() for name in (values or [])))
        avail = f" Modèles présents : {', '.join(pool[:5])}." if pool else ""
        raise MissingModel(
            f"Modèle(s) ComfyUI manquant(s) : {', '.join(missing)}.{avail} "
            "Lancez download-models.ps1 puis redémarrez ComfyUI, ou choisissez un modèle présent dans Moteurs → Configurer."
        )

    unavailable = _lists_unavailable(lists, video, s)
    if unavailable:
        raise ModelListUnavailable(
            f"ComfyUI est joignable mais la liste des modèles est inaccessible "
            f"(endpoint object_info indisponible pour : {', '.join(unavailable)}). "
            "Impossible de confirmer la présence des modèles. "
            "Vérifiez que ComfyUI a terminé son démarrage, puis réessayez."
        )


# ------------------------------------------------------------------ workflows (ComfyUI API format)

def _image_workflow(s: dict, prompt: str, w: int, h: int, seed: int, image: Optional[str]) -> dict:
    flux = s["image_preset"].startswith("flux")
    schnell = s["image_preset"] == "flux-schnell"
    wf: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": s["image_checkpoint"]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "" if flux else NEGATIVE, "clip": ["1", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "LocalAiStudio", "images": ["8", 0]}},
    }
    positive: list = ["2", 0]
    if flux and not schnell:
        wf["4"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": ["2", 0], "guidance": 3.5}}
        positive = ["4", 0]
    if image:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        wf["11"] = {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 1}}
        wf["6"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["11", 0], "vae": ["1", 2]}}
        denoise = 0.62
    else:
        wf["6"] = {"class_type": "EmptySD3LatentImage" if flux else "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
        denoise = 1.0
    steps, cfg, sampler, sched = (4, 1.0, "euler", "simple") if schnell else (22, 1.0, "euler", "simple") if flux else (30, 6.5, "dpmpp_2m", "karras")
    wf["5"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": positive, "negative": ["3", 0], "latent_image": ["6", 0], "seed": seed,
        "steps": steps, "cfg": cfg, "sampler_name": sampler, "scheduler": sched, "denoise": denoise}}
    return wf


def _video_workflow(s: dict, prompt: str, w: int, h: int, length: int, seed: int, image: Optional[str], camera_pose: str = "Static") -> dict:
    """Build the ComfyUI workflow for the selected video preset.

    Raises WorkflowError when the preset is unknown or unsupported — an
    unsupported preset is never silently routed to an incompatible engine.
    """
    preset = s["video_preset"]
    if preset not in VIDEO_PRESETS:
        raise WorkflowError(
            f"Préset vidéo inconnu ou non pris en charge : {preset}. "
            f"Choisissez parmi : {', '.join(sorted(VIDEO_PRESETS))}."
        )
    neg = "static, blurry, low quality, distorted, watermark, text, jitter, deformed"
    save = {
        "20": {"class_type": "CreateVideo", "inputs": {"images": ["8", 0], "fps": 24}},
        "21": {"class_type": "SaveVideo", "inputs": {"video": ["20", 0], "filename_prefix": "LocalAiStudio/video", "format": "mp4", "codec": "h264"}},
    }
    if preset == "wan22":
        wf: dict[str, Any] = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": s["video_model"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"], "type": "wan", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": s["video_vae"]}},
            "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
            "7": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["3", 0], "width": w, "height": h, "length": length, "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {
                "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "seed": seed,
                "steps": 30, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
            **save,
        }
        if image:
            wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
            wf["7"]["inputs"]["start_image"] = ["10", 0]
        return wf
    if preset == "wan21_fun_camera":
        if camera_pose not in WAN_CAMERA_POSES:
            raise WorkflowError(f"Pose caméra non prise en charge par Wan Fun Camera : {camera_pose}")
        if not image:
            raise WorkflowError(
                "Wan 2.1 Fun Camera est un modèle Image-to-Video : une image de départ est requise. "
                "Sélectionnez une image de référence avant de générer."
            )
        wf = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": s["video_model"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"], "type": "wan", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": s["video_vae"]}},
            "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
            "7": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
            "8": {"class_type": "WanCameraEmbedding", "inputs": {"camera_pose": camera_pose, "width": w, "height": h, "length": length, "speed": 1.0}},
            "9": {"class_type": "LoadImage", "inputs": {"image": image}},
            "10": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["7", 0], "image": ["9", 0], "crop": "center"}},
            "11": {"class_type": "WanCameraImageToVideo", "inputs": {
                "positive": ["5", 0], "negative": ["6", 0], "vae": ["3", 0],
                "width": w, "height": h, "length": length, "batch_size": 1,
                "clip_vision_output": ["10", 0], "start_image": ["9", 0],
                "camera_conditions": ["8", 0]}},
            "12": {"class_type": "KSampler", "inputs": {
                "model": ["4", 0], "positive": ["11", 0], "negative": ["11", 1],
                "latent_image": ["11", 2], "seed": seed,
                "steps": 20, "cfg": 6.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
            "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
            "14": {"class_type": "CreateVideo", "inputs": {"images": ["13", 0], "fps": 24}},
            "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": "LocalAiStudio/video", "format": "mp4", "codec": "h264"}},
        }
        return wf
    # LTX-Video
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": s["video_model"]}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"], "type": "ltxv", "device": "default"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
        "12": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["1", 2]}},
        **save,
    }
    if image:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        wf["7"] = {"class_type": "LTXVImgToVideo", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "vae": ["1", 2], "image": ["10", 0],
            "width": w, "height": h, "length": length, "batch_size": 1, "strength": 1.0}}
        cond_pos, cond_neg, latent = ["7", 0], ["7", 1], ["7", 2]
    else:
        wf["7"] = {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": w, "height": h, "length": length, "batch_size": 1}}
        cond_pos, cond_neg, latent = ["5", 0], ["6", 0], ["7", 0]
    wf["11"] = {"class_type": "LTXVConditioning", "inputs": {"positive": cond_pos, "negative": cond_neg, "frame_rate": 24.0}}
    wf["13"] = {"class_type": "LTXVScheduler", "inputs": {"steps": 30, "max_shift": 2.05, "base_shift": 0.95, "stretch": True, "terminal": 0.1, "latent": latent}}
    wf["14"] = {"class_type": "SamplerCustom", "inputs": {
        "model": ["1", 0], "add_noise": True, "noise_seed": seed, "cfg": 3.0, "positive": ["11", 0], "negative": ["11", 1],
        "sampler": ["12", 0], "sigmas": ["13", 0], "latent_image": latent}}
    return wf


def _fill(node: Any, values: dict[str, Any]) -> Any:
    """Substitute {{PLACEHOLDERS}} in a user workflow; a value that is exactly a placeholder keeps its native type."""
    if isinstance(node, dict):
        return {k: _fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, values) for v in node]
    if isinstance(node, str):
        for k, v in values.items():
            tag = "{{" + k + "}}"
            if node == tag:
                return v
            if tag in node:
                node = node.replace(tag, str(v))
    return node


# ------------------------------------------------------------------ execution

async def _upload(c: httpx.AsyncClient, base: str, data: bytes, mime: str) -> str:
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    r = await c.post(f"{base}/upload/image", files={"image": (f"las_{uuid.uuid4().hex[:10]}.{ext}", data, mime)}, data={"overwrite": "true"})
    r.raise_for_status()
    j = r.json()
    return f"{j['subfolder']}/{j['name']}" if j.get("subfolder") else j["name"]


def _first_file(outputs: dict, video: bool) -> Optional[dict]:
    files = [f for out in outputs.values() for v in out.values() if isinstance(v, list) for f in v if isinstance(f, dict) and f.get("filename")]
    if video:
        vids = [f for f in files if f["filename"].lower().endswith((".mp4", ".webm", ".mov"))]
        return (vids or files or [None])[0]
    return files[0] if files else None


def image_settings(s: dict, preset: Optional[str]) -> dict:
    """Return settings with a per-request image preset applied (None keeps the saved settings)."""
    if not preset:
        return s
    if preset not in IMAGE_PRESETS:
        raise ValueError(f"Preset image inconnu : {preset}")
    return {**s, "image_preset": preset, "image_checkpoint": IMAGE_PRESETS[preset]["checkpoint"]}


async def image_model_status(s: dict) -> list[dict]:
    """Installed state of each image preset: True/False, or None when ComfyUI cannot list its checkpoints."""
    try:
        async with _client(10) as c:
            ckpts = await _choices(c, s["base_url"], "CheckpointLoaderSimple", "ckpt_name", {})
    except Exception:  # noqa: BLE001 — status is informative, it must never break the page
        ckpts = None
    return [
        {
            "key": key,
            "label": v["label"],
            "checkpoint": v["checkpoint"],
            "installed": None if ckpts is None else v["checkpoint"] in ckpts,
        }
        for key, v in IMAGE_PRESETS.items()
    ]


async def video_model_status(s: dict) -> dict:
    """Verified install status for each preset, including secondary encoders such as CLIP Vision."""
    presets = []
    try:
        async with _client(10) as c:
            for key, value in VIDEO_PRESETS.items():
                selected = video_settings({**s, "custom_video_workflow": ""}, key)
                required = _model_requirements(selected, video=True)
                lists = await _model_lists(c, selected["base_url"], required)
                unavailable = _lists_unavailable(lists, True, selected)
                missing = _missing_files(selected, lists, True)
                installed = None if unavailable else not missing
                files = list(dict.fromkeys(f for _, _, names in required.values() for f in names))
                presets.append({"key": key, "label": value["label"], "model": value["model"], "files": files, "installed": installed})
            camera_info = await c.get(f"{s['base_url'].rstrip('/')}/object_info/WanCameraEmbedding")
            camera_info.raise_for_status()
            camera_input = camera_info.json()["WanCameraEmbedding"]["input"]["required"]["camera_pose"]
            camera_poses = camera_input[1].get("options", []) if len(camera_input) > 1 and isinstance(camera_input[1], dict) else []
    except Exception:  # noqa: BLE001 — status is informative, it must never break the page
        if not presets:
            presets = [{"key": key, "label": value["label"], "model": value["model"], "files": [], "installed": None} for key, value in VIDEO_PRESETS.items()]
        camera_poses = []
    return {"presets": presets, "camera_poses": camera_poses}


def progress_from_ws(msg: Any, pid: str, elapsed: int) -> Optional[str]:
    """Turn one ComfyUI websocket message into a user-facing label; None when it is not ours or not a step."""
    if not isinstance(msg, dict) or msg.get("type") != "progress":
        return None
    d = msg.get("data") or {}
    if d.get("prompt_id", pid) != pid:
        return None
    value, total = d.get("value"), d.get("max")
    if not isinstance(value, int) or not isinstance(total, int) or not 0 <= value <= total or total <= 0:
        return None
    return f"Rendu local sur votre GPU · étape {value}/{total} · {elapsed}s"


async def _ws_progress(base: str, client_id: str, pid: str, progress: Progress, started: float, live: dict, workflow: Optional[dict] = None) -> None:
    """Stream ComfyUI step progress. Best effort: any failure leaves the elapsed-time labels in charge."""
    try:
        import websockets  # optional at runtime; only needed for step labels
    except ImportError:
        _log.warning("websockets absent : progression par étapes désactivée (pip install -r requirements.txt)")
        return
    url = re.sub(r"^http", "ws", base) + f"/ws?clientId={client_id}"
    try:
        async with websockets.connect(url, max_size=None, open_timeout=5) as ws:
            async for raw in ws:
                if isinstance(raw, bytes):
                    continue  # binary frames are preview images
                msg = json.loads(raw)
                _record_video_ws_event(msg, pid, live, workflow or {}, time.monotonic())
                label = progress_from_ws(msg, pid, int(time.monotonic() - started))
                if label and progress:
                    live["steps"] = True
                    await progress(label)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        _log.info("ComfyUI websocket progress unavailable: %s", exc)


async def run(
    workflow: dict, video: bool, progress: Progress = None, on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
    s: Optional[dict] = None, on_metrics: MetricsCallback = None, metrics_context: Optional[dict[str, Any]] = None,
) -> tuple[bytes, str]:
    s = s or await get_settings()
    base = s["base_url"]
    started = time.monotonic()
    client_id = uuid.uuid4().hex  # unique per render: ComfyUI routes this client's websocket events
    ws_task: Optional[asyncio.Task] = None
    gpu_task: Optional[asyncio.Task] = None
    gpu_stop = asyncio.Event()
    live: dict[str, Any] = {"steps": False, "vram_peak_mib": None}
    if video:
        gpu_task = asyncio.create_task(_gpu_memory_sampler(live, gpu_stop))
    try:
        async with _client(60) as c:
            r = await c.post(f"{base}/prompt", json={"prompt": workflow, "client_id": client_id})
            if r.status_code >= 400:
                detail = r.json() if "json" in r.headers.get("content-type", "") else r.text
                err = detail.get("error", {}).get("message") if isinstance(detail, dict) else str(detail)
                nodes = detail.get("node_errors") if isinstance(detail, dict) else None
                hint = ""
                if nodes:
                    first = next(iter(nodes.values()))
                    hint = " — " + "; ".join(e.get("details") or e.get("message", "") for e in first.get("errors", [])[:2])
                msg = f"ComfyUI a refusé le workflow : {err}{hint}"[:400]
                if _is_missing_model_error(detail, hint):
                    raise MissingModel(
                        f"Modèle ComfyUI manquant : {msg} Lancez download-models.ps1 puis redémarrez ComfyUI, "
                        "ou choisissez un modèle présent dans Moteurs → Configurer."
                    )
                raise WorkflowError(msg)
            pid = r.json()["prompt_id"]
            if on_queued:
                await on_queued(pid)
            ws_task = asyncio.create_task(_ws_progress(base, client_id, pid, progress, started, live, workflow))
            limit = 3600 if video else 900
            while time.monotonic() - started < limit:
                await asyncio.sleep(2)
                h = (await c.get(f"{base}/history/{pid}")).json().get(pid)
                elapsed = int(time.monotonic() - started)
                if not h:
                    if progress and not live["steps"]:
                        await progress(f"Rendu local sur votre GPU · {elapsed}s")
                    continue
                st = h.get("status", {})
                if st.get("status_str") == "error":
                    msgs = [m[1].get("exception_message", "") for m in st.get("messages", []) if m[0] == "execution_error"]
                    raw = (msgs or ["exécution interrompue"])[0]
                    blob = raw.lower()
                    if any(k in blob for k in ("out of memory", "cuda out of memory", "oom", "vram", "ran out of memory", "could not allocate", "not enough memory")):
                        raise GenerationError(
                            f"VRAM insuffisante pour ce rendu ({raw[:200]}). Réduisez la résolution, choisissez FLUX schnell "
                            "ou SDXL pour les photos, ou LTX-Video pour les vidéos (Moteurs → Configurer)."
                        )
                    raise GenerationError(f"Erreur de génération ComfyUI : {raw}"[:400])
                f = _first_file(h.get("outputs", {}), video)
                if not f:
                    raise GenerationError("ComfyUI n'a produit aucun fichier — le workflow a échoué sans erreur explicite.")
                fr = await c.get(f"{base}/view", params={"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                fr.raise_for_status()
                mime = fr.headers.get("content-type", "video/mp4" if video else "image/png").split(";")[0]
                if video:
                    gpu_stop.set()
                    if gpu_task:
                        await gpu_task
                    metrics_finished = time.monotonic()
                    # WebSocket listeners may connect after ComfyUI has emitted execution_start
                    # (or miss its final event). Keep HTTP wall time usable and label the setup
                    # interval honestly instead of persisting null for an otherwise observed run.
                    live.setdefault("execution_started", started)
                    live.setdefault("execution_finished", metrics_finished)
                    report = _video_metrics(live, started, metrics_finished, metrics_context or {})
                    _log.info("video_generation_metrics %s", json.dumps(report, ensure_ascii=False, sort_keys=True))
                    if on_metrics:
                        try:
                            await on_metrics(report)
                        except Exception as exc:  # metrics must never turn a successful render into a failure
                            _log.warning("Could not persist video metrics: %s", exc)
                return fr.content, mime
            raise GenerationError(
                "Délai de rendu local dépassé — la carte graphique est peut-être trop lente ou a manqué de VRAM. "
                "Réduisez la résolution ou la durée, puis réessayez."
            )
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise ComfyUnreachable(unreachable(s)) from exc
    finally:
        gpu_stop.set()
        if ws_task is not None:
            ws_task.cancel()
        if gpu_task is not None and not gpu_task.done():
            try:
                await gpu_task
            except asyncio.CancelledError:
                pass


async def generate_image(
    prompt: str, aspect: str = "1:1", ref: Optional[tuple[bytes, str]] = None, progress: Progress = None,
    on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
    preset: Optional[str] = None,
) -> tuple[bytes, str]:
    """Generate an image via ComfyUI.

    V1-C: verify_ready() is NOT called here.  All callers go through media.py which calls
    verify_ready() before acquiring the GPU slot.  Calling it twice per generation was redundant
    (5 extra HTTP round-trips: system_stats + 4 × object_info) and could cause a false
    ModelListUnavailable error if object_info became briefly unavailable between the two calls.

    Direct callers that bypass media.py (e.g. tests, CLI tools) must call verify_ready()
    themselves before invoking this function.
    """
    s = image_settings(await get_settings(), preset)
    w, h = IMAGE_SIZES.get(aspect, IMAGE_SIZES["1:1"])
    seed = random.randint(1, 2**31)
    image = None
    if ref:
        try:
            async with _client() as c:
                image = await _upload(c, s["base_url"], *ref)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyUnreachable(unreachable(s)) from exc
    if s["custom_image_workflow"].strip():
        wf = _fill(json.loads(s["custom_image_workflow"]), {"PROMPT": prompt, "NEGATIVE": NEGATIVE, "WIDTH": w, "HEIGHT": h, "SEED": seed, "IMAGE": image or ""})
    else:
        wf = _image_workflow(s, prompt, w, h, seed, image)
    return await run(wf, False, progress, on_queued, s=s)


def video_settings(s: dict, preset: Optional[str]) -> dict:
    """Return settings with a per-request video preset applied (None keeps the saved settings)."""
    if not preset:
        return s
    if preset not in VIDEO_PRESETS:
        raise ValueError(f"Préset vidéo inconnu : {preset}")
    p = VIDEO_PRESETS[preset]
    return {**s, "video_preset": preset, "video_model": p["model"], "video_text_encoder": p["text_encoder"], "video_vae": p["vae"]}


async def generate_video(
    prompt: str, duration: str, aspect: str, ref: Optional[tuple[bytes, str]] = None, progress: Progress = None,
    on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
    camera_pose: str = "Static",
    preset: Optional[str] = None,
    on_metrics: MetricsCallback = None,
) -> tuple[bytes, str]:
    """Generate a video via ComfyUI.

    V1-C/V1-D: verify_ready() is NOT called here. media.py and the LocalAiWeb
    hero-video caller each own their single pre-flight check. See generate_image() for rationale.

    Direct callers that bypass media.py must call verify_ready(s, video=True) themselves.
    """
    s = video_settings(await get_settings(), preset)
    w, h = VIDEO_SIZES.get(aspect, VIDEO_SIZES["16:9"])
    length = _video_frame_count(duration)
    seed = random.randint(1, 2**31)
    image = None
    if ref:
        try:
            async with _client() as c:
                image = await _upload(c, s["base_url"], *ref)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyUnreachable(unreachable(s)) from exc
    if s["custom_video_workflow"].strip():
        wf = _fill(json.loads(s["custom_video_workflow"]), {"PROMPT": prompt, "NEGATIVE": NEGATIVE, "WIDTH": w, "HEIGHT": h, "SEED": seed, "LENGTH": length, "IMAGE": image or ""})
    else:
        wf = _video_workflow(s, prompt, w, h, length, seed, image, camera_pose=camera_pose)
    sampler = next((n.get("inputs", {}) for n in wf.values() if n.get("class_type") in ("KSampler", "SamplerCustom")), {})
    metrics_context = {
        "preset": s["video_preset"], "camera_pose": camera_pose, "seed": seed,
        "width": w, "height": h, "frames": length, "fps": 24,
        "sampler": sampler.get("sampler_name", "custom"), "steps": sampler.get("steps"),
        "cfg": sampler.get("cfg"), "comfy_model": s.get("video_model"),
        "i2v": bool(image),
    }
    return await run(wf, True, progress, on_queued, s=s, on_metrics=on_metrics, metrics_context=metrics_context)


async def cancel(prompt_id: str) -> None:
    s = await get_settings()
    async with _client(8) as c:
        await c.post(f"{s['base_url']}/queue", json={"delete": [prompt_id]})
        await c.post(f"{s['base_url']}/interrupt")
