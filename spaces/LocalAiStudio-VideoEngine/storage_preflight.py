"""Disk-space guard for remotely cached SANA dependencies; performs no downloads."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

# Hub metadata, bytes: SANA 4-step checkpoint, RL scale adapter, LTX VAE, Gemma-2-2B.
MODEL_ARTIFACT_BYTES = 17_871_905_340 + 587_418_315 + 1_452_233_194 + 5_250_587_389
# Reserve room for extracted/runtime files and prevent starting with a marginal cache.
MIN_FREE_BYTES = 30 * 1024**3


def storage_report(cache_home: str | Path | None = None) -> dict[str, object]:
    configured = Path(cache_home or os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    probe = configured
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    usage = shutil.disk_usage(probe)
    free = int(usage.free)
    return {
        "free_bytes": free,
        "free_gib": round(free / 1024**3, 2),
        "required_artifact_bytes": MODEL_ARTIFACT_BYTES,
        "required_artifacts_gib": round(MODEL_ARTIFACT_BYTES / 1024**3, 2),
        "minimum_safe_free_gib": round(MIN_FREE_BYTES / 1024**3, 2),
        "sufficient": free >= MIN_FREE_BYTES,
    }
