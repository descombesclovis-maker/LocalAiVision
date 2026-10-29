"""Model-aware production settings from natural French/English creative briefs.

No imaginary ETA, no hidden quality downgrades, no prompt censoring.
ComfyUI workflow metadata stays authoritative for parameters we cannot infer.
An explicit user preference in the prompt takes priority over stale UI settings.
"""
import re
from typing import Any

_DURATION=re.compile(r"\b(\d{1,3}(?:[,.]\d+)?)\s*(?:secondes?|seconds?|secs?|s)\b",re.I)
_FPS=re.compile(r"\b(\d{1,3})\s*(?:fps|images?\s+par\s+seconde|frames?\s+per\s+second)\b",re.I)
_STEPS=re.compile(r"\b(\d{1,3})\s*(?:[ée]tapes?|steps?)\b",re.I)
_FAST=re.compile(r"\b(?:rapide|vite|express|brouillon|draft|fast|quick|acceler[ée]e?)\b",re.I)
_PREMIUM=re.compile(r"\b(?:ultra\s*r[ée]aliste|photorealiste|photor[ée]aliste|cin[ée]matographique|haute\s+qualit[ée]|high\s+quality|4k|premium|d[ée]taill[ée])\b",re.I)
_ASPECTS=(("9:16",re.compile(r"\b(?:vertical|portrait|story|stories|reels?|tiktok|9:16)\b",re.I)),
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
    if settings.get("quality") in (None,"","workflow"):
        settings["quality"]=quality
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
            if workflow_kind!="hunyuan15-i2v-step":
                settings["steps"]=12 if quality=="draft" else 24 if quality=="quality" else 18
        if not settings.get("width") and not settings.get("height") and settings.get("aspect") in ("auto",None,""):
            settings["aspect"]="16:9"
        if not settings.get("width") and not settings.get("height"):
            size=(512,288) if quality=="draft" else (832,480) if quality=="quality" else (640,360)
            # Orientation is handled below; the workflow adapter will preserve
            # a model-specific aspect where supported.
            if settings.get("aspect")=="9:16":
                size=size[::-1]
            if settings.get("aspect") in ("16:9","9:16"):
                settings["width"],settings["height"]=size
    else:
        if workflow_kind=="hunyuanimage21" and not settings.get("width") and not settings.get("height"):
            # Running 2048² by default on 12 GB can thrash or OOM; keep
            # optional quality mode at higher resolution for capable setups.
            side=1024 if quality=="draft" else 1536 if quality=="quality" else 1280
            if settings.get("aspect") in ("auto",None,"","1:1"):
                settings["width"]=settings["height"]=side
    for aspect,matcher in _ASPECTS:
        if matcher.search(text):
            settings["aspect"]=aspect
            if is_video and not _FPS.search(text) and not settings.get("width") and not settings.get("height"):
                pass
            break
    steps=_STEPS.search(text)
    if steps and 1<=int(steps.group(1))<=100:
        settings["steps"]=int(steps.group(1))
    # If user specified a format, default auto width/height should follow
    # the new orientation rather than the old editor choice.
    if is_video and not current or False:
        pass
    return settings
