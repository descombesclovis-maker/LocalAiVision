"""Local PyAV assembler used by the experimental LongForm prototype; run with ComfyUI's Python."""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw


def main() -> None:
    if len(sys.argv) < 6:
        raise SystemExit("usage: longform_assemble_av.py OUTPUT.mp4 REPORT.json TARGET_FRAMES SEGMENT1.mp4 SEGMENT2.mp4 [...]")
    output, report_path = Path(sys.argv[1]), Path(sys.argv[2])
    target_frames = int(sys.argv[3])
    segments = [Path(x) for x in sys.argv[4:]]
    fps = 24
    output.parent.mkdir(parents=True, exist_ok=True)
    container_out = av.open(str(output), mode="w", format="mp4")
    stream = container_out.add_stream("libx264", rate=fps)
    stream.width, stream.height = 832, 480
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "18", "preset": "medium"}
    stream.time_base = Fraction(1, fps)
    counts: list[int] = []
    samples: dict[tuple[int, int], Image.Image] = {}
    previous_last = None
    boundary_maes: list[float] = []
    within_diffs: list[float] = []
    out_index = 0
    try:
        for seg_i, segment in enumerate(segments):
            count = 0
            prev = None
            with av.open(str(segment), mode="r") as source:
                video = source.streams.video[0]
                for local_i, frame in enumerate(source.decode(video=0)):
                    count += 1
                    arr = frame.to_ndarray(format="rgb24")
                    samples[(seg_i, local_i)] = Image.fromarray(arr).resize((160, 90))
                    if prev is not None:
                        within_diffs.append(float(np.abs(arr.astype(np.int16) - prev.astype(np.int16)).mean()))
                    if seg_i > 0 and local_i == 1 and previous_last is not None:
                        boundary_maes.append(float(np.abs(arr.astype(np.int16) - previous_last.astype(np.int16)).mean()))
                    if local_i == count - 1:
                        previous_last = arr.copy()
                    prev = arr
                    if seg_i > 0 and local_i == 0:
                        continue  # one shared boundary keyframe; don't encode it twice
                    if out_index >= target_frames:
                        continue  # trim the endpoint sample so six seconds is exactly 144 frames at 24 fps
                    video_frame = av.VideoFrame.from_ndarray(arr, format="rgb24").reformat(format="yuv420p")
                    video_frame.pts = out_index
                    video_frame.time_base = Fraction(1, fps)
                    for packet in stream.encode(video_frame):
                        container_out.mux(packet)
                    out_index += 1
            counts.append(count)
        for packet in stream.encode():
            container_out.mux(packet)
    finally:
        container_out.close()
    # Decode the assembled output to independently verify frame count/fps/dimensions.
    with av.open(str(output), mode="r") as check:
        out_stream = check.streams.video[0]
        decoded = sum(1 for _ in check.decode(video=0))
        width, height = out_stream.width, out_stream.height
        rate = float(out_stream.average_rate or fps)
    # Local contact sheet samples the full temporal span of both segments.
    tiles = [(seg_i, frame_i, image) for (seg_i, frame_i), image in sorted(samples.items())]
    columns, tile_w, tile_h, label_h = 8, 160, 90, 18
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_w, max(1, rows) * (tile_h + label_h)), "#171717")
    draw = ImageDraw.Draw(sheet)
    for i, (seg_i, frame_i, image) in enumerate(tiles):
        x, y = (i % columns) * tile_w, (i // columns) * (tile_h + label_h)
        sheet.paste(image, (x, y + label_h))
        draw.text((x + 3, y + 2), f"S{seg_i + 1} F{frame_i:02d}", fill="white")
    sheet.save(output.parent / "continuity-contact.jpg", quality=90)
    report = {
        "source_frames_per_segment": counts,
        "shared_boundary_frames_removed": max(0, len(segments) - 1),
        "output_frames": decoded,
        "target_frames": target_frames,
        "fps": rate,
        "duration_seconds": decoded / rate,
        "width": width,
        "height": height,
        "boundary_mae_rgb_0_255": boundary_maes[0] if boundary_maes else None,
        "boundary_maes_rgb_0_255": boundary_maes,
        "mean_intra_segment_adjacent_frame_mae_rgb_0_255": float(np.mean(within_diffs)) if within_diffs else None,
        "note": "Boundary pixel differences are listed in segment order; pixel differences are descriptive only, not perceptual quality scores.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
