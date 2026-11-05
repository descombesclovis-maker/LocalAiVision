"""Build a NEW technology photograph for the Studio brand identity card.

Source: Pedro Henrique Santos, « Purple, pink and cyan Stream PC Colors »
https://unsplash.com/photos/7gMZ6lHDN_0 — Unsplash License.
The licensed real computer hardware photo is bundled for offline desktop use.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

DEST = Path(__file__).resolve().parents[1] / "local_app" / "web" / "presentation" / "brand-identity-1600.webp"
PHOTOS = (
    "https://unsplash.com/photos/7gMZ6lHDN_0/download?force=true&w=1800",
    "https://unsplash.com/photos/l1kqM4qZt2E/download?force=true&w=1800",
)


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 10_000:
        print("Brand card photograph already present:", DEST)
        return
    last_error = None
    for photo in PHOTOS:
        try:
            request = Request(photo, headers={"User-Agent": "Mozilla/5.0 (LocalAiStudio photo bundler)"})
            with urlopen(request, timeout=25) as stream:
                raw = stream.read(14 * 1024 * 1024 + 1)
            if len(raw) > 14 * 1024 * 1024:
                raise ValueError("Photograph too large")
            with Image.open(BytesIO(raw)) as image:
                if image.width < 650 or image.height < 500:
                    raise ValueError("Photograph resolution too low")
                image = ImageOps.fit(image.convert("RGB"), (1600, 700), method=Image.Resampling.LANCZOS)
                image.save(DEST, "WEBP", quality=85, method=6)
            print("Bundled new real cyan-violet technology photograph:", DEST.stat().st_size, "bytes")
            return
        except Exception as exc:
            last_error = exc
            print("Photograph source unavailable:", type(exc).__name__)
    # Never silently reuse the old stationery picture or a web-universe asset:
    # it would conceal an unfulfilled user request.
    raise RuntimeError("Unable to bundle the new technology card photograph") from last_error



if __name__ == "__main__":
    main()
