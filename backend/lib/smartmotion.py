"""Experimental image-to-video 2.5D SmartMotion renderer; independent of production workflows.

This renderer makes bounded camera motion from one still image and a locally cached
Depth Anything V2 Small model. It does not synthesize object motion or new scene content.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FPS = 24
DEFAULT_CACHE = Path.home() / ".cache" / "huggingface" / "hub" / "models--depth-anything--Depth-Anything-V2-Small-hf" / "snapshots"


def recommend_mode(*, still_image: bool, requested_motion: str, fast_model_available: bool = False) -> dict[str, str]:
    """Conservative routing advice; never claims 2.5D can replace generative motion."""
    motion = requested_motion.strip().lower()
    if still_image and motion in {"camera", "dolly", "pan", "zoom", "product-ad", "parallax"}:
        return {"mode": "SmartMotion", "reason": "A still-image scene with camera-only motion is suitable for bounded 2.5D; no object motion is synthesized."}
    if fast_model_available:
        return {"mode": "FastVideo", "reason": "An explicitly verified lightweight video model is available for generative motion."}
    return {"mode": "Cinematic", "reason": "The requested motion needs generative video; no separately validated FastVideo model is configured."}


def discover_local_depth_model(cache_root: Path = DEFAULT_CACHE) -> Path:
    """Find a fully local cached Depth Anything V2 Small snapshot; never accesses the network."""
    snapshots = sorted(cache_root.glob("*/config.json"), key=lambda p: p.parent.stat().st_mtime, reverse=True) if cache_root.exists() else []
    for config in snapshots:
        try:
            metadata = json.loads(config.read_text(encoding="utf-8"))
            if (metadata.get("model_type") == "depth_anything"
                    and (config.parent / "model.safetensors").is_file()
                    and (config.parent / "preprocessor_config.json").is_file()):
                return config.parent
        except (OSError, json.JSONDecodeError):
            continue
    raise FileNotFoundError("A complete local Depth Anything V2 Small snapshot was not found; no model was downloaded")


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def camera_state(frame_index: int, frame_count: int, width: int, height: int) -> dict[str, float]:
    """A gentle 5s product-ad move: 7% push-in plus bounded lateral/vertical drift."""
    if frame_count < 2 or not 0 <= frame_index < frame_count:
        raise ValueError("frame index must be within a sequence of at least two frames")
    t = frame_index / (frame_count - 1)
    e = smoothstep(t)
    # A subtle, bounded arc avoids a linear cumulative pan and leaves crop margin for reprojection.
    arc = math.sin(math.pi * e)
    return {
        "t": t,
        "zoom": 1.0 + 0.07 * e,
        "pan_x": width * (0.012 * e + 0.004 * arc),
        "pan_y": -height * 0.004 * arc,
        "parallax": width * 0.008 * e,
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _system_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        raw = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], timeout=3)
        used, total = (int(part.strip()) for part in raw.decode().splitlines()[0].split(","))
        result.update(vram_used_mib=used, vram_total_mib=total)
    except Exception:
        result["vram_unavailable"] = True
    if os.name == "nt":
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("available", ctypes.c_ulonglong), ("page_total", ctypes.c_ulonglong), ("page_available", ctypes.c_ulonglong), ("virtual_total", ctypes.c_ulonglong), ("virtual_available", ctypes.c_ulonglong), ("extended", ctypes.c_ulonglong)]
        memory = MemoryStatus(); memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            result.update(ram_used_mib=(memory.total-memory.available)//(1024**2), ram_available_mib=memory.available//(1024**2), ram_total_mib=memory.total//(1024**2))
    return result


def _load_depth(image: Any, model_dir: Path, device: str) -> tuple[Any, dict[str, Any]]:
    # Enforce local-only loading even if the machine is online.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    torch.cuda.reset_peak_memory_stats() if device.startswith("cuda") else None
    start = time.perf_counter()
    processor = AutoImageProcessor.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForDepthEstimation.from_pretrained(str(model_dir), local_files_only=True).eval().to(device)
    loaded = time.perf_counter()
    inputs = processor(images=image, return_tensors="pt").to(device)
    with torch.inference_mode():
        raw = model(**inputs).predicted_depth
        depth = torch.nn.functional.interpolate(raw.unsqueeze(1), size=(image.height, image.width), mode="bicubic", align_corners=False)[0, 0]
    lo, hi = torch.quantile(depth.float(), torch.tensor([0.02, 0.98], device=depth.device))
    depth = ((depth - lo) / (hi - lo).clamp_min(1e-6)).clamp(0, 1)
    # Mild smoothing suppresses prediction noise without removing strong depth boundaries.
    depth = torch.nn.functional.avg_pool2d(torch.nn.functional.pad(depth[None, None], (1,1,1,1), mode="replicate"), 3, stride=1)[0, 0]
    elapsed = time.perf_counter()
    depth_info = {"model": str(model_dir), "model_sha256": _sha256(model_dir / "model.safetensors"),
                  "load_seconds": round(loaded-start, 3), "inference_seconds": round(elapsed-loaded, 3),
                  "depth_width": image.width, "depth_height": image.height,
                  "gpu_peak_allocated_mib": int(torch.cuda.max_memory_allocated()/1024**2) if device.startswith("cuda") else None}
    # Free model weights before the frame render / encoder to bound memory.
    del model, processor, inputs, raw
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    return depth, depth_info


def render(input_image: Path, output_dir: Path, model_dir: Path | None = None, *, fps: int = FPS, seconds: int = 5) -> Path:
    generation_started = time.perf_counter()
    if seconds < 1 or fps < 1:
        raise ValueError("seconds and fps must be positive")
    if not input_image.is_file():
        raise FileNotFoundError(input_image)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output directory: {output_dir}")
    model_dir = model_dir or discover_local_depth_model()
    output_dir.mkdir(parents=True, exist_ok=True)

    import av
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        raise RuntimeError("SmartMotion prototype requires the available NVIDIA CUDA GPU for depth and reprojection")
    source = Image.open(input_image).convert("RGB")
    # Preserve source aspect and resolution. No hidden 1080p upscale or frame interpolation.
    width, height = source.size
    depth, depth_metrics = _load_depth(source, model_dir, device)
    depth_preview = (depth.detach().cpu().numpy() * 255).astype(np.uint8)
    Image.fromarray(depth_preview, mode="L").save(output_dir / "depth-relative.png")

    rgb = torch.from_numpy(np.asarray(source).copy()).to(device=device, dtype=torch.float32).permute(2, 0, 1)[None] / 255.0
    depth = depth.to(device=device, dtype=torch.float32)[None, None]
    yy, xx = torch.meshgrid(torch.arange(height, device=device, dtype=torch.float32), torch.arange(width, device=device, dtype=torch.float32), indexing="ij")
    cx, cy = (width-1)/2, (height-1)/2
    # Depth is treated as a continuous pseudo-layer field; this is not semantic segmentation or true geometry.
    rel_depth = (depth[0, 0] - depth.mean()).clamp(-0.5, 0.5)
    frames = seconds * fps
    mp4 = output_dir / "smartmotion.mp4"
    render_started = time.perf_counter()
    encoder_options = {"preset": "p5", "rc": "vbr", "cq": "19"}
    first_frame_seconds = None
    gpu_base = _system_snapshot()
    vram_peak = gpu_base.get("vram_used_mib")
    ram_peak = gpu_base.get("ram_used_mib")
    encode = av.open(str(mp4), mode="w")
    stream = encode.add_stream("h264_nvenc", rate=fps)
    stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
    stream.options = dict(encoder_options)
    try:
        for index in range(frames):
            state = camera_state(index, frames, width, height)
            # Inverse warp: zoom and camera translation are smooth; depth changes translation by <0.8% width.
            sx = (xx-cx)/state["zoom"] + cx - state["pan_x"] - rel_depth * state["parallax"]
            sy = (yy-cy)/state["zoom"] + cy - state["pan_y"]
            gx = (sx / max(width-1, 1)) * 2 - 1
            gy = (sy / max(height-1, 1)) * 2 - 1
            grid = torch.stack((gx, gy), dim=-1)[None]
            # Reflection padding fills crop margins without black holes. Movement is crop-bounded.
            frame = F.grid_sample(rgb, grid, mode="bilinear", padding_mode="reflection", align_corners=True)[0]
            arr = (frame.clamp(0, 1).mul(255).byte().permute(1, 2, 0).contiguous().cpu().numpy())
            video_frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
            for packet in stream.encode(video_frame):
                encode.mux(packet)
            if first_frame_seconds is None:
                first_frame_seconds = time.perf_counter() - render_started
            if index % max(1, fps//2) == 0:
                snap = _system_snapshot()
                if snap.get("vram_used_mib") is not None:
                    vram_peak = max(vram_peak or 0, snap["vram_used_mib"])
                if snap.get("ram_used_mib") is not None:
                    ram_peak = max(ram_peak or 0, snap["ram_used_mib"])
        for packet in stream.encode():
            encode.mux(packet)
    finally:
        encode.close()
    render_seconds = time.perf_counter() - render_started
    # Verify the produced MP4 decodes completely and has intended cadence.
    verify_started = time.perf_counter()
    probe = av.open(str(mp4))
    video = next(s for s in probe.streams if s.type == "video")
    decoded = sum(1 for _ in probe.decode(video=0))
    duration = float(video.duration * video.time_base) if video.duration is not None else None
    probe.close()
    verify_seconds = time.perf_counter() - verify_started
    total_seconds = time.perf_counter() - generation_started
    if decoded != frames:
        raise RuntimeError(f"Encoded output verification failed: decoded {decoded}/{frames} frames")
    manifest = {
        "schema": 1, "mode": "SmartMotion 2.5D camera-only prototype", "created_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(input_image), "input_sha256": _sha256(input_image), "output": mp4.name,
        "width": width, "height": height, "fps": fps, "seconds_requested": seconds, "frames_decoded": decoded, "duration_seconds": duration,
        "codec": "h264_nvenc", "encoder_options": encoder_options, "nvenc_verified": True,
        "depth": depth_metrics, "render_and_encode_seconds": round(render_seconds, 3),
        "container_verification_seconds": round(verify_seconds, 3), "total_wall_seconds_including_depth": round(total_seconds, 3),
        "output_fps": round(decoded / max(render_seconds, 1e-9), 3), "first_frame_seconds": round(first_frame_seconds or 0, 3),
        "vram_baseline_mib": gpu_base.get("vram_used_mib"), "vram_peak_sampled_mib": vram_peak,
        "vram_total_mib": gpu_base.get("vram_total_mib"), "ram_baseline_used_mib": gpu_base.get("ram_used_mib"),
        "ram_peak_sampled_mib": ram_peak, "ram_total_mib": gpu_base.get("ram_total_mib"),
        "resource_measurement_note": "System-wide nvidia-smi and Win32 RAM sampling at baseline and every 12 frames; short peaks may be missed; GPU memory is not process-isolated.",
        "notes": ["Relative depth reprojection only: no semantic subject masks, articulated/object motion, or generative filling of genuinely unseen regions.",
                  "Reflection padding avoids blank exposed borders for this bounded, zoom-in camera move but may mirror edge pixels.",
                  "One still image cannot provide temporal material/identity consistency beyond preserving the source pixels."]
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    html_doc = ("<!doctype html><meta charset=utf-8><title>SmartMotion prototype</title>"
                "<style>body{font:16px system-ui;background:#111;color:#eee;max-width:1100px;margin:2rem auto}video,img{width:100%}section{margin:1.5rem 0}</style>"
                "<h1>SmartMotion · local 2.5D still animation</h1><video controls src='smartmotion.mp4'></video>"
                "<section><h2>Estimated relative depth (not metric depth)</h2><img src='depth-relative.png'></section>"
                f"<pre>{html.escape(json.dumps(manifest,ensure_ascii=False,indent=2))}</pre>")
    (output_dir / "index.html").write_text(html_doc, encoding="utf-8")
    return mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="Local experimental 2.5D SmartMotion renderer; no network or production changes")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--depth-model", type=Path, default=None, help="Existing local Depth Anything V2 Small snapshot; no download is attempted")
    parser.add_argument("--seconds", type=int, default=5)
    parser.add_argument("--fps", type=int, default=FPS)
    args = parser.parse_args()
    path = render(args.input, args.output_dir, args.depth_model, fps=args.fps, seconds=args.seconds)
    print(json.dumps({"status":"done","video":str(path),"gallery":str(path.parent/"index.html"),"manifest":str(path.parent/"manifest.json")},indent=2))


if __name__ == "__main__":
    main()
