"""Private, cross-universe brand kits and accurate advertising overlays.

Only user-provided brand images are accepted. No brand is guessed from a map.
Original ComfyUI outputs remain unchanged; exports are derivative files.
"""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import urlopen
import uuid

ID=re.compile(r"^[a-f0-9]{32}$")
EXPORTED=re.compile(r"^pub-[a-f0-9]{24}\.(?:png|mp4)$")
MAX_SOURCE=110*1024*1024
FIELDS={"name":100,"sector":90,"slogan":180,"audience":180,
        "description":360,"cta":100,"website":160}
COLORS=re.compile(r"^#[0-9A-Fa-f]{6}$")
FORMAT={"square":(1080,1080),"portrait":(1080,1920),"landscape":(1920,1080)}
SUPPORTED={".png": "image/png",".jpg":"image/jpeg",
           ".jpeg":"image/jpeg",".webp":"image/webp",
           ".mp4":"video/mp4",".webm":"video/webm",
           ".mov":"video/quicktime"}


def _root(base):
    path=Path(base)/"brands"
    path.mkdir(parents=True,exist_ok=True)
    return path


def _id(raw):
    value=str(raw or "")
    if not ID.fullmatch(value):
        raise ValueError("Identifiant de marque invalide.")
    return value


def _path(base,brand_id):
    return _root(base)/_id(brand_id)


def _load(base,brand_id):
    path=_path(base,brand_id)/"brand.json"
    if not path.is_file():
        raise FileNotFoundError("Marque introuvable.")
    item=json.loads(path.read_text(encoding="utf-8"))
    item["logo_url"]=("/api/studio/brand/logo?id="+brand_id
                      if (_path(base,brand_id)/"logo.png").is_file() else None)
    return item


def get_brand(base,brand_id):
    return _load(base,brand_id)


def list_brands(base):
    brands=[]
    for child in _root(base).iterdir():
        if child.is_dir() and ID.fullmatch(child.name):
            try:brands.append(_load(base,child.name))
            except (OSError,ValueError,TypeError):pass
    return {"brands":sorted(brands,key=lambda b:(b.get("name") or "").casefold())}


def save_brand(base,values):
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not isinstance(values,dict):
        raise ValueError("Informations de marque invalides.")
    name=str(values.get("name") or "").strip()
    if len(name)<2 or len(name)>100:
        raise ValueError("Entre 2 et 100 caractères pour le nom de la marque.")
    supplied=values.get("id")
    brand_id=_id(supplied) if supplied else uuid.uuid4().hex
    folder=_path(base,brand_id)
    if supplied and not (folder/"brand.json").is_file():
        raise FileNotFoundError("Impossible de modifier une marque introuvable.")
    existing=(_load(base,brand_id) if supplied else {})
    result={"id":brand_id,"name":name,"created_at":existing.get("created_at",time.time()),
            "updated_at":time.time()}
    for field,maxlen in FIELDS.items():
        if field!="name":
            result[field]=str(values.get(field,existing.get(field,"")) or "").strip()[:maxlen]
    for key,default in (("primary_color","#9B71E8"),("secondary_color","#15202E")):
        color=str(values.get(key) or existing.get(key) or default).upper()
        if not COLORS.fullmatch(color):
            raise ValueError("Couleur de marque incorrecte.")
        result[key]=color
    logo=values.get("logo_data")
    decoded=None
    if logo:
        if not isinstance(logo,str) or len(logo)>4_200_000:
            raise ValueError("Le logo doit être un PNG, JPEG ou WebP de moins de 3 Mo.")
        header,sep,payload=logo.partition(",")
        if not sep or not re.fullmatch(r"data:image/(?:png|jpeg|webp);base64",header):
            raise ValueError("Logo accepté : PNG, JPEG ou WebP uniquement.")
        try:
            raw=base64.b64decode(payload,validate=True)
            if len(raw)>3_000_000:raise ValueError("Logo trop volumineux.")
            Image.MAX_IMAGE_PIXELS=22_000_000
            with Image.open(BytesIO(raw)) as im:
                if im.format not in ("PNG","JPEG","WEBP"):
                    raise ValueError("Format de logo invalide.")
                copied=ImageOps.exif_transpose(im).convert("RGBA")
                copied.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                output=BytesIO()
                copied.save(output,format="PNG",optimize=True)
                decoded=output.getvalue()
        except (ValueError,UnidentifiedImageError,OverflowError,OSError) as exc:
            raise ValueError("Impossible de lire le logo : "+str(exc)[:120]) from exc
    folder.mkdir(parents=True,exist_ok=True)
    if decoded is not None:
        tmp=folder/"logo.pending"
        tmp.write_bytes(decoded)
        os.replace(tmp,folder/"logo.png")
    tmp=folder/"brand.pending"
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    os.replace(tmp,folder/"brand.json")
    return _load(base,brand_id)


