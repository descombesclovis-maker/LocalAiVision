"""Model capability/status registry for the private video Space."""
from __future__ import annotations

import os


def gpu_size_from_env() -> str:
    """Keep ZeroGPU's 48 GB allocation by default; 96 GB is explicit only."""
    value = os.environ.get("LAS_GPU_SIZE", "large").strip().lower()
    if value not in {"large", "xlarge"}:
        raise ValueError("LAS_GPU_SIZE must be 'large' (48 GB) or 'xlarge' (96 GB).")
    return value


SANA_T2V = {
    "id": "sana-video-2.0-5b-4step",
    "repository": "Efficient-Large-Model/SANA-Video_2.0_5B_720p_4step",
    "tasks": ["t2v"],
    "license": "Apache-2.0 checkpoint; Gemma and LTX VAE have separate terms",
    "resolution": "1280x736",
    "profiles": {"5 seconds": {"frames": 81, "fps": 16}, "8 seconds": {"frames": 193, "fps": 24}},
}

CANDIDATES: tuple[dict[str, object], ...] = (
    SANA_T2V,
    {
        "id": "sana-video-2.0-5b-base",
        "repository": "Efficient-Large-Model/SANA-Video_2.0_5B_720p",
        "tasks": ["t2v", "ti2v"],
        "license": "Apache-2.0 checkpoint; Gemma and LTX VAE have separate terms",
        "status": "not_loaded",
        "weights_loaded": False,
        "validated_on_this_space": False,
        "notes": "50-step model; not loaded alongside the 4-step checkpoint.",
    },
    {
        "id": "wan2.2-ti2v-5b",
        "repository": "Wan-AI/Wan2.2-TI2V-5B",
        "tasks": ["t2v", "i2v"],
        "license": "Apache-2.0",
        "status": "not_loaded",
        "weights_loaded": False,
        "validated_on_this_space": False,
        "notes": "Alternative candidate; no weights loaded or inference validated in this Space.",
    },
)


def engine_status(*, model_loaded: bool = False, load_error: str | None = None) -> dict[str, object]:
    """Return truthful readiness without disclosing secrets or exception payloads."""
    token_present = bool(os.environ.get("HF_TOKEN"))
    if model_loaded:
        reason = "SANA-Video 2.0 5B four-step T2V is loaded. I2V is not supported by this checkpoint."
    elif load_error:
        reason = f"Model startup failed ({load_error}); inspect Space logs for details."
    elif not token_present:
        reason = "Add a fine-grained, read-only HF_TOKEN Space secret with access to google/gemma-2-2b-it, then restart."
    else:
        reason = "Model weights are loading or unavailable; generation is not ready."

    candidates = []
    for item in CANDIDATES:
        candidate = dict(item)
        if candidate["id"] == SANA_T2V["id"]:
            candidate["status"] = "ready" if model_loaded else ("loading" if token_present and not load_error else "blocked_secret")
            candidate["weights_loaded"] = bool(model_loaded)
            candidate["validated_on_this_space"] = bool(model_loaded)
        candidates.append(candidate)

    return {
        "generation_ready": bool(model_loaded),
        "supported_generation_tasks": ["t2v"] if model_loaded else [],
        "selected_model": SANA_T2V["id"] if model_loaded else None,
        "reason": reason,
        "candidates": candidates,
        "gpu_size": gpu_size_from_env(),
        "quota_note": "ZeroGPU quota is account-level and remaining daily quota is not exposed by this endpoint.",
        "paid_fallback_configured": False,
    }
