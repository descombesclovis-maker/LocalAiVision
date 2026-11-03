"""Convert the complete, locked Studio PNG to a genuine multi-resolution ICO.

No drawing, cropping, recolouring, alpha removal or logo reconstruction.
The master bytes are pinned to the user-approved SHA-256 before conversion.
"""
from __future__ import annotations
import hashlib
import io
from pathlib import Path
import struct


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "local_app" / "web" / "assets" / "brand-reference" / "LocalAIStudio_Official_Original.png"
MASTER_SHA256 = "9c8e94862781f263b1b95d2e13504518f7a624b809db93e074ce1a498b9fdcd4"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
OUTPUT = ROOT / "build" / "branding"


def prepare(output=OUTPUT):
    from PIL import Image
    payload = MASTER.read_bytes()
    if hashlib.sha256(payload).hexdigest() != MASTER_SHA256:
        raise RuntimeError("Le logo maître LocalAI Studio ne correspond pas à l’original approuvé.")
    with Image.open(io.BytesIO(payload)) as source:
        if source.size != (724, 724):
            raise RuntimeError("Le carré complet du logo Studio doit mesurer 724 × 724 pixels.")
        master = source.convert("RGBA")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Every size is independently scaled from the WHOLE original. PNG payloads
    # inside an ICO directory are the lossless Windows Vista+ icon format.
    entries, images = [], []
    offset = 6 + 16 * len(ICON_SIZES)
    for size in ICON_SIZES:
        frame = master.resize((size, size), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        data = buffer.getvalue()
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256,
                                   0, 0, 1, 32, len(data), offset))
        images.append(data)
        offset += len(data)
    (output / "LocalAiStudio.ico").write_bytes(
        struct.pack("<HHH", 0, 1, len(entries)) + b"".join(entries) + b"".join(images))
    master.resize((256, 256), Image.Resampling.LANCZOS).save(output / "LocalAiStudio.png")
    (output / "icon-provenance.txt").write_text(
        f"Source: {MASTER.relative_to(ROOT).as_posix()}\nSHA-256: {MASTER_SHA256}\n"
        "Conversion: complete square, proportional LANCZOS scaling only.\n"
        "ICO sizes: " + ", ".join(map(str, ICON_SIZES)) + " px.\n",
        encoding="utf-8")
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
    (output / "version_info.txt").write_text(version, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(prepare())
