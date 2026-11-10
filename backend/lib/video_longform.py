"""Experimental, resumable Wan I2V chaining prototype. Not wired into production routes/defaults."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

FPS = 24
SEGMENT_SECONDS = 3
FRAMES_PER_SEGMENT = 73  # Wan constraint: 4n + 1; (73 - 1) / 24 = 3 seconds.
DEFAULT_PROMPT = (
    "A single continuous premium studio product shot of the exact same cobalt-blue glass perfume bottle, "
    "with its gold cap resting separately to the right, on white marble. Preserve the bottle silhouette, "
    "cobalt color, gold cap, marble surface, reflections and studio lighting throughout. The camera makes "
    "a slow, smooth pan left; no cuts, no new objects, no labels, no text."
)


@dataclass(frozen=True)
class SegmentSpec:
    index: int
    start_frame: int
    frame_count: int
    unique_frames: int
    seed: int


@dataclass(frozen=True)
class SubjectObservation:
    hue: int
    bbox: tuple[float, float, float, float]
    center_x: float
    center_y: float
    pixels: int


CAMERA_STRATEGIES = ("legacy", "neutral", "bounded", "keyframe")
ATTENTION_BACKENDS = ("pytorch attention", "comfy kitchen attention")
DEFAULT_SUBJECT_ROI = (0.32, 0.34, 0.38, 0.42)


def _validate_roi(roi: tuple[float, float, float, float]) -> None:
    x, y, width, height = roi
    if width <= 0 or height <= 0 or x < 0 or y < 0 or x + width > 1 or y + height > 1:
        raise ValueError("subject ROI must be normalized x,y,width,height inside [0,1]")


def _hue_distance(a: int, b: int) -> int:
    distance = abs(a - b)
    return min(distance, 256 - distance)


def estimate_subject_hue(image_path: Path, roi: tuple[float, float, float, float] = DEFAULT_SUBJECT_ROI) -> int:
    """Find a dominant saturated hue inside an operator-defined subject ROI.

    This lightweight guard is for distinctly chromatic subjects, not semantic object detection.
    It deliberately fails if the ROI has no reliable color anchor rather than guessing.
    """
    from PIL import Image

    _validate_roi(roi)
    with Image.open(image_path) as source:
        hsv = source.convert("HSV")
        width, height = hsv.size
        x, y, rw, rh = roi
        crop = hsv.crop((int(x * width), int(y * height), max(int((x + rw) * width), 1), max(int((y + rh) * height), 1)))
        bins = [0] * 16
        pixels = crop.tobytes()
        for i in range(0, len(pixels), 3):
            hue, saturation, value = pixels[i], pixels[i + 1], pixels[i + 2]
            if saturation >= 70 and value >= 24:
                bins[(hue * 16) // 256] += 1
    bucket = max(range(16), key=bins.__getitem__)
    if bins[bucket] < 32:
        raise ValueError("No distinct saturated subject color found in subject ROI; adjust --subject-roi or use --no-subject-guard")
    return int((bucket + 0.5) * 256 / 16) % 256


def observe_subject(
    image_path: Path, hue: int, tolerance: int = 18,
    search_roi: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 0.86),
) -> SubjectObservation | None:
    """Locate the persistent chromatic subject signature; coordinates are normalized.

    The default search region omits the bottom 14% to avoid tracking a mirror reflection
    as a second continuation of the object in product-shot scenes.
    """
    from PIL import Image

    _validate_roi(search_roi)
    with Image.open(image_path) as source:
        hsv = source.convert("HSV")
        width, height = hsv.size
        rx, ry, rw, rh = search_roi
        x0, y0 = int(rx * width), int(ry * height)
        x1, y1 = max(x0 + 1, int((rx + rw) * width)), max(y0 + 1, int((ry + rh) * height))
        xs: list[int] = []
        ys: list[int] = []
        pixels = hsv.tobytes()
        for y in range(y0, y1):
            for x in range(x0, x1):
                index = (y * width + x) * 3
                target_hue, saturation, value = pixels[index], pixels[index + 1], pixels[index + 2]
                if saturation >= 55 and value >= 20 and _hue_distance(target_hue, hue) <= tolerance:
                    xs.append(x)
                    ys.append(y)
    if len(xs) < max(32, width * height // 5000):
        return None
    left, right = min(xs), max(xs) + 1
    top, bottom = min(ys), max(ys) + 1
    bbox = (left / width, top / height, right / width, bottom / height)
    return SubjectObservation(hue, bbox, (left + right) / (2 * width), (top + bottom) / (2 * height), len(xs))


def framing_risk(observation: SubjectObservation | None) -> str | None:
    """Return a fail-closed reason if the anchored subject is lost or near frame exit."""
    if observation is None:
        return "subject color anchor not detected"
    left, top, right, bottom = observation.bbox
    if left <= 0.01 or right >= 0.99 or top <= 0.01 or bottom >= 0.99:
        return "anchored subject touches the frame edge"
    if not 0.12 <= observation.center_x <= 0.88 or not 0.10 <= observation.center_y <= 0.90:
        return "anchored subject center is outside the safe framing zone"
    if right - left < 0.04 or bottom - top < 0.05:
        return "anchored subject is too small or partially lost"
    return None


def camera_pose_for_segment(
    strategy: str, segment_index: int, requested_pose: str,
    observation: SubjectObservation | None = None, keyframes: tuple[str, ...] = ("Pan Left", "Static"),
) -> str:
    """Choose a per-segment pose; bounded mode counters observed lateral drift."""
    if strategy not in CAMERA_STRATEGIES:
        raise ValueError(f"Unsupported camera strategy: {strategy}")
    if segment_index < 1:
        raise ValueError("segment_index is one-based")
    if strategy == "legacy":
        return requested_pose
    if strategy == "neutral":
        return "Static"
    if strategy == "keyframe":
        if not keyframes:
            return "Static"
        return keyframes[min(segment_index - 1, len(keyframes) - 1)]
    if segment_index == 1 or observation is None:
        return requested_pose
    if observation.center_x > 0.62:
        return "Pan Right"
    if observation.center_x < 0.38:
        return "Pan Left"
    return "Static"


def plan_segments(target_seconds: int, segment_seconds: int = SEGMENT_SECONDS, seed: int = 753934134) -> list[SegmentSpec]:
    """Plan exact 24fps Wan segments; adjacent segments share one boundary frame."""
    if target_seconds <= 0 or segment_seconds not in (3, 5) or target_seconds % segment_seconds:
        raise ValueError("target_seconds must be a positive multiple of a Wan 3s or 5s segment")
    frame_count = {3: 73, 5: 121}[segment_seconds]
    stride = frame_count - 1
    return [
        SegmentSpec(i + 1, i * stride, frame_count, frame_count if i == 0 else stride, seed + i)
        for i in range(target_seconds // segment_seconds)
    ]


def total_unique_frames(target_seconds: int, segment_seconds: int = SEGMENT_SECONDS) -> int:
    return sum(s.unique_frames for s in plan_segments(target_seconds, segment_seconds))


def _supported_target_seconds(target_seconds: int) -> bool:
    return target_seconds in (6, 9, 12)


def config_fingerprint(config: dict[str, Any]) -> str:
    data = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Atomically persist state so completed segments survive process/power interruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def segment_is_resumable(manifest: dict[str, Any], index: int, folder: Path) -> bool:
    rows = manifest.get("segments", [])
    if index < 1 or index > len(rows):
        return False
    row = rows[index - 1]
    if row.get("status") != "done":
        return False
    video = folder / row.get("video", "")
    end_frame = folder / row.get("end_frame", "")
    return (
        video.is_file() and end_frame.is_file()
        and sha256_file(video) == row.get("video_sha256")
        and sha256_file(end_frame) == row.get("end_frame_sha256")
    )


def extend_completed_manifest(
    manifest: dict[str, Any], new_config: dict[str, Any], folder: Path,
) -> bool:
    """Allow only a strictly longer run with identical generation settings and verified old segments."""
    old = manifest.get("config", {})
    old_seconds = old.get("target_seconds")
    new_seconds = new_config.get("target_seconds")
    if not isinstance(old_seconds, int) or not isinstance(new_seconds, int) or new_seconds <= old_seconds:
        return False
    old_core = {k: v for k, v in old.items() if k not in ("target_seconds", "segment_count")}
    new_core = {k: v for k, v in new_config.items() if k not in ("target_seconds", "segment_count")}
    if old_core != new_core:
        return False
    old_specs = plan_segments(old_seconds, 3, old.get("base_seed", 753934134))
    if len(manifest.get("segments", [])) != len(old_specs):
        return False
    if not all(segment_is_resumable(manifest, spec.index, folder) for spec in old_specs):
        return False
    all_specs = plan_segments(new_seconds, 3, new_config.get("base_seed", 753934134))
    if len(all_specs) <= len(old_specs):
        return False
    manifest["segments"].extend({
        "index": spec.index, "status": "pending", "start_frame": spec.start_frame,
        "frame_count": spec.frame_count, "unique_frames": spec.unique_frames, "seed": spec.seed,
    } for spec in all_specs[len(old_specs):])
    manifest["config"] = new_config
    manifest["config_sha256"] = config_fingerprint(new_config)
    manifest["status"] = "running"
    manifest["extension_from_seconds"] = old_seconds
    manifest.pop("assembly", None)
    return True


def build_wan_workflow(
    settings: dict[str, Any], prompt: str, image_name: str, seed: int,
    camera_pose: str = "Pan Left", width: int = 832, height: int = 480,
    length: int = FRAMES_PER_SEGMENT, output_prefix: str = "LocalAiVision/longform",
    reference_image_name: str | None = None, attention_backend: str = "pytorch attention",
) -> dict[str, Any]:
    """Mirror the app's Wan Fun Camera I2V graph and additionally save the last frame as a keyframe."""
    if settings.get("video_preset") != "wan21_fun_camera":
        raise ValueError("LongForm prototype only supports wan21_fun_camera I2V")
    if not image_name:
        raise ValueError("An input image is required for Wan Fun Camera I2V")
    if length < 5 or (length - 1) % 4:
        raise ValueError("Wan frame count must satisfy 4n+1")
    if attention_backend not in ATTENTION_BACKENDS:
        raise ValueError(f"Unsupported attention backend: {attention_backend}")
    neg = "static, blurry, low quality, distorted, watermark, text, jitter, deformed"
    workflow = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": settings["video_model"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": settings["video_text_encoder"], "type": "wan", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": settings["video_vae"]}},
        "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
        "7": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
        "8": {"class_type": "WanCameraEmbedding", "inputs": {"camera_pose": camera_pose, "width": width, "height": height, "length": length, "speed": 1.0}},
        "9": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "10": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["7", 0], "image": ["9", 0], "crop": "center"}},
        "11": {"class_type": "WanCameraImageToVideo", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "vae": ["3", 0], "width": width,
            "height": height, "length": length, "batch_size": 1, "clip_vision_output": ["10", 0],
            "start_image": ["9", 0], "camera_conditions": ["8", 0]}},
        "12": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["11", 0],
            "negative": ["11", 1], "latent_image": ["11", 2], "seed": seed, "steps": 20, "cfg": 6.0,
            "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["13", 0], "fps": FPS}},
        "15": {"class_type": "SaveVideo", "inputs": {"video": ["14", 0], "filename_prefix": f"{output_prefix}/segment", "format": "mp4", "codec": "h264"}},
        # Save exactly the final decoded frame; no video re-decode dependency is needed to chain segments.
        "16": {"class_type": "ImageFromBatch", "inputs": {"image": ["13", 0], "batch_index": length - 1, "length": 1}},
        "17": {"class_type": "SaveImage", "inputs": {"images": ["16", 0], "filename_prefix": f"{output_prefix}/end_frame"}},
    }
    if reference_image_name and reference_image_name != image_name:
        workflow["18"] = {"class_type": "LoadImage", "inputs": {"image": reference_image_name}}
        workflow["10"]["inputs"]["image"] = ["18", 0]
    if attention_backend == "comfy kitchen attention":
        workflow["19"] = {"class_type": "ModelAttentionBackend", "inputs": {
            "model": ["1", 0], "attention": "comfy kitchen attention"}}
        workflow["4"]["inputs"]["model"] = ["19", 0]
    return workflow


