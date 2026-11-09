"""French companies from the official, free 'API Recherche d'entreprises' (no key) + API Adresse geocoding."""
import asyncio
import logging
import time
from datetime import date, datetime
from typing import Optional

import httpx

from lib.dates import today_iso
from lib.db import db

API = "https://recherche-entreprises.api.gouv.fr"
GEO = "https://api-adresse.data.gouv.fr/search/"
log = logging.getLogger(__name__)


def today() -> date:
    return date.fromisoformat(today_iso("Europe/Paris"))

SECTIONS = {
    "A": "Agriculture, sylviculture, pêche", "B": "Industries extractives", "C": "Industrie manufacturière",
    "D": "Énergie", "E": "Eau, déchets, dépollution", "F": "Construction, artisans du bâtiment",
    "G": "Commerce, réparation auto", "H": "Transports et entreposage", "I": "Hôtellerie et restauration",
    "J": "Information et communication", "K": "Finance et assurance", "L": "Immobilier",
    "M": "Activités spécialisées, scientifiques, techniques", "N": "Services administratifs et de soutien",
    "O": "Administration publique", "P": "Enseignement", "Q": "Santé humaine et action sociale",
    "R": "Arts, spectacles, loisirs", "S": "Autres services (coiffure, beauté, réparation…)",
    "T": "Ménages employeurs", "U": "Organisations extraterritoriales",
}
EFFECTIFS = {
    "NN": "Non employeuse", "00": "0 salarié", "01": "1 à 2 salariés", "02": "3 à 5 salariés", "03": "6 à 9 salariés",
    "11": "10 à 19 salariés", "12": "20 à 49 salariés", "21": "50 à 99 salariés", "22": "100 à 199 salariés",
    "31": "200 à 249 salariés", "32": "250 à 499 salariés", "41": "500 à 999 salariés", "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés", "52": "5 000 à 9 999 salariés", "53": "10 000 salariés et plus",
}
EFFECTIF_MIN = {"11": 10, "12": 20, "21": 50, "22": 100, "31": 200, "32": 250, "41": 500, "42": 1000, "51": 2000, "52": 5000, "53": 10000}
CATEGORIES = {"PME": "PME", "ETI": "Entreprise de taille intermédiaire", "GE": "Grande entreprise"}
LABELS = {
    "est_rge": "Certifiée RGE (Reconnu Garant de l'Environnement)", "est_qualiopi": "Certifiée Qualiopi",
    "est_bio": "Professionnel certifié bio", "est_ess": "Entreprise de l'économie sociale et solidaire",
    "est_patrimoine_vivant": "Label Entreprise du Patrimoine Vivant", "est_societe_mission": "Société à mission",
    "est_entrepreneur_spectacle": "Entrepreneur de spectacles", "est_siae": "Structure d'insertion par l'activité économique",
}

