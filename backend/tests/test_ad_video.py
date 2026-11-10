from pathlib import Path

import pytest

pytest.importorskip("numpy")
av = pytest.importorskip("av")
PIL = pytest.importorskip("PIL.Image")
import numpy as np

from lib.ad_video import assemble


def _make_clip(path: Path, colors: list[tuple[int, int, int]], fps: int = 4) -> None:
    container = av.open(str(path), "w", format="mp4")
    stream = container.add_stream("libx264", rate=fps)
    stream.width, stream.height, stream.pix_fmt = 64, 48, "yuv420p"
    for index, color in enumerate(colors):
        frame = av.VideoFrame.from_ndarray(np.full((48, 64, 3), color, dtype=np.uint8), format="rgb24")
        frame.pts = index
        from fractions import Fraction
        frame.time_base = Fraction(1, fps)
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()


def test_ad_assembler_composes_overlay_cuts_two_real_clips_and_verifies_output(tmp_path: Path):
    first, second = tmp_path / "first.mp4", tmp_path / "second.mp4"
    _make_clip(first, [(220, 10, 10)] * 3)
    _make_clip(second, [(10, 20, 220)] * 2)
    overlay = PIL.new("RGBA", (64, 48), (0, 0, 0, 0))
    overlay.putpixel((2, 2), (10, 240, 20, 255))
    overlay_path = tmp_path / "overlay.png"
    overlay.save(overlay_path)
    output = tmp_path / "ad.mp4"

    report = assemble([first, second], overlay_path, output, fps=4)

    assert report["verification"].startswith("all output frames decoded")
    assert report["transition"] == "hard_cut"
    assert report["audio"] == "omitted"
    assert report["segments"] == 2 and report["frames"] == 5
    assert report["width"] == 64 and report["height"] == 48
    assert output.is_file() and output.stat().st_size > 500
    with av.open(str(output)) as result:
        frames = list(result.decode(video=0))
    assert len(frames) == 5
    assert (tmp_path / "ad.json").is_file()


def test_ad_assembler_rejects_empty_clip_set(tmp_path: Path):
    overlay = tmp_path / "overlay.png"
    PIL.new("RGBA", (64, 48), (0, 0, 0, 0)).save(overlay)
    with pytest.raises(ValueError, match="one to eight"):
        assemble([], overlay, tmp_path / "empty.mp4")