def _named_file(outputs: dict[str, Any], extensions: tuple[str, ...]) -> dict[str, str] | None:
    for node in outputs.values():
        for value in node.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and str(item.get("filename", "")).lower().endswith(extensions):
                        return item
    return None


def _host_memory_mib() -> tuple[int, int] | None:
    if os.name != "nt":
        return None
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    mib = 1024 * 1024
    return int((status.ullTotalPhys - status.ullAvailPhys) / mib), int(status.ullTotalPhys / mib)


def _record_vram_sample(live: dict[str, Any], used: int, total: int) -> None:
    live.setdefault("vram_baseline_mib", used)
    live["vram_peak_mib"] = max(used, live.get("vram_peak_mib") or used)
    live["vram_total_mib"] = total


async def _gpu_sampler(stop: asyncio.Event, live: dict[str, Any]) -> None:
    while not stop.is_set():
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=4)
            used, total = (int(x.strip()) for x in out.decode().splitlines()[0].split(","))
            _record_vram_sample(live, used, total)
        except Exception:  # best-effort system-wide meter
            live["vram_measurement_unavailable"] = True
        try:
            memory = _host_memory_mib()
            if memory:
                used, total = memory
                live.setdefault("ram_baseline_used_mib", used)
                live["ram_peak_used_mib"] = max(used, live.get("ram_peak_used_mib", used))
                live["ram_min_available_mib"] = min(total - used, live.get("ram_min_available_mib", total - used))
                live["ram_total_mib"] = total
        except Exception:
            live["ram_measurement_unavailable"] = True
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.75)
        except asyncio.TimeoutError:
            pass


