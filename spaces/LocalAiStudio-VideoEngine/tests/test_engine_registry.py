import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_registry import CANDIDATES, engine_status, gpu_size_from_env


def test_no_generation_claim_until_model_dependencies_are_available():
    status = engine_status()
    assert status["generation_ready"] is False
    assert status["supported_generation_tasks"] == []
    assert status["paid_fallback_configured"] is False
    assert "gated Gemma" in status["reason"]


def test_sana_candidate_capabilities_are_not_conflated():
    four_step, base = CANDIDATES
    assert four_step["tasks"] == ["t2v"]
    assert four_step["weights_loaded"] is False
    assert base["tasks"] == ["t2v", "ti2v"]
    assert base["status"] == "not_selected"


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
    result = engine_status()
    result["candidates"][0]["status"] = "mutated"
    assert CANDIDATES[0]["status"] == "blocked_dependency_access"