# Préfectures of metropolitan departments — seeds of the national overview.
DEPARTMENTS: dict[str, tuple[float, float]] = {
    "01": (46.205, 5.225), "02": (49.564, 3.620), "03": (46.566, 3.333), "04": (44.092, 6.236), "05": (44.559, 6.079),
    "06": (43.710, 7.262), "07": (44.735, 4.599), "08": (49.773, 4.720), "09": (42.965, 1.607), "10": (48.297, 4.074),
    "11": (43.212, 2.353), "12": (44.350, 2.575), "13": (43.296, 5.370), "14": (49.183, -0.370), "15": (44.926, 2.440),
    "16": (45.648, 0.156), "17": (46.160, -1.151), "18": (47.081, 2.399), "19": (45.267, 1.772), "21": (47.322, 5.041),
    "22": (48.514, -2.765), "23": (46.171, 1.871), "24": (45.184, 0.721), "25": (47.238, 6.024), "26": (44.933, 4.892),
    "27": (49.024, 1.151), "28": (48.446, 1.489), "29": (47.996, -4.102), "2A": (41.919, 8.738), "2B": (42.697, 9.450),
    "30": (43.837, 4.360), "31": (43.605, 1.444), "32": (43.646, 0.586), "33": (44.838, -0.579), "34": (43.611, 3.877),
    "35": (48.117, -1.678), "36": (46.811, 1.691), "37": (47.394, 0.685), "38": (45.188, 5.724), "39": (46.675, 5.555),
    "40": (43.890, -0.500), "41": (47.586, 1.336), "42": (45.440, 4.387), "43": (45.043, 3.885), "44": (47.218, -1.554),
    "45": (47.903, 1.909), "46": (44.448, 1.441), "47": (44.203, 0.616), "48": (44.518, 3.500), "49": (47.478, -0.563),
    "50": (49.116, -1.090), "51": (48.957, 4.363), "52": (48.111, 5.139), "53": (48.073, -0.770), "54": (48.692, 6.184),
    "55": (48.772, 5.160), "56": (47.658, -2.760), "57": (49.119, 6.176), "58": (46.990, 3.159), "59": (50.629, 3.057),
    "60": (49.430, 2.081), "61": (48.432, 0.091), "62": (50.291, 2.777), "63": (45.778, 3.087), "64": (43.295, -0.371),
    "65": (43.233, 0.078), "66": (42.699, 2.895), "67": (48.573, 7.752), "68": (48.079, 7.358), "69": (45.764, 4.836),
    "70": (47.622, 6.155), "71": (46.307, 4.828), "72": (48.006, 0.199), "73": (45.564, 5.917), "74": (45.899, 6.129),
    "75": (48.857, 2.352), "76": (49.443, 1.099), "77": (48.539, 2.661), "78": (48.801, 2.130), "79": (46.323, -0.464),
    "80": (49.894, 2.296), "81": (43.929, 2.148), "82": (44.018, 1.355), "83": (43.124, 5.928), "84": (43.949, 4.806),
    "85": (46.670, -1.426), "86": (46.580, 0.340), "87": (45.834, 1.261), "88": (48.172, 6.449), "89": (47.798, 3.567),
    "90": (47.638, 6.863), "91": (48.629, 2.441), "92": (48.892, 2.207), "93": (48.908, 2.439), "94": (48.790, 2.455),
    "95": (49.036, 2.063),
}

_client = httpx.AsyncClient(timeout=httpx.Timeout(20, connect=8), headers={"User-Agent": "LocalAiStudio/1.0"})
_sem = asyncio.Semaphore(4)  # official API allows ~7 req/s
_cache: dict[str, tuple[float, list[dict]]] = {}
_overview_task: Optional[asyncio.Task] = None