async def _render_one(base: str, workflow: dict[str, Any], output_dir: Path, segment: SegmentSpec) -> tuple[Path, Path, dict[str, Any]]:
    import websockets

    client_id = uuid.uuid4().hex
    live: dict[str, Any] = {"vram_peak_mib": None}
    gpu_stop = asyncio.Event()
    gpu_task = asyncio.create_task(_gpu_sampler(gpu_stop, live))
    ws_connected = asyncio.Event()
    node_types = {key: value.get("class_type") for key, value in workflow.items()}
    started = time.monotonic()
    ws_metrics: dict[str, float] = {}

    async def listen() -> None:
        ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + f"/ws?clientId={client_id}"
        try:
            async with websockets.connect(ws_url, max_size=None, open_timeout=8) as ws:
                ws_connected.set()
                async for raw in ws:
                    if isinstance(raw, bytes):
                        continue
                    msg = json.loads(raw)
                    if not isinstance(msg, dict) or not isinstance(msg.get("data"), dict):
                        continue
                    data = msg["data"]
                    if data.get("prompt_id", live.get("prompt_id")) != live.get("prompt_id") and live.get("prompt_id"):
                        continue
                    now = time.monotonic()
                    typ = msg.get("type")
                    if typ == "progress":
                        ws_metrics.setdefault("first_step_at", now)
                        ws_metrics["last_step_at"] = now
                        ws_metrics["last_step"] = float(data.get("value", 0))
                        ws_metrics["max_steps"] = float(data.get("max", 0))
                    elif typ == "executing" and node_types.get(str(data.get("node"))) == "SaveVideo":
                        ws_metrics["encode_start"] = now
                    elif typ == "executed" and node_types.get(str(data.get("node"))) == "SaveVideo":
                        ws_metrics["encode_end"] = now
        except Exception as exc:
            live["websocket_warning"] = str(exc)[:240]

    ws_task = asyncio.create_task(listen())
    try:
        try:
            await asyncio.wait_for(ws_connected.wait(), timeout=8)
        except asyncio.TimeoutError:
            pass
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=5)) as client:
            response = await client.post(f"{base}/prompt", json={"prompt": workflow, "client_id": client_id})
            response.raise_for_status()
            pid = response.json()["prompt_id"]
            live["prompt_id"] = pid
            deadline = time.monotonic() + 1800
            history: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                await asyncio.sleep(1.25)
                result = (await client.get(f"{base}/history/{pid}")).json().get(pid)
                if result:
                    status = result.get("status", {}).get("status_str")
                    if status == "error":
                        msgs = [m[1].get("exception_message", "") for m in result.get("status", {}).get("messages", []) if m[0] == "execution_error"]
                        raise RuntimeError((msgs or ["ComfyUI execution error"])[0])
                    if status == "success":
                        history = result
                        break
            if history is None:
                raise TimeoutError(f"ComfyUI job {pid} did not finish within 30 minutes")
            video = _named_file(history.get("outputs", {}), (".mp4", ".webm", ".mov"))
            frame = _named_file(history.get("outputs", {}), (".png", ".jpg", ".webp"))
            if not video or not frame:
                raise RuntimeError("ComfyUI success lacks expected MP4 or final-frame SaveImage output")
            files: list[Path] = []
            for item, name in ((video, f"segment-{segment.index:02d}.mp4"), (frame, f"segment-{segment.index:02d}-end.png")):
                r = await client.get(f"{base}/view", params={"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")})
                r.raise_for_status()
                path = output_dir / name
                path.write_bytes(r.content)
                files.append(path)
        ended = time.monotonic()
        first = ws_metrics.get("first_step_at")
        last = ws_metrics.get("last_step_at")
        metrics = {
            "prompt_id": live.get("prompt_id"), "wall_seconds": round(ended - started, 3),
            "setup_to_first_step_seconds": round(first - started, 3) if first else None,
            "sampling_observed_seconds": round(last - first, 3) if first and last else None,
            "sampling_steps_observed": int(ws_metrics["max_steps"]) if "max_steps" in ws_metrics else None,
            "savevideo_encode_seconds": round(ws_metrics["encode_end"] - ws_metrics["encode_start"], 3) if "encode_start" in ws_metrics and "encode_end" in ws_metrics else None,
            "vram_baseline_mib": live.get("vram_baseline_mib"), "vram_peak_mib": live.get("vram_peak_mib"),
            "vram_total_mib": live.get("vram_total_mib"),
            "ram_baseline_used_mib": live.get("ram_baseline_used_mib"),
            "ram_peak_used_mib": live.get("ram_peak_used_mib"),
            "ram_min_available_mib": live.get("ram_min_available_mib"),
            "ram_total_mib": live.get("ram_total_mib"),
            "measurement_note": "System-wide nvidia-smi and Win32 RAM sampled every ~0.75s; wall time includes queue, model setup, sampling, VAE decode, encode and download.",
            "websocket_warning": live.get("websocket_warning"),
        }
        return files[0], files[1], metrics
    finally:
        gpu_stop.set()
        await gpu_task
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass


