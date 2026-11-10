"""Truthful readiness manifest for candidate video models (no weights loaded)."""
from __future__ import annotations

import os


def gpu_size_from_env() -> str:
    """Allow 48 GB default or explicit 96 GB ZeroGPU allocation."""
    value = os.environ.get("LAS_GPU_SIZE", "large").strip().lower()
    if value not in {"large", "xlarge"}:
        raise ValueError("LAS_GPU_SIZE must be 'large' (48 GB) or 'xlarge' (96 GB).")
    return value


CANDIDATES: tuple[dict[str, object], ...] = (
    {
        "id": "sana-video-2.0-5b-4step",
        "repository": "Efficient-Large-Model/SANA-Video_2.0_5B_720p_4step",
        "tasks": ["t2v"],
        "weights_license": "Apache-2.0",
        "status": "blocked_dependency_access",
        "blocking_dependency": "google/gemma-2-2b-it",
        "weights_loaded": False,
        "validated_on_this_space": False,
        "notes": "Distilled 4-step preview; model card explicitly says T2V-only.",
    },
    {
        "id": "sana-video-2.0-5b-base",
        "repository": "Efficient-Large-Model/SANA-Video_2.0_5B_720p",
        "tasks": ["t2v", "ti2v"],
        "weights_license": "Apache-2.0",
        "status": "not_selected",
        "blocking_dependency": "google/gemma-2-2b-it",
        "weights_loaded": False,
        "validated_on_this_space": False,
        "notes": "Base pipeline advertises T2V/TI2V; 50-step recipe, not benchmarked here.",
    },
)


def engine_status() -> dict[str, object]:
    return {
        "generation_ready": False,
        "supported_generation_tasks": [],
        "reason": (
            "No model is enabled. The preferred T2V candidate requires gated Gemma-2-2B access; "
            "the connected account currently receives 403 for that dependency."
        ),
        "candidates": [dict(candidate) for candidate in CANDIDATES],
        "paid_fallback_configured": False,
    }
