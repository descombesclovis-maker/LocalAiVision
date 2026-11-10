import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_registry import CANDIDATES, engine_status, gpu_size_from_env


def test_generation_is_not_claimed_without_loaded_model_or_secret(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    status = engine_status()
    assert status["generation_ready"] is False
    assert status["supported_generation_tasks"] == []
    assert "fine-grained" in status["reason"]
    assert status["paid_fallback_configured"] is False


def test_sana_checkpoint_is_distilled_t2v_only():
    four_step, base, wan = CANDIDATES
    assert four_step["tasks"] == ["t2v"]
    assert four_step["repository"].endswith("_4step")
    assert base["tasks"] == ["t2v", "ti2v"]
    assert base["status"] == "not_loaded"
    assert wan["tasks"] == ["t2v", "i2v"]
    assert wan["status"] == "not_loaded"


def test_loaded_status_exposes_only_validated_t2v(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "test-secret-not-used")
    status = engine_status(model_loaded=True)
    assert status["generation_ready"] is True
    assert status["supported_generation_tasks"] == ["t2v"]
    assert status["selected_model"] == "sana-video-2.0-5b-4step"
    assert "test-secret-not-used" not in repr(status)
    assert status["candidates"][0]["validated_on_this_space"] is True


def test_load_failure_does_not_report_readiness(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "test-secret-not-used")
    status = engine_status(load_error="RuntimeError")
    assert status["generation_ready"] is False
    assert status["supported_generation_tasks"] == []
    assert "RuntimeError" in status["reason"]
    assert "test-secret-not-used" not in repr(status)


def test_gpu_size_defaults_to_48gb_and_allows_explicit_96gb(monkeypatch):
    monkeypatch.delenv("LAS_GPU_SIZE", raising=False)
    assert gpu_size_from_env() == "large"
    monkeypatch.setenv("LAS_GPU_SIZE", "xlarge")
    assert gpu_size_from_env() == "xlarge"
    monkeypatch.setenv("LAS_GPU_SIZE", "paid-gpu")
    try:
        gpu_size_from_env()
    except ValueError as exc:
        assert "LAS_GPU_SIZE" in str(exc)
    else:
        raise AssertionError("unsupported GPU size should fail closed")


def test_engine_status_returns_detached_data():
    first = engine_status()
    first["candidates"][0]["status"] = "mutated"
    assert CANDIDATES[0].get("status") is None
