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
    # Render the vector master mark directly with Pillow primitives at
    # four times the final size. No embedded 160px WebP, no platform-specific
    # SVG/Cairo runtime and no network download.
    from PIL import Image, ImageDraw
    import math
    if "CRÉATIONS VISUELLES" not in MASTER.read_text(encoding="utf-8"):
        raise RuntimeError("Le logo général de LocalAiVision est introuvable.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    size=1024
    icon=Image.new("RGBA",(size,size),(38,24,56,255))
    draw=ImageDraw.Draw(icon)
    cx=cy=size//2
    outer=size*0.40
    inner=size*0.165
    points=[]
    for k in range(16):
        angle=-math.pi/2+k*math.pi/8
        radius=outer if k%2==0 else inner
        points.append((cx+int(math.cos(angle)*radius),
                       cy+int(math.sin(angle)*radius)))
    draw.polygon(points,fill="#39215d")
    draw.line(points+[points[0]],fill="#a580c7",width=12,joint="curve")
    draw.line([(cx,175),(cx,302),(cx+40,355),(cx+40,430)],
              fill="#ba91e2",width=12,joint="curve")
    draw.line([(cx-290,cy),(cx-100,cy),(cx-60,cy+32)],
              fill="#9766c3",width=10,joint="curve")
    draw.line([(cx+290,cy),(cx+110,cy),(cx+58,cy+30)],
              fill="#9766c3",width=10,joint="curve")
    draw.line([(cx,cy+290),(cx,cy+105),(cx-35,cy+60)],
              fill="#9766c3",width=10,joint="curve")
    # Eight-point sparkle remains legible at 16x16.
    sparkle=[]
    for k in range(8):
        angle=-math.pi/2+k*math.pi/4
        radius=155 if k%2==0 else 24
        sparkle.append((cx+int(math.cos(angle)*radius),
                        cy+int(math.sin(angle)*radius)))
    draw.polygon(sparkle,fill="#FAF4FF")
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
