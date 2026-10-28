"""Visible, bounded OpenStreetMap prospects without a recorded website.

Missing website OSM tags DO NOT prove that a business has no actual website.
OpenStreetMap/Overpass is shared infrastructure: a single cached overview of
France is a geographically distributed *sample*, not an exhaustive dataset.
Local detail loads are debounced in the UI and throttled on the server.
"""
from __future__ import annotations
import ipaddress
import threading
import time
from urllib.parse import urlencode, urlsplit
from pathlib import Path
import json
import os

from local_app import web_business_map

# Representative centers only; never invent names or locations of businesses.
FRANCE_POINTS = (
 (48.8566,2.3522),(50.6292,3.0573),(48.5734,7.7521),
 (45.7640,4.8357),(43.2965,5.3698),(43.7102,7.2620),
 (43.6047,1.4442),(44.8378,-0.5792),(47.2184,-1.5536),
 (48.1173,-1.6778),(48.3904,-4.4861),(47.3220,5.0415),
 (47.2378,6.0241),(45.1885,5.7245),(43.6108,3.8767),
 (45.7772,3.0870),(47.9029,1.9093),(47.3941,0.6848),
 (49.4432,1.0993),(49.8941,2.2958),(45.8336,1.2611),
 (48.6921,6.1844),(46.5802,0.3404),(43.4832,-1.5586),
 # Distribute initial leads beyond major metros, without making an
 # exhaustive country-wide Overpass extraction (which is impractical).
 (45.1885,5.7245),(45.4397,4.3872),(45.8992,6.1294),
 (45.5646,5.9178),(44.9334,4.8924),(43.9493,4.8055),
 (43.1242,5.9280),(43.8367,4.3601),(42.6887,2.8948),
 (43.3442,3.2158),(43.1843,3.0031),(43.2132,2.3518),
 (43.2951,-0.3708),(43.2327,0.0781),(46.1591,-1.1520),
 (45.6484,0.1562),(46.3237,-0.4588),(45.1582,1.5321),
 (45.1840,0.7211),(44.3937,0.6008),(44.0221,1.3520),
 (43.9273,2.1480),(44.3495,2.5750),(44.9282,2.4449),
 (46.5669,3.3322),(46.9896,3.1590),(47.0844,2.3964),
 (46.8114,1.6913),(47.5923,1.3281),(48.0077,0.1984),
 (48.0704,-0.7731),(48.4310,0.0900),(49.1829,-0.3707),
 (49.6394,-1.6160),(49.1143,-1.0910),(48.8826,-0.6385),
 (48.4473,1.4890),(47.7982,3.5738),(48.2973,4.0744),
 (49.2583,4.0317),(49.7711,4.7198),(49.1193,6.1757),
 (48.1734,6.4494),(48.0793,7.3585),(47.7508,7.3359),
 (47.6397,6.8638),(47.6198,6.1559),(47.0922,5.4911),
 (46.2044,5.2255),(46.3069,4.8287),(46.7806,4.8539),
 (46.6749,5.5500),(41.9192,8.7386),(42.7028,9.4509),
 (50.9513,1.8587),(51.0344,2.3768),(50.7238,1.6133),
 (50.2910,2.7775),(50.4293,2.8277),(50.3709,3.0807),
 (50.1750,3.2340),(50.3599,3.5238),(49.4330,2.0844),
 (49.4179,2.8261),(49.5641,3.6249),(49.8477,3.2877),
)
WEBSITE_KEYS=("website","contact:website","url","contact:url","website:mobile")
# Both Overpass and this server screen the known website tags. Their absence
# cannot certify that an establishment does not have a website.
NO_WEBSITE_TAGS="".join(f'[!"{tag}"]' for tag in WEBSITE_KEYS)
BUSINESS_TAG='[~"^(shop|craft|office|amenity|leisure|tourism)$"~"."]'
LOCK=threading.RLock()
CACHE={}
LAST_REQUEST=0.0
CACHE_SECONDS=1800
# One small Overpass batch per interval, rather than one huge query for France.
THROTTLE_SECONDS=12
# Best-effort community instances: identify application, cache, and rate limit.
# Private.coffee expressly provides a POST Overpass endpoint; FOSSGIS is fallback.
OVERPASS_ENDPOINTS=(
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    web_business_map.OVERPASS,
)
# Persist only actual OSM responses; show a clearly dated local cache offline.
CACHE_DIR=Path(os.environ.get("LOCALVISIONAI_DATA",str(Path.home()/".localvisionai")))/"map_cache"
FRANCE_BATCH_SIZE=10
FRANCE_BATCH_COUNT=(len(FRANCE_POINTS)+FRANCE_BATCH_SIZE-1)//FRANCE_BATCH_SIZE


