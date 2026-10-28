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
THROTTLE_SECONDS=27


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
    raw=web_business_map._json_http(
        "overpass",web_business_map.OVERPASS,post=urlencode({"data":query}))
    items=[]
    seen=set()
    for row in (raw.get("elements") or [])[:650]:
        tags=row.get("tags") or {}
        if any(str(tags.get(tag) or "").strip() for tag in WEBSITE_KEYS):
            continue
        business=_normalize(row)
        if not business or business["id"] in seen or business["website_recorded"]:
            continue
        seen.add(business["id"])
        items.append(business)
    result={"results":items,"mode":mode,"partial":True,
            "website_status":"non_renseigne_osm",
            "website_verified":False,
            "notice":"Aucun site indiqué dans OSM ≠ absence de site confirmée. Vérification complémentaire nécessaire.",
            "source":"OpenStreetMap / Overpass","cached":False}
    with LOCK:
        if len(CACHE)>70:CACHE.clear()
        CACHE[key]=(time.monotonic(),result)
    return result


def france_overview():
    """One bounded Overpass query; few real leads per city, not all France."""
    key=("france-overview",)
    pieces=[]
    for lat,lon in FRANCE_POINTS:
        # Explicit small radii and per-city output caps prevent a country-wide
        # bulk export and distribute the displayed points across France.
        pieces.append(
            f'nwr(around:800,{lat},{lon})["name"]'
            f'{BUSINESS_TAG}{NO_WEBSITE_TAGS};out center 12;')
    statement="[out:json][timeout:25];"+"".join(pieces)
    return _load(key,statement,"france_overview")


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
        f'{BUSINESS_TAG}{NO_WEBSITE_TAGS};out center 220;'
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
        f'{BUSINESS_TAG}{NO_WEBSITE_TAGS};out center 350;'
    )
    return _load(key,statement,"viewport")