async def _verify_models(
    base: str, attention_backend: str = "pytorch attention", camera_poses: tuple[str, ...] = (),
) -> dict[str, Any]:
    requirements = {
        "UNETLoader": ("unet_name", "wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors"),
        "CLIPLoader": ("clip_name", "umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
        "VAELoader": ("vae_name", "wan_2.1_vae.safetensors"),
        "CLIPVisionLoader": ("clip_name", "clip_vision_h.safetensors"),
    }
    status: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=12) as c:
        stats = (await c.get(f"{base}/system_stats")).json()
        queue = (await c.get(f"{base}/queue")).json()
        if queue.get("queue_running") or queue.get("queue_pending"):
            raise RuntimeError("ComfyUI already has user work queued/running; LongForm prototype will not submit a competing job")
        for node, (field, expected) in requirements.items():
            r = await c.get(f"{base}/object_info/{node}")
            r.raise_for_status()
            choices = r.json()[node]["input"]["required"][field][0]
            if expected not in choices:
                raise RuntimeError(f"Required installed model not verified: {expected} ({node}/{field})")
            status[expected] = "present in ComfyUI object_info"
        attention = await c.get(f"{base}/object_info/ModelAttentionBackend")
        if attention.is_success:
            choices = attention.json()["ModelAttentionBackend"]["input"]["required"]["attention"][1]["options"]
            status["attention_backends"] = choices
        else:
            choices = ["pytorch attention"]
            status["attention_backends"] = choices
        if attention_backend not in choices:
            raise RuntimeError(f"Requested attention backend is not installed/available in ComfyUI: {attention_backend}")
        camera = await c.get(f"{base}/object_info/WanCameraEmbedding")
        camera.raise_for_status()
        supported_poses = camera.json()["WanCameraEmbedding"]["input"]["required"]["camera_pose"][1]["options"]
        status["camera_poses"] = supported_poses
        unsupported_poses = sorted(set(camera_poses) - set(supported_poses))
        if unsupported_poses:
            raise RuntimeError(f"Requested camera poses are not supported by installed ComfyUI: {unsupported_poses}")
    status["gpu"] = (stats.get("devices") or [{}])[0]
    status["ram"] = stats.get("system", {})
    return status