def safe_website(raw):
    """Allow an ordinary public HTTP(S) URL only, never arbitrary HTML/JS."""
    candidate=str(raw or "").strip()
    if (not candidate or any(ch.isspace() for ch in candidate) or
            any(ch in candidate for ch in ("\\", "<", ">", "\"", "'"))):
        return ""
    if not candidate.startswith(("http://","https://")):
        if "://" in candidate or candidate.startswith(("/", "#")):
            return ""
        candidate="https://"+candidate
    try:
        parsed=urlsplit(candidate)
        host=(parsed.hostname or "").strip().lower()
        if parsed.scheme not in ("http","https") or not host or parsed.username or parsed.password:
            return ""
        if host in ("localhost","localhost.localdomain") or host.endswith((".local",".internal")):
            return ""
        try:
            ip=ipaddress.ip_address(host)
            if not ip.is_global:
                return ""
        except ValueError:
            if "." not in host or host.startswith(".") or host.endswith("."):
                return ""
        if len(candidate)>170 or parsed.port not in (None,80,443):
            return ""
    except ValueError:
        return ""
    return candidate


def _normalize(row):
    tags=row.get("tags") or {}
    if not tags.get("name"):
        return None
    website_raw=next((str(tags.get(key) or "").strip() for key in WEBSITE_KEYS
                      if str(tags.get(key) or "").strip()),"")
    # Exclude non-commercial public facilities from broad OSM category matches.
    if not tags.get("shop") and not tags.get("craft") and not tags.get("office"):
        if not any(tags.get(key) in (
            "restaurant","cafe","bar","fast_food","pub","ice_cream",
            "dentist","doctors","veterinary","clinic","pharmacy",
            "fitness_centre","sports_centre","spa","sauna",
            "hotel","guest_house","hostel","camp_site","gallery","attraction"
        ) for key in ("amenity","leisure","tourism")):
            return None
    center=row.get("center") or row
    if "lat" not in center or "lon" not in center:
        return None
    category=next((tags[t] for t in ("shop","craft","office","amenity","leisure","tourism")
                   if tags.get(t)), "entreprise")
    street=" ".join(str(x) for x in (
        tags.get("addr:housenumber"),tags.get("addr:street")) if x)
    address=", ".join(str(x) for x in (
        street,tags.get("addr:postcode"),tags.get("addr:city")) if x)
    info=web_business_map._result({
        "name":tags["name"],"lat":center["lat"],"lon":center["lon"],
        "osm_id":f'{row.get("type","node")}/{row.get("id","")}',
        "category":category,"address":address,
        "postcode":tags.get("addr:postcode"),"city":tags.get("addr:city"),
        "country":tags.get("addr:country"),
        "phone":tags.get("contact:phone") or tags.get("phone"),
        "email":tags.get("contact:email") or tags.get("email"),
        "opening_hours":tags.get("opening_hours"),
        "description":tags.get("description"),
        "operator":tags.get("operator"),
        "website":safe_website(website_raw),
        "source":"overpass",
    })
    if info:
        info["website_status"]=("renseigne_osm" if website_raw else "non_renseigne_osm")
        info["website_recorded"]=bool(website_raw)
        info["website_link_available"]=bool(info.get("website"))
    return info


