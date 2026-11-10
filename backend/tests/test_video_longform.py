import json
from pathlib import Path

import pytest

from lib.video_longform import (
    build_wan_workflow,
    config_fingerprint,
    plan_segments,
    save_manifest,
    segment_is_resumable,
    extend_completed_manifest,
    _record_vram_sample,
    total_unique_frames,
    CAMERA_STRATEGIES,
    SubjectObservation,
    camera_pose_for_segment,
    _write_gallery,
    estimate_subject_hue,
    observe_subject,
    framing_risk,
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


def test_longform_plans_three_and_four_segments_with_continuous_frame_stride():
    nine = plan_segments(9, 3, 100)
    twelve = plan_segments(12, 3, 100)
    assert len(nine) == 3 and [s.start_frame for s in nine] == [0, 72, 144]
    assert len(twelve) == 4 and [s.start_frame for s in twelve] == [0, 72, 144, 216]
    assert [s.seed for s in twelve] == [100, 101, 102, 103]
    assert [s.unique_frames for s in twelve] == [73, 72, 72, 72]
    assert total_unique_frames(9, 3) == 217
    assert total_unique_frames(12, 3) == 289


def test_longform_target_duration_is_whitelisted_without_changing_default():
    from lib.video_longform import _supported_target_seconds

    assert _supported_target_seconds(6)
    assert _supported_target_seconds(9)
    assert _supported_target_seconds(12)
    assert not _supported_target_seconds(30)


def test_gallery_uses_duration_and_all_segment_outputs(tmp_path: Path):
    (tmp_path / "longform-9s.mp4").write_bytes(b"video")
    (tmp_path / "segment-01.mp4").write_bytes(b"s1")
    (tmp_path / "segment-02.mp4").write_bytes(b"s2")
    (tmp_path / "segment-03.mp4").write_bytes(b"s3")
    manifest = {
        "config": {"target_seconds": 9},
        "assembly": {"file": "longform-9s.mp4"},
        "segments": [{"index": i, "status": "done", "video": f"segment-{i:02d}.mp4", "end_frame": f"end-{i}.png"} for i in range(1, 4)],
    }
    _write_gallery(tmp_path, manifest)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "9-second continuity experiment" in html
    assert "longform-9s.mp4" in html
    assert html.count("<h2>Segment") == 3


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


def test_completed_run_can_extend_only_with_identical_settings_and_verified_segments(tmp_path: Path):
    from lib.video_longform import sha256_file

    rows = []
    for i in range(1, 4):
        video, frame = tmp_path / f"segment-{i:02d}.mp4", tmp_path / f"segment-{i:02d}-end.png"
        video.write_bytes(f"video{i}".encode())
        frame.write_bytes(f"frame{i}".encode())
        rows.append({"index": i, "status": "done", "video": video.name, "end_frame": frame.name,
                     "video_sha256": sha256_file(video), "end_frame_sha256": sha256_file(frame)})
    old = {"model": "wan", "target_seconds": 9, "segment_count": 3, "base_seed": 50, "prompt": "same"}
    manifest = {"config": old, "segments": rows, "assembly": {"file": "old.mp4"}}
    new = {**old, "target_seconds": 12, "segment_count": 4}
    assert extend_completed_manifest(manifest, new, tmp_path)
    assert [r["status"] for r in manifest["segments"]] == ["done", "done", "done", "pending"]
    assert manifest["extension_from_seconds"] == 9
    assert "assembly" not in manifest

    manifest = {"config": old, "segments": rows.copy()}
    assert not extend_completed_manifest(manifest, {**new, "prompt": "changed"}, tmp_path)


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


def test_neutral_bounded_and_keyframe_camera_policies():
    centered = SubjectObservation(170, (0.4, 0.2, 0.6, 0.8), 0.5, 0.5, 500)
    drifted_right = SubjectObservation(170, (0.72, 0.2, 0.99, 0.8), 0.855, 0.5, 500)
    assert camera_pose_for_segment("neutral", 1, "Pan Left") == "Static"
    assert camera_pose_for_segment("legacy", 2, "Pan Left", centered) == "Pan Left"
    assert camera_pose_for_segment("bounded", 1, "Pan Left") == "Pan Left"
    assert camera_pose_for_segment("bounded", 2, "Pan Left", drifted_right) == "Pan Right"
    assert camera_pose_for_segment("bounded", 2, "Pan Left", centered) == "Static"
    assert camera_pose_for_segment("keyframe", 2, "Pan Left", centered, ("Pan Left", "Zoom Out")) == "Zoom Out"
    assert camera_pose_for_segment("keyframe", 4, "Pan Left", centered, ("Pan Left", "Static")) == "Static"


def test_subject_color_guard_locates_reference_and_rejects_edge_drift(tmp_path: Path):
    from PIL import Image, ImageDraw

    reference = tmp_path / "reference.png"
    image = Image.new("RGB", (200, 200), (170, 170, 170))
    ImageDraw.Draw(image).rectangle((72, 66, 128, 154), fill=(5, 28, 220))
    image.save(reference)
    hue = estimate_subject_hue(reference, (0.30, 0.30, 0.40, 0.50))
    centered = observe_subject(reference, hue)
    assert centered is not None
    assert abs(centered.center_x - 0.5) < 0.02
    assert framing_risk(centered) is None

    shifted = tmp_path / "shifted.png"
    drift = Image.new("RGB", (200, 200), (170, 170, 170))
    ImageDraw.Draw(drift).rectangle((174, 66, 199, 154), fill=(5, 28, 220))
    drift.save(shifted)
    observation = observe_subject(shifted, hue)
    assert observation is not None
    assert framing_risk(observation) is not None
    assert framing_risk(None) == "subject color anchor not detected"


def test_wan_workflow_supports_persistent_reference_and_opt_in_kitchen_attention():
    settings = {"video_preset": "wan21_fun_camera", "video_model": "wan.safetensors",
                "video_text_encoder": "umt5.safetensors", "video_vae": "wan.vae"}
    workflow = build_wan_workflow(settings, "same object", "current.png", 11, "Pan Right",
                                  reference_image_name="initial.png", attention_backend="comfy kitchen attention")
    assert workflow["9"]["inputs"]["image"] == "current.png"
    assert workflow["18"]["inputs"]["image"] == "initial.png"
    assert workflow["10"]["inputs"]["image"] == ["18", 0]
    assert workflow["11"]["inputs"]["start_image"] == ["9", 0]
    assert workflow["19"]["class_type"] == "ModelAttentionBackend"
    assert workflow["19"]["inputs"]["attention"] == "comfy kitchen attention"
    assert workflow["4"]["inputs"]["model"] == ["19", 0]

    default_workflow = build_wan_workflow(settings, "same object", "current.png", 11)
    assert default_workflow["4"]["inputs"]["model"] == ["1", 0]
    assert "19" not in default_workflow


def test_attention_backend_rejects_unknown_value():
    settings = {"video_preset": "wan21_fun_camera", "video_model": "wan.safetensors",
                "video_text_encoder": "umt5.safetensors", "video_vae": "wan.vae"}
    with pytest.raises(ValueError, match="Unsupported attention backend"):
        build_wan_workflow(settings, "p", "source.png", 1, attention_backend="unverified")


def test_camera_strategy_names_are_experimental_and_explicit():
    assert CAMERA_STRATEGIES == ("legacy", "neutral", "bounded", "keyframe")
    with pytest.raises(ValueError, match="Unsupported camera strategy"):
        camera_pose_for_segment("automatic_magic", 1, "Pan Left")


def test_subject_roi_rejects_out_of_frame_values():
    from lib.video_longform import _validate_roi

    with pytest.raises(ValueError, match="normalized"):
        _validate_roi((0.9, 0.1, 0.2, 0.2))
