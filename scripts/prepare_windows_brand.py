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
MASTER = ROOT / "local_app" / "web" / "brand-identity.svg"
OUTPUT = ROOT / "build" / "branding"


def prepare():
    from PIL import Image, ImageOps
    content = MASTER.read_text(encoding="utf-8")
    found = re.search(r"data:image/webp;base64,([A-Za-z0-9+/=]+)", content)
    if not found:
        raise RuntimeError("Identité générale introuvable dans les logos fournis.")
    supplied = base64.b64decode(found.group(1), validate=True)
    img = Image.open(io.BytesIO(supplied)).convert("RGBA")
    if img.width < 200 or img.height < 100:
        raise RuntimeError("Identité générale de mauvaise dimension.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # The eight-point star is the visual mark of the SECOND supplied image.
    # Using the complete horizontal banner as a 16 px icon would be unreadable.
    mark = img.crop((118, 25, 192, 97))
    mark = mark.resize((218, 218), Image.Resampling.LANCZOS)
    from PIL import ImageDraw
    mask = Image.new("L",(218,218),0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,217,217),radius=32,fill=255)
    mark.putalpha(mask)
    icon = Image.new("RGBA", (256, 256), "#261838")
    icon.alpha_composite(mark,(19,19))
    icon.save(OUTPUT / "LocalAiVision.png", "PNG")
    icon.save(OUTPUT / "LocalAiVision.ico", format="ICO",
              sizes=[(16, 16), (24, 24), (32, 32),
                     (48, 48), (64, 64), (128, 128), (256, 256)])
    # Windows PE metadata identifies the software, but ONLY a legitimate
    # Authenticode certificate can identify a verified publisher to Windows.
    version = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=(3,1,0,0), prodvers=(3,1,0,0), mask=0x3f,
    flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0,0)),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'LocalAiVision'),
        StringStruct('FileDescription', 'LocalAiVision - studios IA et creation de sites'),
        StringStruct('FileVersion', '3.1.0'),
        StringStruct('InternalName', 'LocalVisionAI'),
        StringStruct('OriginalFilename', 'LocalVisionAI.exe'),
        StringStruct('ProductName', 'LocalAiVision & LocalAiWeb'),
        StringStruct('ProductVersion', '3.1.0'),
        StringStruct('LegalCopyright', 'LocalAiVision'),
      ]),
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ])
"""
    (OUTPUT / "version_info.txt").write_text(version, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    print(prepare())