def logo_bytes(base,brand_id):
    _load(base,brand_id)
    return (_path(base,brand_id)/"logo.png").read_bytes()


def _font(size,bold=True):
    from PIL import ImageFont
    candidates=(
        ("C:/Windows/Fonts/seguisb.ttf","C:/Windows/Fonts/segoeui.ttf")
        if bold else ("C:/Windows/Fonts/segoeui.ttf",)
    )
    for file in (*candidates,"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:return ImageFont.truetype(file,size)
        except (OSError,ValueError):continue
    return ImageFont.load_default()


def _overlay(brand,width,height,logo_path,format_name):
    from PIL import Image, ImageDraw
    canvas=Image.new("RGBA",(width,height),(0,0,0,0))
    draw=ImageDraw.Draw(canvas,"RGBA")
    scale=width/1080
    margin=round(58*scale)
    pad=round(20*scale)
    # Compact, legible footer; keep original photo visible.
    footer=round(height*.20) if height<width*1.3 else round(height*.12)
    for row in range(footer):
        alpha=round(226*row/max(1,footer-1))
        draw.line((0,height-footer+row,width,height-footer+row),
                  fill=(8,13,23,alpha),width=1)
    if logo_path.is_file():
        with Image.open(logo_path) as logo:
            logo=logo.convert("RGBA")
            logo.thumbnail((round(width*.16),round(height*.095)),Image.Resampling.LANCZOS)
            plaque=Image.new("RGBA",(logo.width+pad*2,logo.height+pad*2),
                             (12,14,22,154))
            plaque.alpha_composite(logo,(pad,pad))
            canvas.alpha_composite(plaque,(margin,round(54*scale)))
    name=str(brand.get("name",""))[:70]
    slogan=str(brand.get("slogan") or "")[:120]
    cta=str(brand.get("cta") or "")[:60]
    font=_font(max(24,round(41*scale)))
    secondary=_font(max(17,round(24*scale)),False)
    base=height-round(42*scale)
    # Fit long names to usable width instead of clipping.
    while draw.textbbox((0,0),name,font=font)[2]>width-2*margin and getattr(font,"size",0)>22:
        font=_font(font.size-3)
    if cta:
        tw=draw.textbbox((0,0),cta,font=secondary)[2]
        x=max(margin,width-margin-tw-round(24*scale))
        draw.rounded_rectangle((x-round(12*scale),base-round(11*scale),
                                min(width-margin+pad,x+tw+round(14*scale)),base+round(32*scale)),
                               radius=round(9*scale),fill=(255,255,255,235))
        draw.text((x,base-round(3*scale)),cta,font=secondary,fill=(25,18,38,255))
    top=height-footer+round(footer*.20)
    draw.text((margin,top),name,font=font,fill=(255,255,255,255),
              stroke_width=1,stroke_fill=(0,0,0,140))
    if slogan:
        short=slogan
        while draw.textbbox((0,0),short,font=secondary)[2]>width-2*margin and len(short)>8:
            short=short[:-2].rstrip()
        if short!=slogan:short+="…"
        draw.text((margin,top+round(52*scale)),short,font=secondary,fill=(239,234,246,245))
    return canvas


def _source_media(item):
    filename=str(item.get("filename") or "")
    subfolder=str(item.get("subfolder") or "")
    kind=str(item.get("type") or "output")
    if (not filename or filename!=Path(filename).name
            or not re.fullmatch(r"[a-zA-Z0-9_().+ -]{1,220}",filename)
            or ".." in subfolder or "\\" in subfolder
            or kind!="output"):
        raise ValueError("Fichier de sortie invalide.")
    ext=Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError("Image ou vidéo non prise en charge.")
    return filename,subfolder,ext


def render_advert(base,comfy_base,body):
    from PIL import Image, ImageOps
    brand=_load(base,body.get("brand_id"))
    fmt=str(body.get("format") or "square")
    if fmt not in FORMAT:raise ValueError("Format publicitaire inconnu.")
    filename,subfolder,ext=_source_media(body)
    url=comfy_base.rstrip("/")+"/view?"+urlencode({
        "filename":filename,"subfolder":subfolder,"type":"output"})
    with urlopen(url,timeout=50) as reply:
        raw=reply.read(MAX_SOURCE+1)
    if len(raw)>MAX_SOURCE:raise ValueError("Fichier source trop volumineux.")
    width,height=FORMAT[fmt]
    out=Path(base)/"advertising"/"output"
    out.mkdir(parents=True,exist_ok=True)
    suffix=".mp4" if ext in (".mp4",".webm",".mov") else ".png"
    name="pub-"+uuid.uuid4().hex[:24]+suffix
    target=out/name
    overlay=_overlay(brand,width,height,_path(base,brand["id"])/"logo.png",fmt)
    if suffix==".png":
        with Image.open(BytesIO(raw)) as img:
            src=ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"),
                             (width,height),method=Image.Resampling.LANCZOS)
        src=src.convert("RGBA")
        src.alpha_composite(overlay)
        src.convert("RGB").save(target,format="PNG",optimize=True)
    else:
        ffmpeg=shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("Export vidéo avec logo : FFmpeg est nécessaire sur ce PC. "
                               "Les images publicitaires restent disponibles.")
        with tempfile.TemporaryDirectory(prefix="localai-ad-") as temporary:
            source=Path(temporary)/("source"+ext)
            stamp=Path(temporary)/"stamp.png"
            source.write_bytes(raw)
            overlay.save(stamp,format="PNG")
            args=[ffmpeg,"-hide_banner","-loglevel","error","-y",
                  "-i",str(source),"-loop","1","-i",str(stamp),
                  "-filter_complex",
                  "[0:v]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d[bg];"
                  "[bg][1:v]overlay=0:0:shortest=1:format=auto[v]"%
                  (width,height,width,height),
                  "-map","[v]","-map","0:a?","-c:v","libx264",
                  "-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
                  "-c:a","aac","-b:a","160k","-movflags","+faststart",
                  str(target)]
            try:
                proc=subprocess.run(args,capture_output=True,timeout=210,check=False)
                if proc.returncode or not target.is_file():
                    raise RuntimeError("FFmpeg n'a pas pu exporter cette vidéo : "+
                                       proc.stderr.decode("utf-8","replace")[-280:])
            except (OSError,subprocess.TimeoutExpired):
                target.unlink(missing_ok=True)
                raise RuntimeError("Export vidéo interrompu. Le fichier original est conservé.")
    return {"ok":True,"filename":name,"url":"/api/studio/advert/file?name="+name,
            "kind":"video" if suffix==".mp4" else "image",
            "brand":brand["name"],"format":fmt}


def advert_file(base,name):
    if not EXPORTED.fullmatch(str(name or "")):
        raise ValueError("Export publicitaire invalide.")
    path=Path(base)/"advertising"/"output"/name
    if not path.is_file():raise FileNotFoundError("Publicité introuvable.")
    return path


def delete_advert(base,name):
    path=advert_file(base,name)
    path.unlink()
    return {"ok":True,"deleted":True}
