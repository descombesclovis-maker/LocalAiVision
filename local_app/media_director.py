"""Model-aware production settings from natural French/English creative briefs.

No imaginary ETA, no hidden quality downgrades, no prompt censoring.
ComfyUI workflow metadata stays authoritative for parameters we cannot infer.
An explicit user preference in the prompt takes priority over stale UI settings.
"""
import math
import re
from typing import Any

_DURATION=re.compile(r"\b(\d{1,3}(?:[,.]\d+)?)\s*(?:secondes?|seconds?|secs?|s)\b",re.I)
_FPS=re.compile(r"\b(\d{1,3})\s*(?:fps|images?\s+par\s+seconde|frames?\s+per\s+second)\b",re.I)
_STEPS=re.compile(r"\b(\d{1,3})\s*(?:[ée]tapes?|steps?)\b",re.I)
_FAST=re.compile(r"\b(?:rapide|vite|express|brouillon|draft|fast|quick|acceler[ée]e?)\b",re.I)
_PREMIUM=re.compile(r"\b(?:photo\s*r[ée]aliste|ultra\s*r[ée]aliste|photorealiste|photor[ée]aliste|cin[ée]matographique|haute\s+qualit[ée]|high\s+quality|4k|premium|d[ée]taill[ée])\b",re.I)
_ASPECTS=(("4:3",re.compile(r"\b4:3\b",re.I)),
          ("3:4",re.compile(r"\b3:4\b",re.I)),
          ("9:16",re.compile(r"\b(?:vertical|portrait|story|stories|reels?|tiktok|9:16)\b",re.I)),
          ("16:9",re.compile(r"\b(?:horizontal|paysage|youtube|panoramique|16:9)\b",re.I)),
          ("1:1",re.compile(r"\b(?:carr[ée]|square|1:1)\b",re.I)))

def plan(prompt: str, workflow_kind: str, current: dict[str,Any] | None = None)->dict[str,Any]:
    """Return normalized ComfyUI controls without modifying the submitted text.

    Tuned to the user's common 12-GB GPU (not a guarantee of performance).
    Video 10 seconds at 12 FPS = ~121 latent frames, which remains expensive.
    Explicit requested FPS/duration are respected if within reasonable limits.
    """
    settings=dict(current or {})
    text=str(prompt or "")
    is_video=workflow_kind in ("wan","hunyuan15","hunyuan15-i2v-step",
                                "omniweaving-t2v","omniweaving-i2v")
    is_image=workflow_kind in ("sdxl","hunyuanimage21")
    fast=bool(_FAST.search(text))
    premium=bool(_PREMIUM.search(text))
    if not (is_video or is_image):
        return settings
    if fast and not premium: quality="draft"
    elif premium: quality="quality"
    else: quality="balanced"
    # Never treat a stale visible dropdown as the user's instruction.
    if fast or premium or settings.get("quality") in (None,"","workflow"):
        settings["quality"]=quality
    quality=settings["quality"]
    requested_aspect=next((aspect for aspect,matcher in _ASPECTS if matcher.search(text)),None)
    if requested_aspect:
        settings["aspect"]=requested_aspect
    if is_video:
        duration=_DURATION.search(text)
        if duration:
            value=float(duration.group(1).replace(",","."))
            if 0.2<=value<=60:
                settings["duration"]=value
        fps=_FPS.search(text)
        if fps:
            value=int(fps.group(1))
            if 1<=value<=60:
                settings["fps"]=value
        if settings.get("fps") is None:
            settings["fps"]=8 if quality=="draft" else 16 if quality=="quality" else 12
        if settings.get("steps") is None:
            # Distilled models have far lower optimal steps; preserve their
            # workflow sampler steps instead of forcing 16-24 slow steps.
            if workflow_kind not in ("hunyuan15-i2v-step", "hunyuan15"):
                settings["steps"]=12 if quality=="draft" else 24 if quality=="quality" else 18
        if not settings.get("width") and not settings.get("height") and settings.get("aspect") in ("auto",None,""):
            settings["aspect"]="16:9"
        if not settings.get("width") and not settings.get("height"):
            if workflow_kind in ("hunyuan15", "hunyuan15-i2v-step") and quality!="draft":
                # Keep native 480p on HunyuanVideo 1.5, not a hidden 360p fallback.
                size=(832,480)
            else:
                size=(512,288) if quality=="draft" else (832,480) if quality=="quality" else (640,360)
            # Orientation is handled below; the workflow adapter will preserve
            # a model-specific aspect where supported.
            if settings.get("aspect")=="9:16":
                size=size[::-1]
            aspect=settings.get("aspect")
            if aspect in ("16:9","9:16"):
                settings["width"],settings["height"]=size
            elif aspect in ("1:1","4:3","3:4"):
                ratios={"1:1":1.0,"4:3":4/3,"3:4":3/4}
                area=size[0]*size[1]
                w=max(256,round(math.sqrt(area*ratios[aspect])/32)*32)
                h=max(256,round(math.sqrt(area/ratios[aspect])/32)*32)
                settings["width"],settings["height"]=w,h
    else:
        if workflow_kind=="hunyuanimage21" and not settings.get("width") and not settings.get("height"):
            # Running 2048² by default on 12 GB can thrash or OOM; keep
            # optional quality mode at higher resolution for capable setups.
            side=1024 if quality=="draft" else 1536 if quality=="quality" else 1280
            aspect=settings.get("aspect")
            if aspect in ("auto",None,"","1:1"):
                settings["width"]=settings["height"]=side
            elif aspect in ("16:9","9:16","4:3","3:4"):
                # Keep the 12-GB pixel budget close to square presets.
                # The imported workflow's huge landscape defaults are not
                # safe on every RTX 3060, particularly for portrait renders.
                ratios={"16:9":16/9,"9:16":9/16,"4:3":4/3,"3:4":3/4}
                ratio=ratios[aspect]
                settings["width"]=max(256,round(side*math.sqrt(ratio)/32)*32)
                settings["height"]=max(256,round(side/math.sqrt(ratio)/32)*32)
    steps=_STEPS.search(text)
    if steps and 1<=int(steps.group(1))<=100:
        settings["steps"]=int(steps.group(1))
    return settings

VIDEO_MOTION_HINT = (
    "Temporal quality only: maintain the same subject identity, face, clothing and "
    "body proportions across consecutive frames. Smooth physically plausible "
    "movement, stable lighting and camera, natural motion blur, realistic "
    "textures and consistent background geometry, avoid jerky camera motion."
)
VIDEO_NEGATIVE_HINT = (
    "temporal flicker, frame jitter, face drift, warped limbs, ghosting, "
    "melting textures, frame inconsistency, excessive camera shake, "
    "motion artifacts, blocky compression, artificial plastic skin"
)

def enhance_video_continuity(prompt: str, negative: str | None, kind: str, technical_quality=True):
    """Quality-only camera/temporal advice that cannot change the user's scene."""
    if not technical_quality or kind not in ("wan","hunyuan15","hunyuan15-i2v-step",
                                            "omniweaving-t2v","omniweaving-i2v"):
        return prompt,negative
    original=str(prompt or "").strip()
    result=original if VIDEO_MOTION_HINT in original else original+"\n\n"+VIDEO_MOTION_HINT
    original_negative=str(negative or "").strip()
    neg=original_negative if VIDEO_NEGATIVE_HINT in original_negative else (original_negative+", "+VIDEO_NEGATIVE_HINT).strip(", ")
    return result,neg
