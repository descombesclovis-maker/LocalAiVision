"""Isolated adult/NSFW workspace configuration.

This module is deliberately separate from the normal RealVisXL/Animagine/Wan
profiles so experiments here cannot change the other profiles. It contains no
content-bypass logic; it only owns this workspace's independent workflow names
and neutral rendering-quality defaults.
"""

IMAGE_WORKFLOW = "NSFW Image.json"
VIDEO_WORKFLOW = "NSFW Video.json"

# These are the ONLY automatic text additions for this isolated workspace.
# Keep them technical if you want the user's semantic request to remain intact.
TECHNICAL_QUALITY = (
    "high detail, coherent anatomy, accurate hands, clean edges, sharp focus, "
    "consistent shapes, realistic texture, natural lighting, low artifacts"
)
DEFAULT_NEGATIVE = (
    "lowres, blurry, compression artifacts, watermark, unwanted text, "
    "malformed hands, fused fingers, extra fingers, missing fingers, extra limbs, "
    "duplicate limbs, broken anatomy, rendering artifacts"
)


def prepare_visual_request(prompt, selected_style="none", negative=None, technical_quality=True):
    """Prepare a request for the isolated workspace without rewriting semantics."""
    raw = (prompt or "").strip()
    prepared = raw
    if technical_quality:
        prepared += "\n\nTechnical quality only: " + TECHNICAL_QUALITY + "."
    neg = negative
    if technical_quality and not (negative or "").strip():
        neg = DEFAULT_NEGATIVE
    # Style is intentionally not injected here; the dedicated workflow can be
    # edited independently without affecting normal profiles.
    return prepared, neg, None
