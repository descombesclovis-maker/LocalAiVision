"""Free website detection for prospecting: OpenStreetMap 'website' tags + probable domain probing (verified by page content)."""
import asyncio
import logging
import math
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from lib.db import db

log = logging.getLogger(__name__)
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
STOP = {
    "sas", "sarl", "sa", "eurl", "sasu", "sci", "snc", "selarl", "selas", "scp", "earl", "gaec", "scop", "ste", "societe", "ets",
    "etablissements", "et", "de", "du", "des", "la", "le", "les", "l", "d", "au", "aux", "en", "france", "groupe", "holding", "sc",
}
PARKED = (
    "domain is for sale", "domaine est a vendre", "nom de domaine a vendre", "buy this domain", "this domain", "parked",
    "sedo", "hugedomains", "afternic", "dan.com", "for sale", "site en construction", "coming soon", "under construction", "domaine reserve", "page par defaut", "default page",
)
FRESH_DAYS = 30
_pending: set[str] = set()
_sem = asyncio.Semaphore(8)
_osm_down_until = 0.0


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", _ascii(name)) if len(t) >= 2 and t not in STOP]


def candidates(name: str, city: str) -> list[str]:
    t = tokens(name)[:4]
    if not t or len("".join(t)) < 4:
        return []
    joined, dashed = "".join(t), "-".join(t)
    c = "-".join(tokens(city)[:2])
    out = [f"{joined}.fr", f"{dashed}.fr", f"{joined}.com", f"{dashed}.com"]
    if c:
        out += [f"{joined}-{c}.fr", f"{dashed}-{c}.fr"]
    seen: list[str] = []
    for d in out:
        if d not in seen:
            seen.append(d)
    return seen[:6]


def _dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    dy = (a[0] - b[0]) * 110540
    return math.hypot(dx, dy)


def _name_match(a: str, b: str) -> bool:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return False
    common = ta & tb
    return len(common) >= max(1, min(len(ta), len(tb)) // 2) and any(len(w) >= 4 for w in common)


async def _osm(items: list[dict]) -> dict[str, str]:
    """One Overpass query for the whole batch bbox; returns siret -> website."""
    global _osm_down_until
    if not items or time.time() < _osm_down_until:
        return {}
    lats, lngs = [i["lat"] for i in items], [i["lng"] for i in items]
    pad = 0.002
    bbox = f"{min(lats) - pad},{min(lngs) - pad},{max(lats) + pad},{max(lngs) + pad}"
    q = f'[out:json][timeout:10];nwr["name"][~"^(website|contact:website|url)$"~"."]({bbox});out center tags;'
    for url in OVERPASS:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=5), headers={"User-Agent": "LocalAiStudio/1.0"}) as c:
                r = await c.post(url, data={"data": q})
                r.raise_for_status()
                elements = r.json().get("elements", [])
            break
        except Exception:
            continue
    else:
        _osm_down_until = time.time() + 300
        return {}
    pois = []
    for e in elements:
        tags = e.get("tags", {})
        lat, lng = e.get("lat") or e.get("center", {}).get("lat"), e.get("lon") or e.get("center", {}).get("lon")
        site = tags.get("website") or tags.get("contact:website") or tags.get("url")
        if lat and lng and site:
            pois.append((tags.get("name", ""), (lat, lng), site))
    found = {}
    for it in items:
        for name, pos, site in pois:
            if _dist_m((it["lat"], it["lng"]), pos) < 250 and _name_match(it["name"], name):
                found[it["siret"]] = site if site.startswith("http") else f"https://{site}"
                break
    return found


async def _probe(client: httpx.AsyncClient, domain: str, name: str) -> Optional[str]:
    t = tokens(name)[:3]
    for scheme in ("https://", "http://"):
        try:
            r = await client.get(f"{scheme}{domain}")
        except Exception:
            continue
        host = (r.url.host or "").removeprefix("www.")
        if "".join(t) not in host.replace("-", "") and host != domain:
            return None  # redirected to another site (marketplace, parking, unrelated brand)
        if r.status_code in (401, 403, 429, 503) and len("".join(t)) >= 6:
            return str(r.url)  # bot-protected but alive: the exact-name domain exists
        if r.status_code >= 400:
            return None
        text = _ascii(r.text[:300_000])
        if any(p in text for p in PARKED):
            return None
        if all(re.search(rf"\b{re.escape(w)}\b", text) for w in t):
            return str(r.url)
        return None
    return None


async def _domains(it: dict) -> Optional[str]:
    async with _sem:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6, connect=4), follow_redirects=True, headers={"User-Agent": UA}) as c:
            for d in candidates(it["name"], it.get("city", "")):
                url = await _probe(c, d, it["name"])
                if url:
                    return url
    return None


async def _save(siret: str, status: str, url: Optional[str], source: str) -> None:
    await db.company_web.update_one(
        {"siret": siret},
        {"$set": {"siret": siret, "status": status, "url": url, "source": source, "checked_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


async def _process(items: list[dict]) -> None:
    osm_task = asyncio.create_task(_osm(items))
    try:
        async def one(it: dict) -> None:
            try:
                url = await _domains(it)
                if url:
                    await _save(it["siret"], "found", url, "domain")
                elif osm_task.done() and it["siret"] not in osm_task.result():
                    await _save(it["siret"], "none", None, "")
                else:  # wait for OpenStreetMap before declaring "no website"
                    osm = await osm_task
                    if it["siret"] in osm:
                        await _save(it["siret"], "found", osm[it["siret"]], "osm")
                    else:
                        await _save(it["siret"], "none", None, "")
            except Exception as exc:
                log.warning("webcheck %s: %s", it["siret"], exc)
            finally:
                _pending.discard(it["siret"])

        await asyncio.gather(*(one(it) for it in items))
    finally:
        for it in items:
            _pending.discard(it["siret"])


async def statuses(items: list[dict]) -> list[dict]:
    sirets = [i["siret"] for i in items]
    limit = (datetime.now(timezone.utc) - timedelta(days=FRESH_DAYS)).isoformat()
    known = {d["siret"]: d async for d in db.company_web.find({"siret": {"$in": sirets}, "checked_at": {"$gte": limit}}, {"_id": 0})}
    todo = [i for i in items if i["siret"] not in known and i["siret"] not in _pending]
    if todo:
        _pending.update(i["siret"] for i in todo)
        asyncio.create_task(_process(todo))
    return [
        {"siret": s, "status": known[s]["status"], "url": known[s].get("url"), "source": known[s].get("source", "")}
        if s in known else {"siret": s, "status": "pending", "url": None, "source": ""}
        for s in sirets
    ]
