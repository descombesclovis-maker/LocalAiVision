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

from local_app import web_business_map, web_prospect_filter

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
FRANCE_BATCH_SIZE=5
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
    if not web_prospect_filter.eligible({
        "name":tags["name"],"website_recorded":bool(website_raw),
        "osm_category":category,"brand":tags.get("brand"),
        "operator":tags.get("operator"),"network":tags.get("network")
    }):
        return None
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
        "brand":tags.get("brand"),"network":tags.get("network"),
        "wikidata":tags.get("wikidata"),
        "website":safe_website(website_raw),
        "image_url":web_business_map._commons_photo(tags),
        "image_credit":"Photo Wikimedia Commons — licence à vérifier" if web_business_map._commons_photo(tags) else "",
        "source":"overpass",
    })
    if info:
        info["website_status"]=("renseigne_osm" if website_raw else "non_renseigne_osm")
        info["website_recorded"]=bool(website_raw)
        info["website_link_available"]=bool(info.get("website"))
        info["prospect_eligible"]=True
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
                "overpass" if index==0 else "overpass_backup" if index==1 else "overpass_backup2",
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
            "website_status":"non_renseigne_osm",
            "website_verified":False,
            "notice":"Petits commerces sans site renseigné dans OSM (absence non confirmée). Enseignes nationales écartées ; données partielles.",
            "source":"OpenStreetMap / Overpass","cached":False,"offline":source_offline}
    with LOCK:
        if len(CACHE)>70:CACHE.clear()
        CACHE[key]=(time.monotonic(),result)
    return result