async def _get(url: str, params: dict) -> dict:
    for attempt in range(3):
        async with _sem:
            r = await _client.get(url, params=params)
        if r.status_code == 429:
            await asyncio.sleep(1.2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Le service officiel des entreprises est saturé, réessayez dans quelques secondes")


def _title(s: str) -> str:
    return " ".join(w if len(w) <= 3 and w.isupper() and w in {"SAS", "SARL", "SA", "EURL", "SCI"} else w.capitalize() for w in (s or "").split())


def display_name(r: dict, etab: Optional[dict] = None) -> str:
    ens = (etab or {}).get("liste_enseignes") or (etab or {}).get("nom_commercial") or r.get("siege", {}).get("liste_enseignes")
    if isinstance(ens, list):
        ens = ens[0] if ens else None
    return _title(ens or r.get("nom_raison_sociale") or r.get("nom_complet") or "Entreprise")


def _points(results: list[dict]) -> list[dict]:
    pts: dict[str, dict] = {}
    for r in results:
        for e in r.get("matching_etablissements") or [r.get("siege") or {}]:
            if e.get("etat_administratif") != "A" or not e.get("latitude") or not e.get("longitude"):
                continue
            naf = e.get("activite_principale") or r.get("activite_principale") or ""
            pts[e["siret"]] = {
                "siren": r["siren"], "siret": e["siret"], "name": display_name(r, e),
                "lat": float(e["latitude"]), "lng": float(e["longitude"]), "naf": naf,
                "section": r.get("section_activite_principale") or "", "address": e.get("adresse") or "",
                "city": _title(e.get("libelle_commune") or ""), "effectif": EFFECTIFS.get(e.get("tranche_effectif_salarie") or "", ""),
                "is_siege": bool(e.get("est_siege")),
            }
    return list(pts.values())


async def near(lat: float, lng: float, radius: float, section: str = "", pages: int = 4) -> list[dict]:
    key = f"{lat:.3f}|{lng:.3f}|{radius:.1f}|{section}|{pages}"
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 1800:
        return hit[1]
    params = {"lat": lat, "long": lng, "radius": radius, "per_page": 25, "etat_administratif": "A"}
    if section:
        params["section_activite_principale"] = section
    first = await _get(f"{API}/near_point", {**params, "page": 1})
    total_pages = min(pages, first.get("total_pages") or 1)
    rest = await asyncio.gather(*(_get(f"{API}/near_point", {**params, "page": n}) for n in range(2, total_pages + 1)), return_exceptions=True)
    results = first.get("results", []) + [x for d in rest if isinstance(d, dict) for x in d.get("results", [])]
    pts = _points(results)
    if len(_cache) > 400:
        _cache.clear()
    _cache[key] = (time.time(), pts)
    return pts


async def _build_overview() -> None:
    for dep, (lat, lng) in DEPARTMENTS.items():
        try:
            pts = await near(lat, lng, 6, pages=1)
            await db.company_overview.update_one({"dep": dep}, {"$set": {"dep": dep, "points": pts, "day": today().isoformat()}}, upsert=True)
        except Exception as exc:  # one department failing must not stop the map
            log.warning("overview %s failed: %s", dep, exc)


async def overview() -> dict:
    """Sample of real companies around every préfecture, cached in Mongo and refreshed weekly."""
    global _overview_task
    docs = await db.company_overview.find({}, {"_id": 0}).to_list(200)
    fresh = [d for d in docs if (today() - datetime.fromisoformat(d["day"]).date()).days < 7]
    if len(fresh) < len(DEPARTMENTS) and (_overview_task is None or _overview_task.done()):
        _overview_task = asyncio.create_task(_build_overview())
    points = [p for d in docs for p in d["points"]]
    return {"points": points, "departments_ready": len(docs), "departments_total": len(DEPARTMENTS)}


async def geocode(q: str) -> list[dict]:
    data = await _get(GEO, {"q": q, "limit": 5})
    return [
        {"label": f["properties"]["label"], "lat": f["geometry"]["coordinates"][1], "lng": f["geometry"]["coordinates"][0],
         "type": f["properties"].get("type", "")}
        for f in data.get("features", [])
    ]


def _juridique(code: str) -> str:
    c = str(code or "")
    for prefix, label in (("1", "Entrepreneur individuel"), ("5499", "SARL"), ("5498", "EURL"), ("5710", "SAS"), ("5720", "SASU"),
                          ("54", "SARL"), ("57", "SAS"), ("55", "SA"), ("56", "SA"), ("65", "Société civile"), ("92", "Association"), ("7", "Organisme public")):
        if c.startswith(prefix):
            return label
    return f"Forme juridique {c}" if c else ""


def guess_site_type(naf: str) -> str:
    if naf.startswith("56") or naf.startswith("55"):
        return "restaurant"
    if naf.startswith("68"):
        return "immobilier"
    if naf.startswith("47"):
        return "boutique"
    return "services"


def _strengths(r: dict) -> list[str]:
    out: list[str] = []
    s = r.get("siege") or {}
    if s.get("libelle_commune"):
        out.append(f"Implantée à {_title(s['libelle_commune'])} ({s.get('code_postal','')}), ancrage local")
    if r.get("date_creation"):
        year = int(r["date_creation"][:4])
        age = today().year - year
        if age >= 2:
            out.append(f"Fondée en {year} : {age} ans d'expérience")
    tr = r.get("tranche_effectif_salarie") or ""
    if tr in EFFECTIF_MIN:
        out.append(f"Équipe de {EFFECTIFS[tr].lower()}")
    if (r.get("nombre_etablissements_ouverts") or 0) > 1:
        out.append(f"{r['nombre_etablissements_ouverts']} établissements ouverts")
    comp = r.get("complements") or {}
    out += [label for k, label in LABELS.items() if comp.get(k)]
    fin = r.get("finances") or {}
    years = sorted(fin.keys())
    if len(years) >= 2:
        a, b = fin[years[-2]].get("ca"), fin[years[-1]].get("ca")
        if a and b and b > a:
            out.append(f"Chiffre d'affaires en croissance de {round((b - a) / a * 100)} % ({years[-2]} → {years[-1]})")
    return out


def _dirigeants(r: dict) -> list[str]:
    out = []
    for d in (r.get("dirigeants") or [])[:6]:
        if d.get("type_dirigeant") == "personne physique":
            name = f"{_title(d.get('prenoms','').split(' ')[0])} {_title(d.get('nom',''))}".strip()
        else:
            name = _title(d.get("denomination") or "")
        if name:
            out.append(f"{name} — {d['qualite']}" if d.get("qualite") else name)
    return out


async def detail(siren: str) -> Optional[dict]:
    data = await _get(f"{API}/search", {"q": siren, "per_page": 1})
    r = next((x for x in data.get("results", []) if x.get("siren") == siren), None)
    if not r:
        return None
    s = r.get("siege") or {}
    fin = r.get("finances") or {}
    last = sorted(fin.keys())[-1] if fin else None
    naf = r.get("activite_principale") or ""
    return {
        "siren": siren, "siret": s.get("siret") or "", "name": display_name(r), "legal_name": _title(r.get("nom_complet") or ""),
        "naf": naf, "section": r.get("section_activite_principale") or "", "section_label": SECTIONS.get(r.get("section_activite_principale") or "", ""),
        "address": s.get("adresse") or "", "city": _title(s.get("libelle_commune") or ""), "postal_code": s.get("code_postal") or "",
        "lat": float(s["latitude"]) if s.get("latitude") else None, "lng": float(s["longitude"]) if s.get("longitude") else None,
        "created": r.get("date_creation") or "", "legal_form": _juridique(r.get("nature_juridique")),
        "category": CATEGORIES.get(r.get("categorie_entreprise") or "", ""), "effectif": EFFECTIFS.get(r.get("tranche_effectif_salarie") or "", ""),
        "establishments": r.get("nombre_etablissements_ouverts") or 0, "directors": _dirigeants(r),
        "revenue": fin[last].get("ca") if last else None, "net_result": fin[last].get("resultat_net") if last else None,
        "finance_year": last, "strengths": _strengths(r), "site_type": guess_site_type(naf),
        "active": r.get("etat_administratif") == "A",
    }


def site_prompt(c: dict) -> str:
    money = f"{c['revenue']:,} €".replace(",", " ") if c.get("revenue") else "non publié"
    facts = "\n".join(f"- {s}" for s in c["strengths"]) or "- (aucun atout officiel détecté : déduis-les du métier et de la ville)"
    return f"""Crée le site web professionnel de l'entreprise française RÉELLE suivante (données officielles SIRENE, ne pose aucune question).
Entreprise : {c['name']} ({c['legal_name']}, {c['legal_form']}) · SIREN {c['siren']}
Activité : code NAF {c['naf']} · {c['section_label']}
Adresse : {c['address']}
Création : {c['created']} · Effectif : {c['effectif'] or 'non renseigné'} · {c['category']}
Dirigeants : {', '.join(c['directors'][:3]) or 'non diffusés'}
Chiffre d'affaires {c.get('finance_year') or ''} : {money}
ATOUTS VÉRIFIÉS :
{facts}

MISSION : identifie d'abord les MEILLEURS ARGUMENTS DE VENTE de cette entreprise : ses atouts vérifiés ci-dessus + les bénéfices clients typiques de son métier et de sa zone ({c['city']}) + ce qui la différencie de ses concurrents locaux. Mets-les en scène : hero percutant avec promesse claire, section « Pourquoi nous choisir », preuves (ancienneté, labels, équipe), parcours vers la prise de contact / devis / réservation, appels à l'action répétés, référencement local (ville dans les titres).
N'invente ni faux avis chiffrés, ni fausses certifications, ni faux numéros : les contenus incertains (téléphone, e-mail, horaires, tarifs) sont des exemples plausibles marqués « à personnaliser »."""[:3990]