async def run_prototype(args: argparse.Namespace) -> Path:
    base = args.comfy_url.rstrip("/")
    target_seconds = int(getattr(args, "target_seconds", 6))
    if not _supported_target_seconds(target_seconds):
        raise ValueError("LongForm prototype currently supports 6, 9 or 12 seconds")
    out = Path(args.output_dir).resolve()
    manifest_path = out / "manifest.json"
    initial = Path(args.input_image).resolve()
    roi = tuple(args.subject_roi)
    _validate_roi(roi)
    if not initial.is_file():
        raise FileNotFoundError(initial)
    if args.camera_strategy not in CAMERA_STRATEGIES:
        raise ValueError(f"Unsupported camera strategy: {args.camera_strategy}")
    if args.attention_backend not in ATTENTION_BACKENDS:
        raise ValueError(f"Unsupported attention backend: {args.attention_backend}")
    if args.camera_strategy == "bounded" and not args.subject_guard:
        raise ValueError("bounded camera strategy requires the subject framing guard")
    anchor_hue = estimate_subject_hue(initial, roi) if args.subject_guard else None
    initial_observation = observe_subject(initial, anchor_hue) if anchor_hue is not None else None
    if args.subject_guard and framing_risk(initial_observation):
        raise ValueError(f"Initial image is not trackable inside the configured subject ROI: {framing_risk(initial_observation)}")
    if args.resume:
        if not out.is_dir() or not manifest_path.is_file():
            raise FileNotFoundError(f"Cannot resume without an existing manifest: {manifest_path}")
    elif out.exists() and any(out.iterdir()):
        raise FileExistsError(f"Refusing to overwrite data in an existing run directory: {out}")
    out.mkdir(parents=True, exist_ok=True)
    environment = await _verify_models(base, args.attention_backend,
                                       (args.camera_pose, *tuple(args.camera_keyframes), "Static", "Pan Right"))
    specs = plan_segments(target_seconds, 3, args.seed)
    config = {
        "model": "wan21_fun_camera", "prompt": args.prompt, "camera_pose": args.camera_pose,
        "camera_strategy": args.camera_strategy, "camera_keyframes": list(args.camera_keyframes),
        "attention_backend": args.attention_backend, "subject_guard": args.subject_guard,
        "subject_roi": list(roi), "subject_hue": anchor_hue,
        "target_seconds": target_seconds, "segment_count": len(specs),
        "width": 832, "height": 480, "fps": FPS, "segment_seconds": 3, "frames_per_segment": FRAMES_PER_SEGMENT,
        "steps": 20, "cfg": 6.0, "sampler": "uni_pc", "scheduler": "simple", "base_seed": args.seed,
        "initial_image_sha256": sha256_file(initial), "overlap_frames": 1,
    }
    fingerprint = config_fingerprint(config)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("config_sha256") != fingerprint:
            if not extend_completed_manifest(manifest, config, out):
                raise ValueError("Resume refused: config differs, or a longer target is not compatible with all verified completed segments")
            save_manifest(manifest_path, manifest)
    else:
        manifest = {"schema": 2, "created_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
                    "environment_preflight": environment, "config": config, "config_sha256": fingerprint, "segments": [
                        {"index": s.index, "status": "pending", "start_frame": s.start_frame, "frame_count": s.frame_count,
                         "unique_frames": s.unique_frames, "seed": s.seed} for s in specs]}
        manifest["subject_guard_note"] = "Dominant-hue tracking within an operator-selected ROI; not semantic object detection."
        save_manifest(manifest_path, manifest)
    current_source = initial
    current_observation = initial_observation
    persistent_reference = args.camera_strategy in ("bounded", "keyframe")
    async with httpx.AsyncClient(timeout=60) as client:
        fixed_reference_name = await _upload_local_image(client, base, initial) if persistent_reference else None
        for spec in specs:
            row = manifest["segments"][spec.index - 1]
            video_path = out / f"segment-{spec.index:02d}.mp4"
            frame_path = out / f"segment-{spec.index:02d}-end.png"
            if segment_is_resumable(manifest, spec.index, out):
                current_source = frame_path
                current_observation = observe_subject(frame_path, anchor_hue) if anchor_hue is not None else None
                continue
            if args.subject_guard and spec.index > 1:
                risk = framing_risk(current_observation)
                if risk:
                    manifest["status"] = "drift_guard_stopped"
                    manifest["stop_reason"] = risk
                    save_manifest(manifest_path, manifest)
                    raise RuntimeError(f"Refusing segment {spec.index}: subject framing guard: {risk}")
            pose = camera_pose_for_segment(args.camera_strategy, spec.index, args.camera_pose,
                                           current_observation, tuple(args.camera_keyframes))
            row.update({"status": "running", "source_image": str(current_source), "camera_pose": pose,
                        "reference_image": str(initial if persistent_reference else current_source),
                        "started_utc": datetime.now(timezone.utc).isoformat()})
            save_manifest(manifest_path, manifest)
            source_name = await _upload_local_image(client, base, current_source)
            reference_name = fixed_reference_name if persistent_reference else source_name
            settings = {"video_preset": "wan21_fun_camera", "video_model": "wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors",
                        "video_text_encoder": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "video_vae": "wan_2.1_vae.safetensors"}
            workflow = build_wan_workflow(settings, args.prompt, source_name, spec.seed, pose,
                                          output_prefix=f"LocalAiVision/longform/{out.name}/s{spec.index:02d}",
                                          reference_image_name=reference_name,
                                          attention_backend=args.attention_backend)
            try:
                video_path, frame_path, metrics = await _render_one(base, workflow, out, spec)
                observation = observe_subject(frame_path, anchor_hue) if anchor_hue is not None else None
                risk = framing_risk(observation) if args.subject_guard else None
                row.update({"status": "done", "video": video_path.name, "end_frame": frame_path.name,
                            "video_sha256": sha256_file(video_path), "end_frame_sha256": sha256_file(frame_path),
                            "finished_utc": datetime.now(timezone.utc).isoformat(), "metrics": metrics,
                            "subject_framing": asdict(observation) if observation else None,
                            "framing_risk": risk})
                current_source = frame_path
                current_observation = observation
            except Exception as exc:
                row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"[:1200],
                            "failed_utc": datetime.now(timezone.utc).isoformat()})
                manifest["status"] = "interrupted"
                save_manifest(manifest_path, manifest)
                raise
            save_manifest(manifest_path, manifest)
            if risk and spec.index < len(specs):
                manifest["status"] = "drift_guard_stopped"
                manifest["stop_reason"] = risk
                manifest["stopped_before_segment"] = spec.index + 1
                save_manifest(manifest_path, manifest)
                raise RuntimeError(f"Subject framing guard stopped before segment {spec.index + 1}: {risk}")
    assembled = out / f"longform-{target_seconds}s.mp4"
    all_segments_resumable = all(segment_is_resumable(manifest, spec.index, out) for spec in specs)
    if not assembled.exists() or not manifest.get("assembly") or not all_segments_resumable:
        manifest["status"] = "assembling"
        save_manifest(manifest_path, manifest)
        comfy_python = Path(args.comfy_python).resolve()
        if not comfy_python.is_file():
            manifest["status"] = "assembly_failed"
            save_manifest(manifest_path, manifest)
            raise FileNotFoundError(f"ComfyUI Python (with PyAV) not found: {comfy_python}")
        worker = Path(__file__).resolve().parents[1] / "scripts" / "longform_assemble_av.py"
        report_path = out / "assembly-report.json"
        target_frames = target_seconds * FPS
        segment_paths = [str(out / f"segment-{spec.index:02d}.mp4") for spec in specs]
        try:
            subprocess.run([str(comfy_python), str(worker), str(assembled), str(report_path), str(target_frames),
                            *segment_paths], check=True, capture_output=True, text=True, timeout=600)
            manifest["assembly"] = {"file": assembled.name, "sha256": sha256_file(assembled),
                                     "report": json.loads(report_path.read_text(encoding="utf-8"))}
        except Exception as exc:
            manifest["status"] = "assembly_failed"
            manifest["assembly_error"] = f"{type(exc).__name__}: {exc}"[:1200]
            save_manifest(manifest_path, manifest)
            raise
    manifest["status"] = "done"
    manifest["total_unique_frames"] = total_unique_frames(target_seconds, 3)
    manifest["note"] = f"Experimental {len(specs)}-segment LongForm continuity; strategy, persistent visual anchor and framing guard are recorded per run."
    save_manifest(manifest_path, manifest)
    _write_gallery(out, manifest)
    return out


