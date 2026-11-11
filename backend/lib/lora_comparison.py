"""Deterministic cache identity and manifest format for controlled LoRA comparisons.

This module does not launch inference. Render tools can use its key so a completed
same-prompt/same-seed comparison is reused instead of generated on every catalogue open.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def comparison_identity(*, model: str, checkpoint: str, checkpoint_sha256: str | None,
                        prompt: str, seed: int, width: int, height: int, steps: int,
                        cfg: float, sampler: str, scheduler: str,
                        lora_filename: str, lora_sha256: str, lora_strength: float) -> dict[str, Any]:
    return {
        "model": model,
        "checkpoint": checkpoint,
        "checkpoint_sha256": checkpoint_sha256,
        "prompt": prompt,
        "seed": int(seed),
        "width": int(width),
        "height": int(height),
        "steps": int(steps),
        "cfg": float(cfg),
        "sampler": sampler,
        "scheduler": scheduler,
        "lora_filename": lora_filename,
        "lora_sha256": lora_sha256,
        "lora_strength": float(lora_strength),
    }


def comparison_cache_key(identity: dict[str, Any]) -> str:
    canonical = json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def comparison_cache_dir(root: str | Path, identity: dict[str, Any]) -> Path:
    return Path(root) / comparison_cache_key(identity)


def build_controlled_workflows(settings: dict[str, Any], *, prompt: str, seed: int,
                                width: int, height: int, lora_filename: str,
                                lora_strength: float) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build baseline/treatment workflows; only treatment gets LoraLoader."""
    from . import comfy

    baseline = comfy._image_workflow(settings, prompt, width, height, seed, None)
    treatment = comfy._image_workflow(settings, prompt, width, height, seed, None,
                                      lora_filename, lora_strength)
    def sampler(workflow: dict[str, Any]) -> dict[str, Any]:
        return next(node["inputs"] for node in workflow.values() if node["class_type"] == "KSampler")
    left, right = sampler(baseline), sampler(treatment)
    for field in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise", "latent_image", "positive", "negative"):
        if left[field] != right[field]:
            raise ValueError(f"Controlled comparison differs outside LoRA: {field}")
    if any(node["class_type"] == "LoraLoader" for node in baseline.values()):
        raise ValueError("Baseline must not contain a LoRA")
    if not any(node["class_type"] == "LoraLoader" for node in treatment.values()):
        raise ValueError("Treatment workflow must contain the selected LoRA")
    return baseline, treatment


def comparison_manifest(identity: dict[str, Any], *, baseline_file: str = "without_lora.png",
                        lora_file: str = "with_lora.png") -> dict[str, Any]:
    """Manifest contract: both outputs share every inference setting and prompt."""
    return {
        "schema_version": 1,
        "comparison_key": comparison_cache_key(identity),
        "identity": identity,
        "outputs": {
            "baseline": {"file": baseline_file, "lora": None},
            "treatment": {"file": lora_file, "lora": identity["lora_filename"],
                          "strength_model": identity["lora_strength"],
                          "strength_clip": identity["lora_strength"]},
        },
        "cache_policy": "reuse only when both files and this exact manifest identity are present",
        "visual_validation": "not_generated",
    }
