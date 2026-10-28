"""Local, independently sourced French business index and daily prospect shortlist.

Records are public, diffusible business facts from SIRENE / OSM, NOT Google
Places data. A place's website missing from these sources is unknown, never
proof that the company has no online presence.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import time

_LOCK=threading.RLock()
_LIMIT=35000
_FIELDS=("id","name","lat","lon","address","city","postcode","country",
         "siret","category","osm_category","phone","email","website",
         "opening_hours","description","operator","source","image_url",
         "image_credit","establishment_created","website_status","website_recorded")

def database_path():
    root=Path(os.environ.get("LOCALVISIONAI_DATA",
         str(Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"LocalVisionAI")))
    return root/"localaiweb"/"prospects.sqlite3"

def _db():
    path=database_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(path),timeout=15)
    con.execute("pragma busy_timeout=10000")
    con.execute("create table if not exists companies (id text primary key, "
                "lat real not null, lon real not null, name text not null, "
                "payload text not null, updated real not null)")
    con.execute("create index if not exists ix_lat_lon on companies(lat,lon)")
    return con

def save(rows):
    """Bounded SQLite upsert, deduplicated by official SIRET/OSM identifier."""
    payload=[]
    now=time.time()
    for row in rows or []:
        if not isinstance(row,dict) or not row.get("id") or not row.get("name"):
            continue
        try:
            lat,lon=float(row["lat"]),float(row["lon"])
        except (KeyError,ValueError,TypeError):
            continue
        if not (41.0<=lat<=51.9 and -6.0<=lon<=10.2):
            continue
        record={key:row.get(key) for key in _FIELDS if row.get(key) not in (None,"")}
        record["lat"]=lat
        record["lon"]=lon
        # Never store the short-lived selection token in the persistent index.
        record.pop("selection_token",None)
        payload.append((str(row["id"])[:90],lat,lon,str(row["name"])[:100],
                        json.dumps(record,ensure_ascii=False),now))
    if not payload:return 0
    with _LOCK, _db() as con:
        con.executemany("insert into companies (id,lat,lon,name,payload,updated) "
                        "values (?,?,?,?,?,?) on conflict(id) do update set "
                        "lat=excluded.lat,lon=excluded.lon,name=excluded.name,"
                        "payload=excluded.payload,updated=excluded.updated",payload)
        count=con.execute("select count(*) from companies").fetchone()[0]
        if count>_LIMIT:
            con.execute("delete from companies where id in (select id from companies "
                        "order by updated asc limit ?)",(count-_LIMIT,))
    return len(payload)

def browse(limit=12000, south=40.8,west=-6.2,north=52,east=10.3):
    limit=max(1,min(int(limit),15000))
    south,west,north,east=map(float,(south,west,north,east))
    if south>=north or west>=east or north-south>15 or east-west>19:
        raise ValueError("Limites géographiques invalides.")
    with _LOCK,_db() as con:
        records=con.execute("select payload from companies "
           "where lat between ? and ? and lon between ? and ? "
           "order by updated desc limit ?",(south,north,west,east,limit)).fetchall()
        total=con.execute("select count(*) from companies").fetchone()[0]
    from local_app import web_business_map
    results=[]
    for (raw,) in records:
        info=json.loads(raw)
        # Re-mint an expiring click-selection token; never trust a token
        # serialized in persistent JSON.
        fresh=web_business_map._result({
            **info,"osm_id":info["id"],
            "source":("french_registry" if "data.gouv" in info.get("source","")
                      else "overpass"),
        })
        if fresh:
            fresh.update({k:v for k,v in info.items() if k not in ("selection_token","id")})
            results.append(fresh)
    return {"results":results,"count":total,"partial":total>limit,
            "source":"Annuaire français + OpenStreetMap, index local",
            "website_verified":False}

def _score(row,day):
    activity=(str(row.get("category") or "")+" "+
              str(row.get("osm_category") or "")).lower()
    # Sector preferences are explicit, not a fabricated success probability.
    keywords=("hairdress","coiff","boulanger","bakery","beauty","florist",
              "fleur","artisan","pet_","clothes","restaurant","cafe",
              "96.02","47.","56.","43.")
    sector=40 if any(x in activity for x in keywords) else 12
    site=18 if not row.get("website") else 0
    details=3*sum(bool(row.get(k)) for k in ("city","address","phone","email"))
    fresh=0
    created=row.get("establishment_created") or ""
    try:
        date=datetime.date.fromisoformat(str(created)[:10])
        delta=(day-date).days
        if 0<=delta<=180:fresh=45
        elif 181<=delta<=720:fresh=14
    except (ValueError,TypeError):pass
    tie=int(hashlib.sha256((day.isoformat()+str(row["id"])).encode()).hexdigest()[:8],16)%17
    return sector+site+details+fresh+tie

def daily(today=None,limit=5):
    day=today or datetime.date.today()
    limit=max(1,min(int(limit),5))
    with _LOCK,_db() as con:
        # Public index only, no web scraping or personal demographic scoring.
        values=con.execute("select payload from companies order by updated desc limit 35000").fetchall()
    candidates=[]
    for (value,) in values:
        try:r=json.loads(value)
        except ValueError:continue
        if not r.get("name") or not r.get("id"):continue
        candidates.append((_score(r,day),r))
    candidates.sort(key=lambda pair:(-pair[0],pair[1]["id"]))
    selected=[]
    cities=set()
    for _,row in candidates:
        city=str(row.get("city") or "").lower()
        if city and city in cities:continue
        if city:cities.add(city)
        selected.append(row)
        if len(selected)>=limit:break
    if len(selected)<limit:
        present={r["id"] for r in selected}
        for _,row in candidates:
            if row["id"] not in present:
                selected.append(row);present.add(row["id"])
            if len(selected)>=limit:break
    from local_app import web_business_map
    results=[]
    for row in selected:
        fresh=0
        try:
            date=datetime.date.fromisoformat(str(row.get("establishment_created") or "")[:10])
            fresh=(day-date).days
        except ValueError:pass
        reasons=[]
        if 0<fresh<=180:
            reasons.append("Établissement récent (date déclarée à vérifier)")
        if not row.get("website"):
            reasons.append("Site non renseigné dans la source — à vérifier")
        reasons.append("Activité locale susceptible de bénéficier d'une identité numérique")
        result=web_business_map._result({
            **row,"osm_id":row["id"],
            "source":"french_registry" if "data.gouv" in str(row.get("source")) else "overpass"})
        if result:
            result.update({k:v for k,v in row.items() if k!="selection_token"})
            result["selection_token"]=result["selection_token"]
            result["reason"]=" · ".join(reasons)
            result["score"]=_score(row,day)
            results.append(result)
    return {"date":day.isoformat(),"results":results,"pool":len(candidates),
            "notice":"Sélection indicative sur des données publiques disponibles, "
                     "pas une prédiction de propension à acheter ni la preuve "
                     "d'une absence de site."}
