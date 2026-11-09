"""Assemblage du prompt photo ComfyUI (partagé app + benchmark). Module pur, sans dépendance."""

PHOTO_QUALITY_SUFFIX = ", highly detailed, professional photography, sharp focus, premium quality"


def comfy_photo_prompt(prompt: str) -> str:
    """Ajoute le suffixe qualité sans doubler la ponctuation (« blanc., highly… » -> « blanc, highly… »)."""
    return prompt.rstrip(" .,;") + PHOTO_QUALITY_SUFFIX
