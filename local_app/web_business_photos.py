"""On-demand, rights-aware storefront photographs from Wikimedia Commons.

No street view screenshots, invented building images or unlicensed Google
Places photos. A verified Commons file is shown only when linked to an OSM
Wikidata item, or when its filename mentions both the full trade name and city.
"""
import html
import json
import re
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from local_app import web_prospect_filter

_LOCK=threading.RLock()
_CACHE={}
_TTL=86400
_AGENT="LocalAiWeb/3.0 (local business card; https://github.com/descombesclovis-maker/LocalAiVision)"
_LICENSED=("cc-by","cc-by-sa","cc0","public domain","public-domain","pd-old","pd-us")
_ALLOWED_IMAGES=(".jpg",".jpeg",".webp",".png")


def _json(host, params):
    url=host+"?"+urlencode(params)
    with urlopen(Request(url,headers={"User-Agent":_AGENT,"Accept":"application/json"}),timeout=7) as response:
        raw=response.read(600001)
    if len(raw)>600000:raise ValueError("Réponse Wikimedia trop volumineuse.")
    return json.loads(raw)


def _attribution(info, license_name):
    meta=info.get("extmetadata") or {}
    raw=str((meta.get("Artist") or {}).get("value") or "")
    author=html.unescape(re.sub(r"<[^>]+>"," ",raw))
    author=" ".join(author.split())[:110]
    return "Wikimedia Commons · "+license_name+((" · "+author) if author else "")


def _license(info):
    meta=info.get("extmetadata") or {}
    short=str((meta.get("LicenseShortName") or {}).get("value") or "").strip()
    code=str((meta.get("License") or {}).get("value") or "").strip().lower()
    if not any(code.startswith(x) or short.lower().startswith(x) for x in _LICENSED):
        return ""
    return short[:70] or code[:70]


def _photo_page(title):
    if not title or not title.startswith("File:") or len(title)>225:
        return None
    lower=title.lower()
    if not lower.endswith(_ALLOWED_IMAGES) or "logo" in lower:
        return None
    data=_json("https://commons.wikimedia.org/w/api.php",{
        "action":"query","format":"json","titles":title,
        "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":950})
    for page in (data.get("query") or {}).get("pages",{}).values():
        info=(page.get("imageinfo") or [{}])[0]
        license_name=_license(info)
        url=str(info.get("thumburl") or info.get("url") or "")
        if not license_name or not url.startswith("https://upload.wikimedia.org/"):
            continue
        return {"image_url":url[:500],"image_credit":_attribution(info,license_name),
                "photo_source":str(info.get("descriptionurl") or "")[:500],
                "photo_type":"photographie_documentee"}
    return None


def _wikidata_photo(item):
    qid=str(item.get("wikidata") or "")
    if not re.fullmatch(r"Q[1-9][0-9]{0,11}",qid):
        return None
    data=_json("https://www.wikidata.org/w/api.php",{
        "action":"wbgetentities","ids":qid,"props":"claims","format":"json"})
    claims=(data.get("entities",{}).get(qid) or {}).get("claims") or {}
    for claim in (claims.get("P18") or [])[:4]:
        filename=(((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value"))
        if isinstance(filename,str):
            photo=_photo_page("File:"+filename.removeprefix("File:"))
            if photo:return photo
    return None


def _search_photo(item):
    name=str(item.get("name") or "").strip()
    city=str(item.get("city") or "").strip()
    # Searching vague company names (or a bare personal surname) risks showing
    # the wrong building. Restrict this fallback to sufficiently precise names.
    if not city or len(name)<9 or len(city)<3:
        return None
    data=_json("https://commons.wikimedia.org/w/api.php",{
        "action":"query","format":"json","generator":"search",
        "gsrsearch":'"'+name[:90]+'" "'+city[:65]+'"',
        "gsrnamespace":6,"gsrlimit":7,
        "prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":950})
    wanted_name=web_prospect_filter.normalize(name)
    wanted_city=web_prospect_filter.normalize(city)
    for page in (data.get("query") or {}).get("pages",{}).values():
        title=str(page.get("title") or "")
        normalized=web_prospect_filter.normalize(title)
        # No unverified geographical or brand matches.
        if wanted_name not in normalized or wanted_city not in normalized:
            continue
        license_name=_license((page.get("imageinfo") or [{}])[0])
        info=(page.get("imageinfo") or [{}])[0]
        url=str(info.get("thumburl") or info.get("url") or "")
        if ("logo" in normalized or not title.lower().endswith(_ALLOWED_IMAGES)
                or not license_name or not url.startswith("https://upload.wikimedia.org/")):
            continue
        return {"image_url":url[:500],"image_credit":_attribution(info,license_name),
                "photo_source":str(info.get("descriptionurl") or "")[:500],
                "photo_type":"photographie_nom_et_ville_a_verifier"}
    return None


def resolve(item):
    """Return an authentic licensed photograph, or an explicit no-photo result."""
    if not item or not web_prospect_filter.eligible(item):
        return {"image_url":"","notice":"Entreprise hors des critères de la carte."}
    if str(item.get("image_url") or "").startswith((
            "https://commons.wikimedia.org/","https://upload.wikimedia.org/")):
        return {"image_url":item["image_url"],
                "image_credit":item.get("image_credit") or "Photo OpenStreetMap · licence à vérifier",
                "photo_type":"source_osm"}
    key=str(item.get("id") or "")
    with _LOCK:
        cached=_CACHE.get(key)
        if cached and time.time()-cached[0]<_TTL:return dict(cached[1])
    photo=None
    try:
        photo=_wikidata_photo(item) or _search_photo(item)
    except (ValueError,KeyError,TypeError,OSError,TimeoutError):
        photo=None
    result=photo or {"image_url":"",
                     "notice":"Aucune photographie de la boutique ou du siège identifiable et librement réutilisable trouvée."}
    with _LOCK:
        if len(_CACHE)>500:_CACHE.clear()
        _CACHE[key]=(time.time(),result)
    return result
