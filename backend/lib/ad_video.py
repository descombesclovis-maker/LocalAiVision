"""Assemble real video clips into an MP4 campaign with a PNG logo/text overlay.

This keeps hard cuts between clips (no continuity or generated transitions are claimed).
Audio is intentionally omitted so different source tracks cannot be silently mixed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _cover_rgb(frame: Any, width: int, height: int):
    """Center-crop an RGB ndarray to the output frame while preserving its aspect ratio."""
    import numpy as np

    source_h, source_w = frame.shape[:2]
    scale = max(width / source_w, height / source_h)
    resized_w, resized_h = round(source_w * scale), round(source_h * scale)
    pil_module = __import__("PIL.Image", fromlist=["Image"])
    pil = pil_module.fromarray(frame).resize((resized_w, resized_h), pil_module.Resampling.LANCZOS)
    left, top = (resized_w - width) // 2, (resized_h - height) // 2
    return np.asarray(pil.crop((left, top, left + width, top + height)).convert("RGB"))


def _emit(stream: Any, container: Any, frame_rgb: Any, overlay: Any, width: int, height: int, frame_index: int, fps: int) -> None:
    import av
    from PIL import Image

    rgb = _cover_rgb(frame_rgb, width, height)
    composed = Image.alpha_composite(Image.fromarray(rgb).convert("RGBA"), overlay)
    video_frame = av.VideoFrame.from_ndarray(__import__("numpy").asarray(composed.convert("RGB")), format="rgb24")
    video_frame.pts = frame_index
    from fractions import Fraction
    video_frame.time_base = Fraction(1, fps)
    for packet in stream.encode(video_frame):
        container.mux(packet)


def assemble(clips: list[Path], overlay_path: Path, output: Path, fps: int = 24) -> dict[str, Any]:
    import av
    import numpy as np
    from PIL import Image

    if not clips or len(clips) > 8:
        raise ValueError("Select one to eight video clips")
    overlay = Image.open(overlay_path).convert("RGBA")
    width, height = overlay.size
    if width < 2 or height < 2 or width % 2 or height % 2:
        raise ValueError("Overlay dimensions must be positive even numbers")
    output.parent.mkdir(parents=True, exist_ok=True)
    container_out = av.open(str(output), mode="w", format="mp4")
    stream = container_out.add_stream("libx264", rate=fps)
    stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
    stream.options = {"crf": "18", "preset": "medium"}
    output_index = 0
    segment_frames: list[int] = []
    total_source_frames = 0
    try:
        for clip in clips:
            with av.open(str(clip), mode="r") as source:
                if not source.streams.video:
                    raise ValueError(f"No video stream in {clip.name}")
                video = source.streams.video[0]
                source_rate = float(video.average_rate or fps)
                decoded = 0
                previous = None
                previous_time = 0.0
                first_time = None
                last_time = 0.0
                next_tick = 0
                for frame in source.decode(video=0):
                    timestamp = float(frame.time) if frame.time is not None else decoded / source_rate
                    if first_time is None:
                        first_time = timestamp
                    timestamp -= first_time
                    current = frame.to_ndarray(format="rgb24")
                    decoded += 1
                    while next_tick / fps <= timestamp:
                        tick = next_tick / fps
                        chosen = previous if previous is not None and abs(tick - previous_time) <= abs(timestamp - tick) else current
                        _emit(stream, container_out, chosen, overlay, width, height, output_index, fps)
                        output_index += 1
                        next_tick += 1
                    previous, previous_time = current, timestamp
                    last_time = timestamp
                if decoded == 0 or previous is None:
                    raise ValueError(f"No decodable video frames in {clip.name}")
                duration = float(source.duration / av.time_base) if source.duration else last_time + 1 / source_rate
                if video.start_time is not None:
                    duration = max(duration - float(video.start_time * video.time_base), 1 / source_rate)
                target_frames = max(1, round(duration * fps))
                while next_tick < target_frames:
                    _emit(stream, container_out, previous, overlay, width, height, output_index, fps)
                    output_index += 1
                    next_tick += 1
                segment_frames.append(next_tick)
                total_source_frames += decoded
        for packet in stream.encode():
            container_out.mux(packet)
    finally:
        container_out.close()

    # Decode the complete result before reporting success.
    with av.open(str(output), mode="r") as check:
        result_stream = check.streams.video[0]
        decoded_out = sum(1 for _ in check.decode(video=0))
        output_width, output_height = result_stream.width, result_stream.height
        output_fps = float(result_stream.average_rate or fps)
        codec = result_stream.codec_context.name
    if decoded_out != output_index or output_width != width or output_height != height:
        raise RuntimeError("The exported MP4 did not pass full decode/dimension verification")
    report = {
        "codec": codec,
        "width": output_width,
        "height": output_height,
        "fps": output_fps,
        "frames": decoded_out,
        "duration_seconds": round(decoded_out / output_fps, 3),
        "source_frames_decoded": total_source_frames,
        "segments": len(clips),
        "segment_output_frames": segment_frames,
        "transition": "hard_cut",
        "audio": "omitted",
        "overlay": "PNG composited over every output frame",
        "verification": "all output frames decoded; MP4 dimensions and frame count checked",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clips", nargs="+", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    result = assemble(args.clips, args.overlay, args.output, args.fps)
    print(json.dumps({"event": "progress", "phase": "verification", "frames_done": result["frames"], "frames_total": result["frames"]}), flush=True)
    print(json.dumps({"event": "done", "report": result}), flush=True)


if __name__ == "__main__":
    main()