def _french_registry_near(lat,lon,radius=2.5,pages=1):
    """Real, geocoded companies from the official French public directory.

    More pages are fetched only after the user zooms into a town. A 25-company
    page limit was the root cause of 10-16 visible businesses per city.
    Data are cached locally for three days; no Google Places listings stored.
    """
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
    la,lo=web_business_map._position(lat,lon)
    if not (41.2<=la<=51.5 and -5.9<=lo<=9.9):
        raise ValueError("L'annuaire professionnel couvre la France uniquement.")
    radius=max(.5,min(float(radius),5))
    pages=max(1,min(int(pages),4))
    all_companies=[]
    cache_hits=0
    for number in range(1,pages+1):
        key=("registry-"+str(round(la,3))+"-"+str(round(lo,3))+"-"+
             str(round(radius,1))+"-page"+str(number))
        file=CACHE_DIR/(key+".json")
        raw=None
        try:
            if file.is_file() and time.time()-file.stat().st_mtime<3*86400:
                cached=json.loads(file.read_text(encoding="utf-8"))
                if isinstance(cached.get("results"),list):
                    raw=cached
                    cache_hits+=1
            if raw is None:
                args=urlencode({"lat":la,"long":lo,"radius":radius,
                     "page":number,"per_page":25,
                     # Prefer local retail, services, restaurants and trades.
                     "section_activite_principale":"G,I,S,F,M,N"})
                with urlopen(Request(
                  "https://recherche-entreprises.api.gouv.fr/near_point?"+args,
                  headers={"User-Agent":web_business_map.CONTACT,
                           "Accept":"application/json"}),timeout=9) as response:
                    payload=response.read(900001)
                    if len(payload)>900000:raise ValueError("Annuaire trop volumineux.")
                    raw=json.loads(payload)
                if not isinstance(raw.get("results"),list):
                    raise ValueError("Réponse de l'annuaire invalide.")
                try:
                    CACHE_DIR.mkdir(parents=True,exist_ok=True)
                    tmp=file.with_suffix(".tmp")
                    tmp.write_text(json.dumps(raw,ensure_ascii=False),encoding="utf-8")
                    tmp.replace(file)
                except (OSError,TypeError):pass
        except Exception:
            try:
                raw=json.loads(file.read_text(encoding="utf-8"))
                if not isinstance(raw.get("results"),list):
                    raise ValueError("Cache invalide")
                cache_hits+=1
            except (OSError,ValueError,TypeError):
                if not all_companies:
                    raise RuntimeError("Annuaire officiel temporairement indisponible.") from None
                break
        all_companies.extend((raw.get("results") or [])[:25])
        # The API declares total_pages: don't make useless page requests.
        if number>=int(raw.get("total_pages") or 1000):
            break
    rows=[]
    seen=set()
    for company in all_companies:
        if not isinstance(company,dict):continue
        if company.get("etat_administratif") not in (None,"A"):continue
        places=list(company.get("matching_etablissements") or [])
        if isinstance(company.get("siege"),dict):
            places.append(company["siege"])
        for location in places:
            if not isinstance(location,dict):continue
            if location.get("etat_administratif") not in (None,"A"):continue
            try:
                y=float(location.get("latitude"))
                x=float(location.get("longitude"))
            except (ValueError,TypeError):continue
            if abs(y-la)>radius/85 or abs(x-lo)>radius/50:continue
            siret=str(location.get("siret") or "")
            if len(siret)!=14 or not siret.isdigit() or siret in seen:continue
            seen.add(siret)
            item=web_business_map._result({
                "name":location.get("nom_commercial") or
                       ((location.get("liste_enseignes") or [""])[0]) or
                       company.get("nom_complet") or company.get("nom_raison_sociale"),
                "siret":siret,
                "establishment_created":(location.get("date_creation") or
                                         location.get("date_creation_etablissement") or ""),
                "lat":y,"lon":x,"osm_id":"siret/"+siret,
                "category":str(location.get("activite_principale") or "entreprise"),
                "address":location.get("adresse") or "",
                "city":location.get("libelle_commune") or "",
                "postcode":location.get("code_postal") or "",
                "source":"french_registry",
                "company_size":company.get("categorie_entreprise") or "",
                "workforce_band":(location.get("tranche_effectif_salarie") or
                                  company.get("tranche_effectif_salarie") or ""),
                "establishment_count":company.get("nombre_etablissements") or 0,
                "naf_code":location.get("activite_principale") or "",
                "brand":location.get("enseigne_1") or ""})
            if not item or not web_prospect_filter.eligible(item):continue
            item["prospect_eligible"]=True
            item["website_recorded"]=False
            item["website_status"]="inconnu_registre"
            item["website_link_available"]=False
            item["website_verified"]=False
            rows.append(item)
            break
    return {"results":rows,"partial":True,"mode":"official_french_registry",
            "source":"API Recherche d'entreprises / data.gouv.fr",
            "website_verified":False,"website_status":"inconnu_registre",
            "notice":"Commerces et artisans déclarés, informations publiques "
                     "non exhaustives. Présence de site internet inconnue.",
            "cached":cache_hits>0,"offline":False,"fallback":True}


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
    # Distribute real, geocoded establishments across five distinct zones
    # per batch rather than requesting only one city, which caused a nearly
    # empty France map. Concurrency is capped for the public official API.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results=[]
    errors=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(_french_registry_near,lat,lon,2.5,3) for lat,lon in centers]
        for future in as_completed(futures):
            try:
                result=future.result()
                results.extend(result["results"])
            except Exception as exc:
                errors.append(str(exc))
    if not results:
        # Keep the actual OSM fallback; never fabricate company coordinates.
        result=_load(key,statement,"france_overview")
    else:
        seen=set()
        unique=[]
        for company in results:
            if company["id"] not in seen:
                unique.append(company);seen.add(company["id"])
        result={"results":unique,"partial":True,"mode":"official_french_registry",
                "source":"API Recherche d'entreprises / data.gouv.fr",
                "website_verified":False,"website_status":"inconnu_registre",
                "notice":"Petites entreprises présumées indépendantes, sans site répertorié (à confirmer). Échantillonnage progressif. "
                         "Ce chargement ne contient pas tous les établissements français.",
                "cached":False,"fallback":True,"offline":False}
    result["batch"]=number
    result["total_batches"]=FRANCE_BATCH_COUNT
    result["next_batch"]=number+1 if number+1<FRANCE_BATCH_COUNT else None
    return result


def registry_city(lat,lon,zoom):
    """Direct official SIRENE-powered lookup, no Overpass startup timeout."""
    la,lo=web_business_map._position(lat,lon)
    z=int(zoom)
    if z<8 or z>20:
        raise ValueError("Zoome sur une ville pour voir les commerces de proximité.")
    radius=3.5 if z<=10 else 2.5 if z<=12 else 1.5 if z<=14 else .8
    return _french_registry_near(la,lo,radius,pages=3)


def area_details(lat,lon,zoom):
    la,lo=web_business_map._position(lat,lon)
    z=int(zoom)
    if z<8 or z>19:
        raise ValueError("Zoome légèrement sur la carte (niveau 8 minimum).")
    radius=5000 if z<=10 else 3000 if z==11 else 1800 if z==12 else 1100 if z==13 else 700
    key=("nearby",round(la,3),round(lo,3),radius)
    statement=(
        "[out:json][timeout:24];"
        f'nwr(around:{radius},{la},{lo})["name"]'
        f'{BUSINESS_TAG};out center 220;'
    )
    try:
        return _load(key,statement,"nearby")
    except RuntimeError as exc:
        if "recharge progressivement" in str(exc):
            raise
        return _french_registry_near(la,lo,radius=min(4,radius/1000),pages=3)


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
    try:
        return _load(key,statement,"viewport")
    except RuntimeError as exc:
        if "recharge progressivement" in str(exc):
            raise
        return _french_registry_near((la1+la2)/2,(lo1+lo2)/2,1.5,pages=3)
