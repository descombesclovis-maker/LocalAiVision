IMAGE_WORKFLOW = "NSFW Image.json"
VIDEO_WORKFLOW = "NSFW Video.json"




PROFILE_PREFIX = (
    "NSFW, nudity, sexual content, pornographic content, explicit content, sexualized content, erotic content, adult content"   
    "realistic, trending girls, sexy, erotic, provocative"
    "high realism body, high realism private parts, high realism, tan lines, latina  "
) 


TECHNICAL_QUALITY = (
   "high detail, coherent anatomy, accurate hands, clean edges, sharp focus, "
    "consistent shapes, realistic texture, natural lighting, low artifacts, "
    "good body shape, realistic proportions"
)



DEFAULT_NEGATIVE = (
    "lowres, blurry, compression artifacts, watermark, unwanted text, "
    "malformed hands, fused fingers, extra fingers, missing fingers, extra limbs, "
    "duplicate limbs, broken anatomy, rendering artifacts, "
    "weird body shape, deformed vulva,unrealistic proportions, unnatural poses, bad angles, bad perspective"
)


def prepare_visual_request(
    prompt,
    selected_style="none",
    negative=None,
    technical_quality=True
):
    raw = (prompt or "").strip()
    prepared = raw

   
    if PROFILE_PREFIX.strip():
        prepared = PROFILE_PREFIX.strip() + "\n\n" + prepared

    
    if technical_quality:
        prepared += "\n\nTechnical quality only: " + TECHNICAL_QUALITY + "."

    neg = negative

   
    if technical_quality and not (negative or "").strip():
        neg = DEFAULT_NEGATIVE

    return prepared, neg, None