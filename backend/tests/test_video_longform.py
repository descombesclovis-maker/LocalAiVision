import json
from pathlib import Path

import pytest

from lib.video_longform import (
    build_wan_workflow,
    config_fingerprint,
    plan_segments,
    save_manifest,
    segment_is_resumable,
    _record_vram_sample,
    total_unique_frames,
)


def test_30s_at_3s_segments_is_10_chunks_with_one_shared_boundary():
    plan = plan_segments(30, 3, 100)
    assert len(plan) == 10
    assert [p.frame_count for p in plan] == [73] * 10
    assert [p.start_frame for p in plan] == [i * 72 for i in range(10)]
    assert total_unique_frames(30, 3) == 721
    assert total_unique_frames(30, 5) == 721


def test_plan_rejects_unaligned_duration_and_non_wan_segment_lengths():
    with pytest.raises(ValueError):
        plan_segments(29, 3)
    with pytest.raises(ValueError):
        plan_segments(30, 4)


def test_config_fingerprint_is_stable_and_sensitive_to_config():
    assert config_fingerprint({"seed": 7, "prompt": "x"}) == config_fingerprint({"prompt": "x", "seed": 7})
    assert config_fingerprint({"seed": 7}) != config_fingerprint({"seed": 8})


def test_resume_requires_success_and_matching_file_hashes(tmp_path: Path):
    video, frame = tmp_path / "segment-01.mp4", tmp_path / "segment-01-end.png"
    video.write_bytes(b"mp4")
    frame.write_bytes(b"png")
    from lib.video_longform import sha256_file
    manifest = {"segments": [{"status": "done", "video": video.name, "end_frame": frame.name,
                               "video_sha256": sha256_file(video), "end_frame_sha256": sha256_file(frame)}]}
    assert segment_is_resumable(manifest, 1, tmp_path)
    video.write_bytes(b"changed")
    assert not segment_is_resumable(manifest, 1, tmp_path)
    manifest["segments"][0]["status"] = "running"
    assert not segment_is_resumable(manifest, 1, tmp_path)


def test_vram_sampler_handles_initial_none_and_tracks_peak():
    live = {"vram_peak_mib": None}
    _record_vram_sample(live, 6000, 12288)
    _record_vram_sample(live, 7200, 12288)
    _record_vram_sample(live, 6500, 12288)
    assert live == {"vram_peak_mib": 7200, "vram_baseline_mib": 6000, "vram_total_mib": 12288}


def test_manifest_write_is_json_and_atomic(tmp_path: Path):
    path = tmp_path / "run" / "manifest.json"
    save_manifest(path, {"state": "running"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"state": "running"}
    assert not path.with_suffix(".json.tmp").exists()


def test_wan_workflow_chains_input_and_saves_last_frame():
    settings = {"video_preset": "wan21_fun_camera", "video_model": "wan.safetensors",
                "video_text_encoder": "umt5.safetensors", "video_vae": "wan.vae"}
    workflow = build_wan_workflow(settings, "same object", "source.png", 11)
    assert workflow["9"]["inputs"]["image"] == "source.png"
    assert workflow["11"]["inputs"]["length"] == 73
    assert workflow["12"]["inputs"]["seed"] == 11
    assert workflow["15"]["class_type"] == "SaveVideo"
    assert workflow["16"]["inputs"] == {"image": ["13", 0], "batch_index": 72, "length": 1}
    assert workflow["17"]["inputs"]["images"] == ["16", 0]


def test_longform_refuses_t2v_or_invalid_wan_frame_counts():
    settings = {"video_preset": "wan22", "video_model": "x", "video_text_encoder": "y", "video_vae": "z"}
    with pytest.raises(ValueError, match="only supports"):
        build_wan_workflow(settings, "p", "source.png", 1)
    settings["video_preset"] = "wan21_fun_camera"
    with pytest.raises(ValueError, match="input image"):
        build_wan_workflow(settings, "p", "", 1)
    with pytest.raises(ValueError, match=r"4n\+1"):
        build_wan_workflow(settings, "p", "source.png", 1, length=72)
