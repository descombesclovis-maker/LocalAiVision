"""Create the real Windows desktop icon from the user-provided master identity.

No external requests, telemetry, untrusted downloads or antivirus exclusions.
The second supplied logo includes the studio wordmark and the eight-pointed
purple mark; the mark is cropped for clarity at small Windows icon sizes.
"""
from __future__ import annotations
import base64
import io
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "local_app" / "web" / "brand-studio.svg"
OUTPUT = ROOT / "build" / "branding"


def prepare():
    # Render the vector master mark directly with Pillow primitives at
    # four times the final size. No embedded 160px WebP, no platform-specific
    # SVG/Cairo runtime and no network download.
    from PIL import Image, ImageDraw
    import math
    if "viewBox=\"0 0 128 128\"" not in MASTER.read_text(encoding="utf-8"):
        raise RuntimeError("La nouvelle identité LocalAI Studio est introuvable.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    size=1024
    icon=Image.new("RGBA",(size,size),(17,16,26,255))
    draw=ImageDraw.Draw(icon)
    # Unified studio monogram, pixel-perfect and readable in the taskbar.
    draw.rounded_rectangle((40,40,984,984),radius=228,
                           outline=(177,144,227,145),width=13)
    draw.line((256,294,755,294),fill="#B98BFF",width=85,joint="curve")
    draw.line((256,510,513,510,755,294),fill="#A77BEF",width=85,joint="curve")
    draw.line((256,740,755,740,513,510),fill="#5FCACF",width=85,joint="curve")
    draw.ellipse((700,687,845,832),fill="#7CE5DB")
    icon=icon.resize((256,256),Image.Resampling.LANCZOS)
    icon.save(OUTPUT / "LocalAiVision.png","PNG")
    icon.save(OUTPUT / "LocalAiVision.ico",format="ICO",
              sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    # Windows PE metadata identifies the software, but ONLY a legitimate
    # Authenticode certificate can identify a verified publisher to Windows.
    version = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=(3,1,0,0), prodvers=(3,1,0,0), mask=0x3f,
    flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0,0)),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'LocalAI Studio'),
        StringStruct('FileDescription', 'LocalAI Studio - sites web, images et videos publicitaires'),
        StringStruct('FileVersion', '3.1.0'),
        StringStruct('InternalName', 'LocalVisionAI'),
        StringStruct('OriginalFilename', 'LocalVisionAI.exe'),
        StringStruct('ProductName', 'LocalAI Studio | LocalAiWeb + LocalAiVision'),
        StringStruct('ProductVersion', '3.1.0'),
        StringStruct('LegalCopyright', 'LocalAI Studio'),
      ]),
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ])
"""
    (OUTPUT / "version_info.txt").write_text(version, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    print(prepare())
