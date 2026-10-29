"""Isolated adult-oriented visual profile; prompt fidelity over generic tags.

The previous default prefixed every prompt with generic sexualized descriptors,
unrequested appearance, and conflicting camera cues. This made ordinary
adult scenes incoherent and frequently impaired animation consistency.
"""
IMAGE_WORKFLOW = "NSFW Image.json"
VIDEO_WORKFLOW = "NSFW Video.json"

TECHNICAL_QUALITY = (
    "Natural coherent anatomy, anatomically correct hands and feet, precise "
    "proportions, consistent identity, realistic skin texture, realistic "
    "lighting, natural shadows, optical detail, no flicker or deformation."
)
DEFAULT_NEGATIVE = (
    "lowres, blurry, compression artifacts, watermark, unwanted text, "
    "malformed hands, fused fingers, extra limbs, duplicate limbs, "
    "warped anatomy, jitter, temporal flicker, inconsistent identity, "
    "unnatural poses, over-smoothed skin, artificial plastic textures"
)

def prepare_visual_request(
    prompt,
    selected_style="none",
    negative=None,
    technical_quality=True,
):
    """Keep the original user's composition and clothing instructions intact."""
    raw=str(prompt or "").strip()
    prepared=raw
    if technical_quality:
        prepared+="\n\nRendering quality only: "+TECHNICAL_QUALITY
    neg=negative
    if technical_quality and not str(negative or "").strip():
        neg=DEFAULT_NEGATIVE
    return prepared,neg,None
