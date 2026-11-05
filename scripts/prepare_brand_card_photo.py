"""Build-only, cached photographic image for the brand identity card.

Photo: Volodymyr Hryshchenko, Unsplash (stationery on a coloured desk),
https://unsplash.com/photos/7_bz84zOU7g — Unsplash License.
The image is bundled into Windows builds so the application works offline.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import shutil
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

DEST = Path(__file__).resolve().parents[1] / "local_app" / "web" / "presentation" / "brand-identity-1600.webp"
FALLBACK = DEST.parent / "web-1600.webp"
PHOTO = "https://images.unsplash.com/photo-1654931800100-2ecf6eee7c64?auto=format&fit=crop&w=1800&h=950&q=85"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 10_000:
        print("Brand card photograph already present:", DEST)
        return
    try:
        request = Request(PHOTO, headers={"User-Agent": "LocalAiStudio/3.1 (+Unsplash licensed photograph)"})
        with urlopen(request, timeout=20) as stream:
            raw = stream.read(12 * 1024 * 1024 + 1)
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError("Unexpectedly large photograph")
        with Image.open(BytesIO(raw)) as image:
            image = ImageOps.fit(image.convert("RGB"), (1600, 700), method=Image.Resampling.LANCZOS)
            image.save(DEST, "WEBP", quality=82, method=6)
        print("Bundled new licensed stationery photograph:", DEST.stat().st_size, "bytes")
    except Exception as exc:
        # A temporary image-host outage should not prevent an unrelated Windows build.
        print("Could not fetch new photograph (using packaged fallback):", exc)
        if FALLBACK.exists():
            shutil.copyfile(FALLBACK, DEST)
        else:
            raise


if __name__ == "__main__":
    main()
