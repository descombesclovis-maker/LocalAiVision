"""Visible, bounded OpenStreetMap leads without a *recorded* website.

The absence of OSM website tags DOES NOT prove that the business has no site.
OpenStreetMap/Overpass is shared infrastructure: a single cached overview of
France is a geographically distributed *sample*, not an exhaustive dataset.
Local detail loads are debounced in the UI and throttled on the server.
"""
from __future__ import annotations
import math
import threading
import time
from urllib.parse import urlencode

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
NO_WEBSITE='[!"website"][!"contact:website"][!"url"][!"contact:url"][!"website:mobile"]'
BUSINESS_TAG='[~"^(shop|craft|office|amenity|leisure|tourism)$"~"."]'
LOCK=threading.RLock()
CACHE={}
LAST_REQUEST=0.0
CACHE_SECONDS=1800
THROTTLE_SECONDS=27


def _normalize(row):
    tags=row.get("tags") or {}
    if not tags.get("name"):
        return None
    if any(str(tags.get(key) or "").strip() for key in (
        "website","contact:website","url","contact:url","website:mobile")):
        return None
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
        "source":"overpass",
    })
    if info:
        info["website_status"]="non_renseigne_osm"
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
                "La carte se recharge progressivement. Évite les déplacements rapides et réessaie dans quelques instants.")
        LAST_REQUEST=now
    raw=web_business_map._json_http(
        "overpass",web_business_map.OVERPASS,post=urlencode({"data":query}))
    items=[]
    seen=set()
    for row in (raw.get("elements") or [])[:650]:
        business=_normalize(row)
        if not business or business["id"] in seen:continue
        seen.add(business["id"])
        items.append(business)
    result={"results":items,"mode":mode,"partial":True,
            "notice":"Sans site renseigné dans OpenStreetMap ≠ absence confirmée de site web.",
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
            f'{BUSINESS_TAG}{NO_WEBSITE};out center 7;')
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
        f'{BUSINESS_TAG}{NO_WEBSITE};out center 220;'
    )
    return _load(key,statement,"nearby")
