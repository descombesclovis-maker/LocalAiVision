"""Opt-in Google Maps / Places discovery. No scraping; official billable APIs only.

These requests occur exclusively after explicit searches or clicked map POIs.
Secrets remain server-side; the separate browser key must be referrer-restricted.
"""
import json
import os
import re
import time
import threading
from urllib.request import Request, urlopen
from urllib.parse import quote
from local_app import web_business_map

_LOCK=threading.Lock()
_LAST=0.0
_BASE="https://places.googleapis.com/v1/"

def configuration():
    """Expose only the browser key (public by design), never the Places REST secret."""
    browser=os.environ.get("LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY","").strip()
    private=os.environ.get("LOCALAIWEB_GOOGLE_PLACES_API_KEY","").strip()
    return {"enabled":bool(browser),
            "browser_key":browser,
            "places_enabled":bool(private),
            "requires_billing":True}

def _request(endpoint, *, data=None, field_mask):
    secret=os.environ.get("LOCALAIWEB_GOOGLE_PLACES_API_KEY","").strip()
    if not secret: raise ValueError("Google Places désactivé : configure une clé officielle de serveur.")
    global _LAST
    with _LOCK:
        now=time.monotonic()
        if now-_LAST<0.3: raise ValueError("Recherche Google trop rapprochée : réessaie dans un instant.")
        _LAST=now
    body=json.dumps(data,ensure_ascii=False).encode("utf-8") if data is not None else None
    headers={"X-Goog-Api-Key":secret,"X-Goog-FieldMask":field_mask,"Accept":"application/json"}
    if body is not None:headers["Content-Type"]="application/json"
    request=Request(_BASE+endpoint,data=body,headers=headers,method="POST" if body is not None else "GET")
    with urlopen(request,timeout=16) as response:
        raw=response.read(650001)
    if len(raw)>650000: raise ValueError("Réponse Google Places trop volumineuse.")
    return json.loads(raw.decode("utf-8"))

def _convert(place):
    point=place.get("location") or {}
    name=(place.get("displayName") or {}).get("text") or ""
    category=(place.get("primaryTypeDisplayName") or {}).get("text") or "entreprise"
    if not name or "latitude" not in point or "longitude" not in point:return None
    hours=place.get("regularOpeningHours") or {}
    return web_business_map._result({
        "name":name,"lat":point["latitude"],"lon":point["longitude"],
        "osm_id":place.get("id") or "",
        "google_place_id":place.get("id") or "",
        "address":place.get("formattedAddress") or "",
        "category":category,"kind":"business",
        "phone":place.get("internationalPhoneNumber") or "",
        "website":place.get("websiteUri") or "",
        "opening_hours":" ; ".join(hours.get("weekdayDescriptions") or []),
        "source":"google",
    })

_MASK="places.id,places.displayName,places.formattedAddress,places.location,places.primaryTypeDisplayName,places.websiteUri,places.internationalPhoneNumber,places.regularOpeningHours"
_DETAIL_MASK=_MASK.replace("places.","")

def search(query):
    q=web_business_map._plain(query,100)
    if len(q)<3:raise ValueError("Recherche Google : trois caractères minimum.")
    response=_request("places:searchText",data={"textQuery":q,"pageSize":10,"languageCode":"fr"},field_mask=_MASK)
    results=[item for place in response.get("places",[])[:10] if (item:=_convert(place))]
    return {"results":results,"source":"Google Maps / Places","cached":False}

def place_details(place_id):
    pid=str(place_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,220}",pid):raise ValueError("Identifiant Google Place invalide.")
    place=_request("places/"+quote(pid,safe=""),field_mask=_DETAIL_MASK)
    result=_convert(place)
    if not result:raise ValueError("Impossible de sélectionner cette entreprise Google Maps.")
    return {"business":result}

