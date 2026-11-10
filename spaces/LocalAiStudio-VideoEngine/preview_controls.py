"""Pure input-contract helpers for the SANA-Video 2.0 preview Space."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# The published full checkpoint is the immutable scale=1 reference. The Space
# deliberately exposes only the validated preview interval at 0.1 increments.
REFERENCE_RL_LORA_SCALE = 1.0
DEFAULT_RL_LORA_SCALE = 0.7
MIN_RL_LORA_SCALE = 0.3
MAX_RL_LORA_SCALE = 1.0
RL_LORA_SCALE_STEP = 0.1

DEFAULT_MOTION_SCORE = 20
MIN_MOTION_SCORE = 0
MAX_MOTION_SCORE = 100


@dataclass(frozen=True)
class VideoProfile:
    """A release-validated temporal bucket and its playback rate."""

    num_frames: int
    fps: int

    @property
    def duration_seconds(self) -> float:
        return (self.num_frames - 1) / self.fps


VIDEO_DURATION_5_SECONDS = "5 seconds"
VIDEO_DURATION_8_SECONDS = "8 seconds"
DEFAULT_VIDEO_DURATION = VIDEO_DURATION_5_SECONDS
VIDEO_PROFILES = {
    VIDEO_DURATION_5_SECONDS: VideoProfile(num_frames=81, fps=16),
    VIDEO_DURATION_8_SECONDS: VideoProfile(num_frames=193, fps=24),
}

MOTION_SUFFIX_RE = re.compile(r"\s+motion\s+score\s*:\s*\d+\.?\s*$", flags=re.IGNORECASE)


def get_video_profile(value: str) -> VideoProfile:
    """Resolve one of the two release-validated duration choices."""
    try:
        return VIDEO_PROFILES[value]
    except (KeyError, TypeError) as exc:
        choices = ", ".join(VIDEO_PROFILES)
        raise ValueError(f"Video duration must be one of: {choices}.") from exc


def normalize_lora_scale(value: int | float) -> float:
    """Validate the public 0.3–1.0 scale contract at 0.1 increments."""
    scale = float(value)
    if not math.isfinite(scale) or not MIN_RL_LORA_SCALE <= scale <= MAX_RL_LORA_SCALE:
        raise ValueError(f"RL LoRA scale must be between {MIN_RL_LORA_SCALE:.1f} " f"and {MAX_RL_LORA_SCALE:.1f}.")
    quantized = round(scale / RL_LORA_SCALE_STEP) * RL_LORA_SCALE_STEP
    if not math.isclose(scale, quantized, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"RL LoRA scale must use {RL_LORA_SCALE_STEP:.1f} increments.")
    return round(quantized, 1)


def lora_adjustment_coefficient(value: int | float, intrinsic_scaling: float) -> float:
    """Return the LoRA BA coefficient relative to the scale-1 full model."""
    scale = normalize_lora_scale(value)
    return (scale - REFERENCE_RL_LORA_SCALE) * float(intrinsic_scaling)


def normalize_motion_score(value: int | float) -> int:
    """Validate the integer motion score used by the prompt suffix."""
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Motion score must be an integer from {MIN_MOTION_SCORE} to {MAX_MOTION_SCORE}.")
    score = int(numeric)
    if numeric != score or not MIN_MOTION_SCORE <= score <= MAX_MOTION_SCORE:
        raise ValueError(f"Motion score must be an integer from {MIN_MOTION_SCORE} to {MAX_MOTION_SCORE}.")
    return score


def motion_suffix(score: int | float) -> str:
    """Return the exact prompt suffix used by SANA-Video motion conditioning."""
    value = normalize_motion_score(score)
    return f" motion score: {value}." if value > 0 else ""


def normalize_base_prompt(prompt: str) -> str:
    """Strip existing trailing motion suffixes so the UI appends exactly one."""
    cleaned = prompt.strip()
    while MOTION_SUFFIX_RE.search(cleaned):
        cleaned = MOTION_SUFFIX_RE.sub("", cleaned).rstrip()
    return cleaned
