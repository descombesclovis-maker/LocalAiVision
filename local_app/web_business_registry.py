"""Optional public French business register enrichment after a human selects a map pin.

Use only open information with a strong commercial identity AND establishment
location match. An officer is not necessarily the owner. No personal/private
postal addresses, birth dates, direct personal contacts, or biographies.
Never build a dossier about a natural person.
"""
from __future__ import annotations
import math
import re
import threading
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json

API="https://recherche-entreprises.api.gouv.fr/search"
SOURCE="https://annuaire-entreprises.data.gouv.fr/"
_LOCK=threading.RLock()
_CACHE={}
_LAST=0.0


def clean(s,n=140):
    return re.sub(r"[\x00-\x1f\x7f]+"," ",str(s or "")).strip()[:n]


def norm(value):
    s=unicodedata.normalize("NFKD",str(value or "").lower())
    return re.sub(r"[^a-z0-9]+"," ", "".join(c for c in s if not unicodedata.combining(c))).strip()


def km(a,b,c,d):
    radians=list(map(math.radians,(float(a),float(b),float(c),float(d))))
    la1,lo1,la2,lo2=radians
    dl=la2-la1;dn=lo2-lo1
    z=math.sin(dl/2)**2+math.cos(la1)*math.cos(la2)*math.sin(dn/2)**2
    return 12742*math.asin(min(1,math.sqrt(z)))


def eligible(business):
    country=norm(business.get("country"))
    lat=float(business.get("lat") or 0)
    lon=float(business.get("lon") or 0)
    french_coords=(41.0<=lat<=51.7 and -5.8<=lon<=9.9)
    postcode=str(business.get("postcode") or "")
    if country and country not in ("france","fr","french republic","republique francaise"):
        return False
    return (country in ("france","fr","republique francaise") or
            french_coords and bool(re.fullmatch(r"\d{5}",postcode)))


def _query(name):
    global _LAST
    with _LOCK:
        if time.monotonic()-_LAST<2:
            raise RuntimeError("Service officiel sollicité trop rapidement.")
        _LAST=time.monotonic()
    url=API+"?"+urlencode({"q":name,"per_page":8,"page":1})
    req=Request(url,headers={
        "Accept":"application/json",
        "User-Agent":"LocalAiWeb/3.0 (public professional company registry lookup; https://github.com/descombesclovis-maker/LocalAiVision)"
    })
    with urlopen(req,timeout=15) as response:
        raw=response.read(1_000_001)
    if len(raw)>1_000_000:
        raise RuntimeError("Réponse trop volumineuse du registre public.")
    return json.loads(raw.decode("utf-8"))


def _locations(entry):
    sources=[entry.get("siege") or {}]+list(entry.get("matching_etablissements") or [])[:10]
    for location in sources:
        if isinstance(location,dict):
            yield location


def _match(entry,business):
    if not isinstance(entry,dict):return False
    label=norm(business.get("name"))
    # Require exact public business name, legal name OR declared local trade name.
    identifiers=[entry.get("nom_complet"),entry.get("nom_raison_sociale"),entry.get("sigle")]
    for office in _locations(entry):
        identifiers += [office.get("nom_commercial")]
        identifiers += office.get("liste_enseignes") or []
    if not label or not any(norm(x)==label for x in identifiers if x):
        return False
    for office in _locations(entry):
        try:
            lat=office.get("latitude");lon=office.get("longitude")
            if lat is not None and lon is not None and km(
                lat,lon,business["lat"],business["lon"])<1.7:
                return True
        except (TypeError,ValueError,KeyError):pass
        # Business name matched exactly; require a *specific* establishment
        # address to avoid mistaking a large company's HQ for a local shop.
        postcode=clean(business.get("postcode"),16)
        if postcode and str(office.get("code_postal") or "")==postcode:
            town=norm(business.get("city"))
            office_town=norm(office.get("libelle_commune"))
            if town and office_town and town==office_town:
                return True
    return False


def professional_profile(business):
    """Return a minimal business profile, never a general personal profile."""
    if not eligible(business):
        return {"matched":False,"message":"Recherche du registre français non disponible pour cette fiche."}
    label=clean(business.get("name"),80)
    if len(label)<3:
        return {"matched":False,"message":"Nom d'entreprise insuffisant pour une vérification fiable."}
    key=(norm(label),round(float(business.get("lat")),3),round(float(business.get("lon")),3))
    with _LOCK:
        stored=_CACHE.get(key)
        if stored and time.monotonic()-stored[0]<900:
            return dict(stored[1])
    try:
        records=_query(label)
    except Exception:
        return {"matched":False,"message":"Registre officiel temporairement indisponible."}
    options=[x for x in records.get("results",[])[:8] if _match(x,business)]
    if len(options)!=1:
        return {"matched":False,"message":"Aucune correspondance juridique unique et certaine. Données non attribuées."}
    entry=options[0]
    officers=[]
    for p in entry.get("dirigeants") or []:
        if not isinstance(p,dict):continue
        role=clean(p.get("qualite"),55)
        if p.get("type_dirigeant")=="personne morale":
            title=clean(p.get("denomination"),90)
        else:
            title=clean((str(p.get("prenoms") or "")+" "+str(p.get("nom") or "")).strip(),90)
        if title and role:
            officers.append({"name":title,"role":role})
        if len(officers)>=2:break
    siren=clean(entry.get("siren"),11)
    if not re.fullmatch(r"\d{9}",siren):
        return {"matched":False,"message":"Identifiant légal non validé."}
    result={
      "matched":True,"legal_name":clean(entry.get("nom_complet"),100),
      "siren":siren,"naf":clean(entry.get("activite_principale"),20),
      "created":clean(entry.get("date_creation"),20),
      "legal_status":clean(entry.get("nature_juridique"),30),
      "officers":officers,
      "source":SOURCE+siren,
      "disclaimer":"Dirigeants déclarés dans un registre professionnel : ils ne sont pas nécessairement propriétaires. Données à vérifier."
    }
    with _LOCK:
        if len(_CACHE)>50:_CACHE.clear()
        _CACHE[key]=(time.monotonic(),result)
    return result