def _load(key, query, mode):
    global LAST_REQUEST
    now=time.monotonic()
    with LOCK:
        cached=CACHE.get(key)
        if cached and now-cached[0] < CACHE_SECONDS:
            return dict(cached[1], cached=True)
        if now-LAST_REQUEST < THROTTLE_SECONDS:
            raise RuntimeError(
                "La carte se recharge progressivement. Réessaie dans quelques instants.")
        LAST_REQUEST=now
    raw=None
    errors=[]
    cache_file=CACHE_DIR/("overpass-"+__import__("hashlib").sha256(query.encode("utf-8")).hexdigest()[:32]+".json")
    for index,endpoint in enumerate(OVERPASS_ENDPOINTS):
        try:
            # Different provider throttle keys avoid double-failing the fallback.
            raw=web_business_map._json_http(
                "overpass" if index==0 else "overpass_backup",
                endpoint,post=urlencode({"data":query}))
            if not isinstance(raw,dict) or "elements" not in raw:
                raise RuntimeError("Réponse Overpass invalide.")
            break
        except Exception as exc:
            errors.append(str(exc))
    source_offline=False
    if raw is None:
        try:
            cached=json.loads(cache_file.read_text(encoding="utf-8"))
            if not isinstance(cached.get("elements"),list):raise ValueError("Cache invalide")
            raw=cached
            source_offline=True
        except (OSError,ValueError,TypeError):
            # Failed network attempts should not block retry or invent businesses.
            with LOCK:LAST_REQUEST=0.0
            raise RuntimeError("Sources OpenStreetMap indisponibles ; aucune donnée locale encore disponible. "+
                               "; ".join(errors)[:250])
    else:
        try:
            CACHE_DIR.mkdir(parents=True,exist_ok=True)
            tmp=cache_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(raw,ensure_ascii=False),encoding="utf-8")
            tmp.replace(cache_file)
        except (OSError,TypeError):
            pass
    items=[]
    seen=set()
    for row in (raw.get("elements") or [])[:650]:
        tags=row.get("tags") or {}
        business=_normalize(row)
        if not business or business["id"] in seen:
            continue
        seen.add(business["id"])
        items.append(business)
    result={"results":items,"mode":mode,"partial":True,
            "website_status":"mixte_osm",
            "website_verified":False,
            "notice":"Vert : site non renseigné OSM, absence non confirmée. Rouge : site renseigné OSM. Données partielles.",
            "source":"OpenStreetMap / Overpass","cached":False,"offline":source_offline}
    with LOCK:
        if len(CACHE)>70:CACHE.clear()
        CACHE[key]=(time.monotonic(),result)
    return result


def france_overview(batch=0):
    """Small, independently cached regional samples, never a 90-city query.

    A single public Overpass server can timeout on the previous enormous query.
    Batch zero covers ten well-spaced French cities. More batches load lazily
    with visible progress and never block display of earlier points.
    """
    try:
        number=int(batch)
    except (TypeError, ValueError):
        raise ValueError("Numéro de lot de carte invalide.")
    if number<0 or number>=FRANCE_BATCH_COUNT:
        raise ValueError("Numéro de lot de carte hors limites.")
    key=("france-overview-v2",number)
    start=number*FRANCE_BATCH_SIZE
    centers=FRANCE_POINTS[start:start+FRANCE_BATCH_SIZE]
    pieces=[]
    for lat,lon in centers:
        pieces.append(
            f'nwr(around:850,{lat},{lon})["name"]'
            f'{BUSINESS_TAG};out center 18;')
    statement="[out:json][timeout:24];"+"".join(pieces)
    result=_load(key,statement,"france_overview")
    result["batch"]=number
    result["total_batches"]=FRANCE_BATCH_COUNT
    result["next_batch"]=number+1 if number+1<FRANCE_BATCH_COUNT else None
    return result


def area_details(lat,lon,zoom):
    la,lo=web_business_map._position(lat,lon)
    z=int(zoom)
    if z<10 or z>19:
        raise ValueError("Zoome sur une ville (niveau 10 minimum) pour consulter les établissements.")
    radius=5000 if z<=10 else 3000 if z==11 else 1800 if z==12 else 1100 if z==13 else 700
    key=("nearby",round(la,3),round(lo,3),radius)
    statement=(
        "[out:json][timeout:24];"
        f'nwr(around:{radius},{la},{lo})["name"]'
        f'{BUSINESS_TAG};out center 220;'
    )
    return _load(key,statement,"nearby")


def viewport_details(south,west,north,east,zoom):
    """Fetch only a small visible viewport. Broad extents are never scraped."""
    la1,lo1=web_business_map._position(south,west)
    la2,lo2=web_business_map._position(north,east)
    z=int(zoom)
    if z<13 or z>19:
        raise ValueError("Zoome sur un quartier pour charger une zone visible.")
    if not (la1<la2 and lo1<lo2):
        raise ValueError("Limites cartographiques invalides.")
    # At latitude 0 the maximum area is under 11 km by 11 km.
    if la2-la1>0.10 or lo2-lo1>0.10:
        raise ValueError("Zone trop vaste ; zoome davantage.")
    key=("viewport",round(la1,4),round(lo1,4),round(la2,4),round(lo2,4))
    statement=(
        "[out:json][timeout:24];"
        f'nwr({la1},{lo1},{la2},{lo2})["name"]'
        f'{BUSINESS_TAG};out center 350;'
    )
    return _load(key,statement,"viewport")