async def _upload_local_image(client: httpx.AsyncClient, base: str, path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    response = await client.post(f"{base}/upload/image", files={"image": (path.name, path.read_bytes(), mime)}, data={"overwrite": "true"})
    response.raise_for_status()
    result = response.json()
    return f"{result['subfolder']}/{result['name']}" if result.get("subfolder") else result["name"]


def _write_gallery(folder: Path, manifest: dict[str, Any]) -> None:
    rows = []
    combined_name = (manifest.get("assembly") or {}).get("file")
    combined = folder / combined_name if combined_name else None
    if combined and combined.is_file():
        title = combined.stem.replace("longform-", "").replace("s", "-second")
        rows.append(f'<section><h2>Assembled {title} preview</h2><video controls src="{combined.name}"></video></section>')
    for row in manifest["segments"]:
        if row.get("status") == "done":
            rows.append(f'<section><h2>Segment {row["index"]}</h2><video controls src="{row["video"]}"></video><img src="{row["end_frame"]}" alt="End frame"></section>')
    target = manifest.get("config", {}).get("target_seconds", 6)
    html = f"<!doctype html><meta charset=utf-8><title>LongForm continuity experiment</title><style>body{{font:16px system-ui;background:#111;color:#eee}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:1rem}}video,img{{width:100%}}section{{background:#222;padding:1rem}}</style><h1>LongForm · {target}-second continuity experiment</h1><main>" + "".join(rows) + "</main>"
    (folder / "index.html").write_text(html, encoding="utf-8")


def _default_comfy_python() -> str:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "Comfy-Desktop" / "ComfyUI-Installs" / "ComfyUI" / "ComfyUI"
    return str(root / ".venv" / "Scripts" / "python.exe")


def _parse_roi(value: str) -> tuple[float, float, float, float]:
    try:
        roi = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be four comma-separated normalized numbers") from exc
    if len(roi) != 4:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height")
    try:
        _validate_roi(roi)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return roi


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental resumable Wan LongForm continuity prototype (6/9/12s in 3s segments)")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--input-image", required=True, help="Local SDXL/keyframe image; uploaded into ComfyUI input")
    parser.add_argument("--output-dir", required=True, help="New local run directory; existing directory only with --resume")
    parser.add_argument("--comfy-python", default=_default_comfy_python(), help="Existing ComfyUI Python used only for local PyAV assembly")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--seed", type=int, default=753934134)
    parser.add_argument("--target-seconds", type=int, choices=(6, 9, 12), default=6,
                        help="Total duration; each Wan segment is 3 seconds")
    parser.add_argument("--camera-pose", default="Pan Left", help="Requested starting pose for legacy/bounded strategies")
    parser.add_argument("--camera-strategy", choices=CAMERA_STRATEGIES, default="legacy",
                        help="legacy repeats pose; neutral uses Static; bounded corrects observed lateral drift; keyframe uses explicit per-segment poses and a persistent reference")
    parser.add_argument("--camera-keyframes", default="Pan Left,Static", help="Comma-separated pose sequence for keyframe strategy")
    parser.add_argument("--subject-roi", type=_parse_roi, default=DEFAULT_SUBJECT_ROI,
                        help="Normalized x,y,width,height color-anchor ROI in the reference image")
    parser.add_argument("--no-subject-guard", dest="subject_guard", action="store_false",
                        help="Disable the chromatic-subject framing guard (not recommended for longform)")
    parser.set_defaults(subject_guard=True)
    parser.add_argument("--attention-backend", choices=ATTENTION_BACKENDS, default="pytorch attention",
                        help="Experimental ComfyUI attention backend; default remains PyTorch")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()
    args.camera_keyframes = tuple(item.strip() for item in args.camera_keyframes.split(",") if item.strip())
    result = asyncio.run(run_prototype(args))
    print(json.dumps({"status": "done", "output_dir": str(result), "gallery": str(result / "index.html"),
                      "manifest": str(result / "manifest.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
