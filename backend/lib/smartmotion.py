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


CAMERA_MOVES = ("push_in", "pan_left", "pan_right", "tilt_up", "tilt_down", "orbit_subtle", "static")


def camera_state(frame_index: int, frame_count: int, width: int, height: int, motion: str = "push_in") -> dict[str, float]:
    """Bounded 2.5D camera path. These are image-space moves, not true 3D camera solves."""
    if frame_count < 2 or not 0 <= frame_index < frame_count:
        raise ValueError("frame index must be within a sequence of at least two frames")
    if motion not in CAMERA_MOVES:
        raise ValueError(f"unsupported SmartMotion camera move: {motion}")
    t = frame_index / (frame_count - 1)
    e = smoothstep(t)
    arc = math.sin(math.pi * e)
    if motion == "static":
        return {"t": t, "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "parallax": 0.0}
    if motion == "push_in":
        # Keep the validated V2-N motion envelope: gentle zoom and shallow depth parallax.
        return {"t": t, "zoom": 1.0 + 0.07 * e, "pan_x": width * (0.012 * e + 0.004 * arc),
                "pan_y": -height * 0.004 * arc, "parallax": width * 0.008 * e}
    if motion in ("pan_left", "pan_right"):
        sign = 1.0 if motion == "pan_left" else -1.0
        return {"t": t, "zoom": 1.025, "pan_x": sign * width * 0.018 * (e - 0.5),
                "pan_y": 0.0, "parallax": sign * width * 0.002 * (e - 0.5)}
    if motion in ("tilt_up", "tilt_down"):
        sign = 1.0 if motion == "tilt_up" else -1.0
        return {"t": t, "zoom": 1.025, "pan_x": 0.0, "pan_y": sign * height * 0.018 * (e - 0.5),
                "parallax": 0.0}
    return {"t": t, "zoom": 1.0 + 0.025 * e, "pan_x": width * 0.008 * math.sin(2 * math.pi * e),
            "pan_y": -height * 0.006 * arc, "parallax": width * 0.004 * math.sin(2 * math.pi * e)}


def runtime_candidates() -> list[Path]:
    """Candidate local interpreters with the already-installed renderer dependencies; no install/network."""
    candidates: list[Path] = []
    for key in ("LAS_SMARTMOTION_PYTHON", "COMFYUI_PYTHON"):
        if os.environ.get(key):
            candidates.append(Path(os.environ[key]).expanduser())
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    candidates.extend([
        local / "Comfy-Desktop" / "ComfyUI-Installs" / "ComfyUI" / "ComfyUI" / ".venv" / "Scripts" / "python.exe",
        local / "Comfy-Desktop" / "ComfyUI-Installs" / "ComfyUI" / "ComfyUI" / ".venv" / "bin" / "python",
    ])
    seen: set[str] = set()
    return [p for p in candidates if p.is_file() and not (str(p.resolve()).casefold() in seen or seen.add(str(p.resolve()).casefold()))]


def discover_local_video_runtime() -> Path | None:
    """Find ComfyUI's local server without starting/reconfiguring it; no network service or install."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2) as response:
            if response.status != 200:
                return None
    except Exception:
        return None
    return Path("http://127.0.0.1:8188")


def local_runtime() -> tuple[Path, Path]:
    """Return an installed Python runtime and cached depth model, or fail closed without downloading."""
    model_dir = discover_local_depth_model()
    probe = "import importlib.util,sys; req=['torch','transformers','av','PIL']; missing=[x for x in req if importlib.util.find_spec(x) is None]; import torch; sys.exit(1 if missing or not torch.cuda.is_available() else 0)"
    for interpreter in runtime_candidates():
        try:
            check = subprocess.run([str(interpreter), "-c", probe], capture_output=True, timeout=15)
            if check.returncode == 0:
                return interpreter, model_dir
        except (OSError, subprocess.SubprocessError):
            continue
    raise RuntimeError("SmartMotion needs an existing local Python runtime with torch, transformers, PyAV and Pillow; no packages were installed")


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
    if device.startswith("cuda"):
        torch.cuda.synchronize(device)
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


def parse_output_size(value: str) -> tuple[int, int]:
    """Parse WIDTHxHEIGHT; output sizing is explicit so an upscale/crop is never hidden."""
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except (ValueError, TypeError) as exc:
        raise ValueError("output size must be WIDTHxHEIGHT, e.g. 1920x1080") from exc
    if width < 16 or height < 16 or width > 7680 or height > 4320:
        raise ValueError("output dimensions must be between 16x16 and 7680x4320")
    return width, height


def center_crop_box(source_width: int, source_height: int, target_width: int, target_height: int) -> tuple[int, int, int, int]:
    """Largest centered source crop matching target aspect; never distorts image geometry."""
    if min(source_width, source_height, target_width, target_height) <= 0:
        raise ValueError("source and target dimensions must be positive")
    source_aspect = source_width / source_height
    target_aspect = target_width / target_height
    if source_aspect > target_aspect:
        crop_width = max(1, round(source_height * target_aspect))
        left = (source_width - crop_width) // 2
        return left, 0, left + crop_width, source_height
    crop_height = max(1, round(source_width / target_aspect))
    top = (source_height - crop_height) // 2
    return 0, top, source_width, top + crop_height


def render(input_image: Path, output_dir: Path, model_dir: Path | None = None, *, fps: int = FPS, seconds: int = 5, output_size: tuple[int, int] | None = None, motion: str = "push_in", on_progress=None) -> Path:
    generation_started = time.perf_counter()
    if seconds < 1 or seconds > 30 or fps < 1 or fps > 60:
        raise ValueError("seconds must be 1–30 and fps 1–60")
    if motion not in CAMERA_MOVES:
        raise ValueError(f"unsupported SmartMotion camera move: {motion}")
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
    source_width, source_height = source.size
    depth, depth_metrics = _load_depth(source, model_dir, device)
    transform = {"source_width": source_width, "source_height": source_height, "output_width": source_width, "output_height": source_height,
                 "operation": "none (native source dimensions)", "crop_box": [0, 0, source_width, source_height], "upscaled": False}
    if output_size is not None:
        width, height = output_size
        left, top, right, bottom = center_crop_box(source_width, source_height, width, height)
        crop_box = (left, top, right, bottom)
        source = source.crop(crop_box).resize((width, height), Image.Resampling.LANCZOS)
        depth = torch.nn.functional.interpolate(depth[None, None, top:bottom, left:right], size=(height, width), mode="bicubic", align_corners=False)[0, 0]
        transform = {"source_width": source_width, "source_height": source_height, "output_width": width, "output_height": height,
                    "operation": "center crop to target aspect, then Lanczos upscale" if width > right-left or height > bottom-top else "center crop to target aspect, then resize",
                    "crop_box": [left, top, right, bottom], "upscaled": width > right-left or height > bottom-top,
                    "source_crop_width": right-left, "source_crop_height": bottom-top}
    else:
        width, height = source.size
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
            state = camera_state(index, frames, width, height, motion)
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
            if on_progress and ((index + 1) % fps == 0 or index + 1 == frames):
                on_progress(index + 1, frames)
        for packet in stream.encode():
            encode.mux(packet)
    finally:
        encode.close()
    render_seconds = time.perf_counter() - render_started
    # Tell the UI that frame rendering is done and container verification is now running.
    if on_progress:
        on_progress(frames, frames, phase="verification")
    # Verify the produced MP4 decodes completely and has intended cadence.
    verify_started = time.perf_counter()
    probe = av.open(str(mp4))
    video = next(s for s in probe.streams if s.type == "video")
    decoded = 0
    identical_adjacent = 0
    frame_deltas: list[float] = []
    previous = None
    samples = []
    for index, video_frame in enumerate(probe.decode(video=0)):
        frame_rgb = video_frame.to_ndarray(format="rgb24")
        decoded += 1
        if previous is not None:
            if np.array_equal(previous, frame_rgb):
                identical_adjacent += 1
            frame_deltas.append(float(np.abs(frame_rgb.astype(np.int16) - previous.astype(np.int16)).mean()))
        if index % fps == 0:
            thumbnail = Image.fromarray(frame_rgb).convert("RGB")
            thumbnail.thumbnail((300, 180), Image.Resampling.LANCZOS)
            samples.append((index, thumbnail.copy()))
        previous = frame_rgb
    duration = float(video.duration * video.time_base) if video.duration is not None else None
    probe.close()
    # Contact sheet samples every second; all frames above were decoded and measured, not just these samples.
    columns, tile_w, tile_h = 5, 320, 220
    rows = max(1, math.ceil(len(samples) / columns))
    sheet = Image.new("RGB", (columns * tile_w, rows * tile_h), (20, 20, 20))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for sample_index, (frame_index, thumbnail) in enumerate(samples):
        x, y = (sample_index % columns) * tile_w, (sample_index // columns) * tile_h
        sheet.paste(thumbnail, (x + (tile_w-thumbnail.width)//2, y + 4))
        draw.text((x + 8, y + 188), f"frame {frame_index} / {frame_index / fps:.1f}s", fill="white")
    sheet.save(output_dir / "contact-sheet.jpg", quality=88)
    frame_visual_metrics = {
        "decoded_frames": decoded,
        "sampled_contact_sheet_frames": len(samples),
        "contact_sheet_interval_seconds": 1,
        "consecutive_identical_frames": identical_adjacent,
        "mean_adjacent_frame_mae_0_255": round(float(np.mean(frame_deltas)), 4) if frame_deltas else 0.0,
        "min_adjacent_frame_mae_0_255": round(float(np.min(frame_deltas)), 4) if frame_deltas else 0.0,
        "max_adjacent_frame_mae_0_255": round(float(np.max(frame_deltas)), 4) if frame_deltas else 0.0,
        "note": "All encoded frames were decoded and compared to the previous frame. MAE is a simple motion/change indicator, not a perceptual quality metric."
    }
    (output_dir / "visual_metrics.json").write_text(json.dumps(frame_visual_metrics, indent=2), encoding="utf-8")
    verify_seconds = time.perf_counter() - verify_started
    total_seconds = time.perf_counter() - generation_started
    if decoded != frames:
        raise RuntimeError(f"Encoded output verification failed: decoded {decoded}/{frames} frames")
    manifest = {
        "schema": 1, "mode": "SmartMotion 2.5D camera-only prototype", "created_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(input_image), "input_sha256": _sha256(input_image), "output": mp4.name,
        "width": width, "height": height, "fps": fps, "seconds_requested": seconds, "frames_decoded": decoded, "duration_seconds": duration,
        "source_transform": transform, "visual_metrics": frame_visual_metrics,
        "camera_motion": motion, "prompt_interpreted": False, "codec": "h264_nvenc", "encoder_options": encoder_options, "nvenc_verified": True,
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
                "<section><h2>Full-sequence review (one frame per second; all frames decoded)</h2><img src='contact-sheet.jpg'></section>"
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
    parser.add_argument("--output-size", type=str, default=None, help="Explicit WIDTHxHEIGHT output; center-crops to aspect then resizes without stretching (upscale is recorded)")
    parser.add_argument("--motion", choices=CAMERA_MOVES, default="push_in")
    args = parser.parse_args()
    output_size = parse_output_size(args.output_size) if args.output_size else None
    def report_progress(done: int, total: int, *, phase: str = "render") -> None:
        print(json.dumps({"event": "progress", "phase": phase, "frames_done": done, "frames_total": total}), flush=True)
    path = render(args.input, args.output_dir, args.depth_model, fps=args.fps, seconds=args.seconds, output_size=output_size, motion=args.motion, on_progress=report_progress)
    print(json.dumps({"event": "done", "video": str(path), "gallery": str(path.parent/"index.html"), "manifest": str(path.parent/"manifest.json")}), flush=True)


if __name__ == "__main__":
    main()
