"""LocalAiWeb engine: 6-step generation pipeline, QA + targeted auto-fix, chat edits, rendering."""
import asyncio
import json
import logging
import re
import subprocess
import tempfile
from typing import Optional

import httpx

from lib.db import db
from lib import comfy, gpu_queue, premium
from lib.llm import apply_edit, complete, friendly_error, generate_image, parse_edits, parse_files, parse_json
from lib.store import create_media, finish_media, media_url, new_id, now_iso

log = logging.getLogger("pipeline")
TASKS: set[asyncio.Task] = set()

STEPS = [
    ("analyse", "Analyse de la demande"),
    ("architecture", "Architecture & parcours"),
    ("direction", "Direction artistique"),
    ("images", "Création des images"),
    ("generation", "Génération du site"),
    ("qa", "Contrôle qualité"),
]
CREDIT = "Site web créé par Forma"
LEGAL = [("mentions-legales.html", "Mentions légales"), ("confidentialite.html", "Confidentialité")]

SYS_JSON = (
    "Tu es directeur de création et stratège web senior d'une agence premium. "
    "Tu réponds UNIQUEMENT par un objet JSON valide, sans texte autour."
)
SYS_CODE = (
    "Tu es un développeur front-end et designer d'exception (niveau Awwwards). Tu écris du HTML5 sémantique, "
    "du CSS moderne (variables, grid, clamp, container queries si utile) et du JavaScript vanilla robuste, sans framework. "
    "Chaque site est unique : aucune mise en page générique, aucun gabarit figé, typographie expressive, rythme asymétrique, "
    "micro-interactions soignées, accessibilité et responsive mobile impeccables. Tu respectes STRICTEMENT le format de sortie demandé."
)


def spawn(coro) -> None:
    t = asyncio.create_task(coro)
    TASKS.add(t)
    t.add_done_callback(TASKS.discard)


def files_map(p: dict) -> dict[str, str]:
    return {f["path"]: f["content"] for f in p.get("files", [])}


def files_list(m: dict[str, str]) -> list[dict]:
    order = lambda k: (0 if k == "index.html" else 1 if k.endswith(".html") and not k.startswith("_") else 2, k)
    return [{"path": k, "content": m[k]} for k in sorted(m, key=order)]


def pages_from(m: dict[str, str]) -> list[dict]:
    pages = []
    for f in files_list(m):
        path, content = f["path"], f["content"]
        if path.endswith(".html") and not path.startswith("_"):
            t = re.search(r"<title>(.*?)</title>", content, re.S)
            pages.append({"file": path, "title": (t.group(1).strip() if t else path)[:80]})
    return pages


def render(m: dict[str, str], path: str) -> str:
    c = m.get(path, "")
    if path.endswith(".html") and not path.startswith("_"):
        c = c.replace("<!--HEAD-->", m.get("_head.html", ""))
        c = c.replace("<!--HEADER-->", m.get("_header.html", ""))
        c = c.replace("<!--FOOTER-->", m.get("_footer.html", ""))
    return c


async def _set(pid: str, **fields) -> None:
    fields["updated_at"] = now_iso()
    await db.projects.update_one({"id": pid}, {"$set": fields})


async def _step(pid: str, key: str, status: str, detail: str = "") -> None:
    await db.projects.update_one(
        {"id": pid, "steps.key": key},
        {"$set": {"steps.$.status": status, "steps.$.detail": detail, "updated_at": now_iso()}},
    )


async def _msg(pid: str, role: str, content: str) -> None:
    await db.projects.update_one({"id": pid}, {"$push": {"messages": {"role": role, "content": content, "created_at": now_iso()}}})


async def snapshot(pid: str, label: str) -> int:
    p = await db.projects.find_one({"id": pid})
    number = int(p.get("version", 0)) + 1
    await db.versions.insert_one(
        {"id": new_id(), "project_id": pid, "number": number, "label": label, "files": p.get("files", []), "created_at": now_iso()}
    )
    await _set(pid, version=number)
    return number


async def _brand_text(p: dict) -> str:
    if not p.get("brand_id"):
        return ""
    b = await db.brands.find_one({"id": p["brand_id"]})
    if not b:
        return ""
    logo = f" Logo disponible : {media_url(b['logo_media_id'])} (à utiliser dans l'en-tête via <img>)." if b.get("logo_media_id") else ""
    return f"\nIDENTITÉ DE MARQUE IMPOSÉE : nom « {b['name']} », slogan « {b.get('slogan','')} », couleurs {', '.join(b.get('colors', []))}.{logo}"


def _style_text(p: dict) -> str:
    s = p.get("style") or {}
    parts = [f"{k} : {v}" for k, v in s.items() if v]
    return ("\nPRÉFÉRENCES DE STYLE DU CLIENT : " + " ; ".join(parts)) if parts else ""


FEATURES = {
    "boutique": "catalogue produits avec filtres par catégorie/prix, fiches avec variantes (taille/couleur), panier latéral persistant (localStorage) avec quantités et total, faux tunnel de commande signalant clairement « Paiement non branché — démonstration »",
    "restaurant": "carte interactive par catégories (onglets), formulaire de réservation : date, nombre de couverts, créneaux horaires générés en JS et sélectionnables, confirmation visuelle, mention « Réservation de démonstration — non transmise »",
    "immobilier": "listing de biens filtrable (type, prix, surface, ville), fiche bien avec galerie lightbox, formulaire de contact/visite, simulateur de mensualité",
    "services": "demande de devis multi-étapes avec récapitulatif, galerie de réalisations avec lightbox et filtres, témoignages",
    "autre": "galerie avec lightbox, formulaire de contact validé en JS, sections interactives adaptées au métier",
}


async def _images_step(pid: str, p: dict, art: dict) -> list[dict]:
    briefs = (art.get("image_briefs") or [])[: (5 if p["mode"] == "pro" else 3)]
    model = "comfy" if p.get("llm") == "local" else "nano-banana-pro" if p["mode"] == "pro" else "nano-banana"
    style = art.get("photo_style", "")
    done = 0
    if model == "comfy" and not await comfy.reachable():
        return []

    async def one(b: dict) -> Optional[dict]:
        nonlocal done
        m = await create_media("image", "site", b.get("prompt", ""), model, status="running", project_id=pid, aspect_ratio=b.get("aspect", "16:9"))
        try:
            prompt = f"{b.get('prompt','')}. Photographic style: {style}. Aspect ratio {b.get('aspect','16:9')}, premium editorial quality, no text, no watermark."
            data, mime = await generate_image(prompt, model, aspect=b.get("aspect", "16:9"))
            await finish_media(m["id"], data, mime)
            done += 1
            await _step(pid, "images", "running", f"{done}/{len(briefs)} images créées")
            if b is briefs[0]:
                hero_bytes[:] = [(data, mime)]
            return {"slot": b.get("slot", "image"), "id": m["id"], "url": media_url(m["id"]), "desc": b.get("prompt", "")[:160]}
        except Exception as exc:  # one failed image must not stop the site
            await db.media.update_one({"id": m["id"]}, {"$set": {"status": "error", "error": str(exc)[:300]}})
            return None

    hero_bytes: list[tuple[bytes, str]] = []
    results = [r for r in await asyncio.gather(*(one(b) for b in briefs)) if r]
    if p.get("hero_video") and hero_bytes:
        video = await _hero_video(pid, p, art, hero_bytes[0])
        if video:
            results.append(video)
    return results


async def _hero_video(pid: str, p: dict, art: dict, ref: tuple[bytes, str]) -> Optional[dict]:
    """Optional 3 s seamless-feeling loop animated from the hero image with Wan 2.2 / LTX (local ComfyUI)."""
    if not await comfy.reachable():
        await _step(pid, "images", "running", "Vidéo d'en-tête ignorée : ComfyUI injoignable")
        return None
    brief = (art.get("image_briefs") or [{}])[0].get("prompt", "")
    prompt = (f"{brief}. Subtle cinematic motion, slow camera push-in, gentle parallax, natural ambient movement (steam, light, fabric, leaves), "
              f"{art.get('photo_style', '')}. Smooth, loopable, no cuts, no text.")
    m = await create_media("video", "site", prompt, "comfy", status="running", project_id=pid, aspect_ratio="16:9", duration="3")

    async def progress(label: str) -> None:
        await _step(pid, "images", "running", f"Vidéo d'en-tête (Wan 2.2 local) : {label}")

    try:
        await _step(pid, "images", "running", "Vidéo d'en-tête (Wan 2.2 local) : démarrage…")
        data, mime = await comfy.generate_video(prompt, "3", "16:9", ref, progress)
        await finish_media(m["id"], data, mime)
        return {"slot": "hero_video", "kind": "video", "id": m["id"], "url": media_url(m["id"]), "desc": "Vidéo d'en-tête animée"}
    except Exception as exc:  # the site must still be delivered without the video
        await db.media.update_one({"id": m["id"]}, {"$set": {"status": "error", "error": str(exc)[:300]}})
        return None


def _ctx(p: dict) -> str:
    return json.dumps({"brief": p.get("brief"), "architecture": p.get("architecture"), "direction": p.get("art")}, ensure_ascii=False)


def _img_text(images: list[dict]) -> str:
    if not images:
        return "Aucune image générée : utilise des compositions typographiques, dégradés et formes CSS."
    return "\n".join(
        f"- {i['slot']} → {i['url']} (VIDÉO mp4 : à utiliser en fond du hero avec <video autoplay muted loop playsinline>)" if i.get("kind") == "video"
        else f"- {i['slot']} → {i['url']} ({i['desc']})" for i in images)


async def _gen_system(p: dict, images: list[dict]) -> dict[str, str]:
    if p.get("engine") == "premium":
        return premium.system_files(p, images)
    site_type = p["brief"].get("site_type", "autre")
    prompt = f"""CONTEXTE DU PROJET (JSON) :
{_ctx(p)}
{await _brand_text(p)}
IMAGES DU SITE :
{_img_text(images)}

Crée le SYSTÈME DE DESIGN partagé et les éléments communs. Produis exactement ces fichiers :
1. _head.html : balises à insérer dans <head> : meta charset, meta viewport, <link> Google Fonts (polices de la direction artistique, axes de graisse valides), <link rel="stylesheet" href="styles.css">{', script Three.js depuis https://unpkg.com/three@0.160.0/build/three.min.js' if p['art'].get('use_three') else ''}.
2. _header.html : en-tête/navigation complète vers toutes les pages de l'architecture (liens relatifs ex. "a-propos.html"), menu mobile (bouton burger), logo/nom. Pas de balise <header> de page au-delà de ça.
3. _footer.html : pied de page complet (coordonnées, liens vers toutes les pages + mentions-legales.html + confidentialite.html). Doit contenir EXACTEMENT le texte « {CREDIT} »{' et la mention « Images illustratives générées par IA »' if images else ''}.
4. styles.css : système complet et original (variables de palette, échelle typographique fluide, composants : boutons, cartes, grilles, formulaires, onglets, drawer panier, lightbox, toasts, animations d'apparition .reveal/.is-visible, transitions, @media mobile/tablette). Signature visuelle forte et propre à CE projet.
5. app.js : JavaScript vanilla (DOMContentLoaded, aucun module) : menu mobile, lien actif selon la page, apparitions au défilement (IntersectionObserver), toasts, lightbox, et fonctionnalités métier : {FEATURES.get(site_type, FEATURES['autre'])}. Toutes les fonctions doivent être tolérantes (ne rien faire si l'élément est absent).{' Ajoute une scène Three.js légère et élégante initialisée sur un élément [data-three] si présent.' if p['art'].get('use_three') else ''}
6. _guide.md : documentation concise pour les intégrateurs de pages : classes CSS disponibles, structure HTML et attributs data-* attendus par app.js pour chaque fonctionnalité (exemples HTML courts).

FORMAT DE SORTIE STRICT : pour chaque fichier, une ligne `===FILE: nom===` puis le contenu brut (sans ```), et termine par `===END===`."""
    out = await complete(SYS_CODE, prompt, p.get("llm", "claude"), 30000)
    files = parse_files(out)
    missing = [f for f in ["_head.html", "_header.html", "_footer.html", "styles.css", "app.js"] if f not in files]
    if missing:
        raise RuntimeError(f"Fichiers communs manquants : {', '.join(missing)}")
    return files


def legal_page(p: dict, file: str) -> str:
    name = (p.get("brief") or {}).get("business_name") or p.get("name") or "[NOM DE L'ENTREPRISE]"
    if file == "mentions-legales.html":
        title, blocks = "Mentions légales", [
            ("Éditeur du site", f"{name} — [FORME JURIDIQUE] au capital de [MONTANT] € — Siège : [ADRESSE] — RCS/SIREN : [NUMÉRO] — TVA : [NUMÉRO] — Téléphone : [TÉLÉPHONE] — E-mail : [E-MAIL]"),
            ("Directeur de la publication", "[NOM ET FONCTION]"),
            ("Hébergement", "[NOM DE L'HÉBERGEUR] — [ADRESSE] — [TÉLÉPHONE]"),
            ("Conception", "Site web créé par Forma."),
            ("Propriété intellectuelle", f"L'ensemble des contenus de ce site est la propriété de {name}, sauf mention contraire. Les images marquées comme illustratives ont été générées par intelligence artificielle. [À COMPLÉTER]"),
        ]
    else:
        title, blocks = "Politique de confidentialité", [
            ("Responsable du traitement", f"{name} — [ADRESSE] — [E-MAIL DE CONTACT]"),
            ("Données collectées", "[À COMPLÉTER : données des formulaires (nom, e-mail, téléphone, message), données de réservation ou de commande]"),
            ("Finalités et base légale", "[À COMPLÉTER : réponse aux demandes, gestion des réservations/commandes, intérêt légitime ou consentement]"),
            ("Durée de conservation", "[À COMPLÉTER]"),
            ("Vos droits", "Accès, rectification, effacement, opposition, limitation et portabilité : écrivez à [E-MAIL]. Réclamation possible auprès de la CNIL (www.cnil.fr)."),
            ("Cookies", "[À COMPLÉTER : liste des cookies et traceurs utilisés]"),
        ]
    body = "\n".join(f"<h2>{h}</h2>\n<p>{t}</p>" for h, t in blocks)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<!--HEAD-->
<title>{title} — {name}</title>
<meta name="description" content="{title} de {name}">
<style>.legal-wrap{{max-width:820px;margin:0 auto;padding:clamp(7rem,14vw,10rem) 1.5rem 5rem}}.legal-wrap h1{{font-size:clamp(2rem,5vw,3.2rem);margin-bottom:1.5rem}}.legal-wrap h2{{font-size:1.25rem;margin:2.2rem 0 .6rem}}.legal-wrap p{{line-height:1.7;opacity:.85}}.legal-note{{border:1px solid currentColor;border-radius:12px;padding:1rem 1.2rem;opacity:.75;font-size:.92rem}}</style>
</head>
<body>
<!--HEADER-->
<main class="legal-wrap">
<h1>{title}</h1>
<p class="legal-note">Modèle à compléter : ce texte n'est pas juridiquement validé et doit être relu par un professionnel avant publication.</p>
{body}
</main>
<!--FOOTER-->
<script src="app.js" defer></script>
</body>
</html>
"""


async def _gen_page(p: dict, page: dict, system: dict[str, str], images: list[dict]) -> str:
    if page["file"] in dict(LEGAL):
        return legal_page(p, page["file"])
    if p.get("engine") == "premium":
        return await _gen_premium_page(p, page, images)
    all_pages = ", ".join(f"{pg['file']} ({pg['title']})" for pg in p["architecture"]["pages"])
    legal = page["file"] in dict(LEGAL)
    extra = (
        "Page légale : structure claire avec des champs à compléter entre crochets [À COMPLÉTER : ...] et un encadré indiquant que ce texte est un modèle à faire valider par un professionnel, non juridiquement validé."
        if legal
        else "Page riche et spectaculaire : sections variées et asymétriques, textes rédigés (pas de lorem ipsum), utilisation des images fournies là où elles servent le récit, animations .reveal."
    )
    prompt = f"""CONTEXTE DU PROJET (JSON) :
{_ctx(p)}
{await _brand_text(p)}
IMAGES DISPONIBLES (utilise les URL exactes, ajoute data-ai="illustrative" sur ces <img>, alt descriptif) :
{_img_text(images)}

GUIDE DES COMPOSANTS (classes et attributs à respecter pour que app.js fonctionne) :
{system.get('_guide.md', '')}

STYLES.CSS DU SITE :
{system['styles.css'][:24000]}

Toutes les pages du site : {all_pages}, mentions-legales.html, confidentialite.html.
Écris la page « {page['file']} » — titre : {page['title']} — rôle : {page.get('purpose','')} — sections : {', '.join(page.get('sections', []))}.
{extra}

Règles : document HTML complet. Dans <head> : la ligne <!--HEAD--> puis <title> et <meta name="description">. Juste après <body> : la ligne <!--HEADER-->. Avant </body> : la ligne <!--FOOTER--> puis <script src="app.js" defer></script>. N'écris ni en-tête de navigation ni pied de page toi-même. Liens internes relatifs uniquement vers les pages existantes. CSS spécifique éventuel dans un <style> court.

FORMAT DE SORTIE STRICT : `===FILE: {page['file']}===` puis le HTML brut, puis `===END===`."""
    out = await complete(SYS_CODE, prompt, p.get("llm", "claude"), 24000)
    files = parse_files(out)
    html = files.get(page["file"]) or (next(iter(files.values())) if files else "")
    if "<html" not in html.lower():
        raise RuntimeError(f"Page {page['file']} invalide")
    return html


SYS_CONTENT = (
    "Tu es directeur de création et concepteur-rédacteur d'une agence web primée (niveau Awwwards). "
    "Tu composes des pages spectaculaires à partir d'un catalogue de sections animées et tu écris des textes de vente percutants. "
    "Tu réponds UNIQUEMENT par un objet JSON valide, sans texte autour."
)


async def _gen_premium_page(p: dict, page: dict, images: list[dict]) -> str:
    """Premium engine: the LLM only writes structured content; sections are rendered by lib.premium."""
    last: Exception | None = None
    for _ in range(2):
        try:
            content = parse_json(await complete(SYS_CONTENT, premium.page_prompt(p, page, images), p.get("llm", "claude"), 7000))
            if isinstance(content, dict) and content.get("sections"):
                return premium.render_page(p, page, content, images)
            last = RuntimeError("contenu vide")
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Page {page['file']} : {last}")


# ---------------------------------------------------------------- QA

def _node_check(js: str) -> Optional[str]:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(js)
        path = fh.name
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True, timeout=20)
        return None if r.returncode == 0 else (r.stderr.strip().splitlines() or ["erreur"])[-1][:300]
    except Exception:
        return None


async def _fonts_ok(head: str) -> tuple[str, bool]:
    m = re.search(r'href="(https://fonts\.googleapis\.com/css2\?[^"]+)"', head)
    if not m:
        return head, True
    url = m.group(1).replace("&amp;", "&")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            if (await c.get(url)).status_code == 200:
                return head, True
    except Exception:
        return head, True
    fams = re.findall(r"family=([^:&]+)", url)
    fixed = "https://fonts.googleapis.com/css2?" + "&".join(f"family={f}" for f in fams) + "&display=swap"
    return head.replace(m.group(1), fixed), False


async def run_qa(m: dict[str, str], asset_ids: set[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Returns (issues per file needing the LLM, auto-fixed notes). Mutates m for mechanical fixes."""
    issues: dict[str, list[str]] = {}
    notes: list[str] = []
    pages = [k for k in m if k.endswith(".html") and not k.startswith("_")]
    if CREDIT not in m.get("_footer.html", ""):
        m["_footer.html"] = m.get("_footer.html", "") + f'\n<p class="forma-credit" style="text-align:center;opacity:.7;font-size:.85rem;padding:1rem">{CREDIT}</p>\n'
        notes.append("Mention « Site web créé par Forma » ajoutée au pied de page")
    if "viewport" not in m.get("_head.html", ""):
        m["_head.html"] = '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + m.get("_head.html", "")
        notes.append("Balise viewport mobile ajoutée")
    head, ok = await _fonts_ok(m.get("_head.html", ""))
    if not ok:
        m["_head.html"] = head
        notes.append("Lien des polices corrigé")
    if "@media" not in m.get("styles.css", ""):
        issues.setdefault("styles.css", []).append("Aucune règle @media : ajouter l'adaptation mobile et tablette")
    for js in [k for k in m if k.endswith(".js")]:
        err = _node_check(m[js])
        if err:
            issues.setdefault(js, []).append(f"Erreur JavaScript : {err}")
    for pg in pages:
        c = m[pg]
        for ph, where in [("<!--HEADER-->", "après <body>"), ("<!--FOOTER-->", "avant </body>"), ("<!--HEAD-->", "dans <head>")]:
            if ph not in c:
                if ph == "<!--HEAD-->":
                    c = c.replace("<head>", "<head>\n<!--HEAD-->", 1)
                elif ph == "<!--HEADER-->":
                    c = re.sub(r"(<body[^>]*>)", r"\1\n<!--HEADER-->", c, count=1)
                else:
                    c = c.replace("</body>", "<!--FOOTER-->\n</body>", 1)
                notes.append(f"{pg} : bloc commun réinséré ({where})")
        if 'src="app.js"' not in c:
            c = c.replace("</body>", '<script src="app.js" defer></script>\n</body>', 1)
        m[pg] = c
    for src in [*pages, "_header.html", "_footer.html"]:
        c = m.get(src, "")
        for href in set(re.findall(r'href="([^"#?:]+\.html)', c)):
            if href.lstrip("./") not in m:
                issues.setdefault(src, []).append(f"Lien vers une page inexistante : {href}")
        for mid in set(re.findall(r"/api/media/([0-9a-f-]{36})/file", c)):
            if mid not in asset_ids:
                issues.setdefault(src, []).append(f"Image absente : /api/media/{mid}/file (remplacer par une image disponible ou une composition CSS)")
    return issues, notes


async def _fix(p: dict, m: dict[str, str], issues: dict[str, list[str]], images: list[dict]) -> int:
    fixed = 0
    pages = ", ".join(k for k in m if k.endswith(".html") and not k.startswith("_"))

    async def one(path: str, probs: list[str]) -> None:
        nonlocal fixed
        prompt = f"""Fichier « {path} » d'un site (pages existantes : {pages}). Images disponibles : {_img_text(images)}
Défauts détectés par le contrôle qualité :
- """ + "\n- ".join(probs) + f"""

Contenu actuel :
{m[path]}

Corrige UNIQUEMENT ces défauts, de façon ciblée, avec des blocs de remplacement :
===EDIT: {path}===
<<<<<<< SEARCH
(lignes exactes actuelles)
=======
(nouvelles lignes)
>>>>>>> REPLACE
Termine par ===END===."""
        out = await complete(SYS_CODE, prompt, p.get("llm", "claude"), 8000)
        changed = _apply_output(m, out)
        if changed:
            fixed += 1

    await asyncio.gather(*(one(k, v) for k, v in issues.items() if k in m))
    return fixed


def _apply_output(m: dict[str, str], out: str) -> list[str]:
    changed: list[str] = []
    for path, content in parse_files(out).items():
        m[path] = content
        changed.append(path)
    for path, blocks in parse_edits(out).items():
        if path not in m:
            continue
        c = m[path]
        ok = False
        for s, r in blocks:
            res = apply_edit(c, s, r)
            if res is not None:
                c, ok = res, True
        if ok:
            m[path] = c
            changed.append(path)
    return changed


# ---------------------------------------------------------------- pipeline

async def _run_pipeline(pid: str) -> None:
    current = "analyse"
    try:
        p = await db.projects.find_one({"id": pid})
        await _set(pid, status="generating", error=None, question=None)
        llm = p.get("llm", "claude")
        base = f"DEMANDE : {p['prompt']}{_style_text(p)}{await _brand_text(p)}"
        if p.get("answer"):
            base += f"\nRÉPONSE DU CLIENT À TA QUESTION : {p['answer']}"

        if not p.get("brief"):
            await _step(pid, "analyse", "running", "Lecture du métier et du positionnement…")
            brief = parse_json(await complete(SYS_JSON, base + """

Analyse la demande. JSON attendu :
{"business_name": str, "sector": str, "site_type": "boutique"|"restaurant"|"services"|"immobilier"|"autre", "positioning": str, "audience": str, "tone": str, "language": "fr"|"en"|..., "requirements": [str], "missing_question": null | str}
"missing_question" : une SEULE question, uniquement si une information indispensable manque vraiment (sinon null ; invente des contenus plausibles plutôt que de questionner).""", llm, 3000))
            if brief.get("missing_question") and not p.get("answer"):
                await _step(pid, "analyse", "waiting", "Une précision est nécessaire")
                await _msg(pid, "assistant", brief["missing_question"])
                await _set(pid, status="needs_input", question=brief["missing_question"])
                return
            name = p.get("name") or brief.get("business_name") or "Nouveau site"
            await _set(pid, brief=brief, name=name, site_type=brief.get("site_type", "autre"))
            await _step(pid, "analyse", "done", f"{brief.get('sector','')} · {brief.get('positioning','')}"[:160])
            p = await db.projects.find_one({"id": pid})

        current = "architecture"
        if not p.get("architecture"):
            await _step(pid, "architecture", "running", "Conception des pages et parcours…")
            n = "5 à 7" if p["mode"] == "pro" else "4 à 5"
            arch = parse_json(await complete(SYS_JSON, f"""Brief : {json.dumps(p['brief'], ensure_ascii=False)}
Conçois l'architecture : {n} pages de contenu (index.html obligatoire, noms de fichiers en minuscules avec tirets), sans les pages légales. JSON :
{{"pages": [{{"file": str, "title": str, "purpose": str, "sections": [str]}}], "journeys": [str]}}""", llm, 3000))
            arch["pages"] = [pg for pg in arch.get("pages", []) if pg["file"] not in dict(LEGAL)][:8]
            arch["pages"] += [{"file": f, "title": t, "purpose": "Page légale", "sections": []} for f, t in LEGAL]
            await _set(pid, architecture=arch)
            await _step(pid, "architecture", "done", f"{len(arch['pages'])} pages · " + ", ".join(pg["title"] for pg in arch["pages"][:5]))
            p = await db.projects.find_one({"id": pid})

        current = "direction"
        if not p.get("art"):
            await _step(pid, "direction", "running", "Typographies, palette, style photo, mouvement…")
            nimg = 5 if p["mode"] == "pro" else 3
            if p.get("engine") == "premium":
                art = premium.make_art(p, parse_json(await complete(SYS_JSON, premium.direction_prompt(p, nimg) + _style_text(p), llm, 3000)))
            else:
              art = parse_json(await complete(SYS_JSON, f"""Brief : {json.dumps(p['brief'], ensure_ascii=False)}{_style_text(p)}{await _brand_text(p)}
Crée une direction artistique ORIGINALE propre à ce projet (pas de gabarit). JSON :
{{"concept": str, "fonts": {{"heading": str (Google Font), "body": str (Google Font)}}, "palette": {{"background": hex, "surface": hex, "text": hex, "muted": hex, "accent": hex, "accent2": hex}}, "photo_style": str (en anglais), "motion": str, "layout_signature": str, "use_three": bool (true seulement si la 3D sert vraiment le propos), "image_briefs": [{{"slot": str (ex. hero, ambiance, produit), "prompt": str (en anglais, très précis), "aspect": "16:9"|"4:5"|"1:1"}}] ({nimg} éléments, le premier = hero)}}""", llm, 3000))
            await _set(pid, art=art)
            await _step(pid, "direction", "done", f"{art['fonts'].get('heading')} / {art['fonts'].get('body')} · {art.get('concept','')}"[:160])
            p = await db.projects.find_one({"id": pid})

        current = "images"
        images = p.get("images")
        if images is None:
            await _step(pid, "images", "running", "Génération des visuels (ComfyUI local)…" if llm == "local" else "Génération des visuels…")
            images = await _images_step(pid, p, p["art"])
            await _set(pid, images=images, asset_ids=[i["id"] for i in images], thumbnail_id=images[0]["id"] if images else None)
            await _step(pid, "images", "done", f"{len(images)} images illustratives" if images else "Aucune image (moteur d'images indisponible) : compositions typographiques et formes CSS")
            p = await db.projects.find_one({"id": pid})

        current = "generation"
        if not p.get("files"):
            await _step(pid, "generation", "running", "Système de design et fonctionnalités…")
            system = await _gen_system(p, images)
            pages = p["architecture"]["pages"]
            done = 0
            sem = asyncio.Semaphore(4)

            async def page_task(pg: dict) -> tuple[str, str]:
                nonlocal done
                async with sem:
                    html = await _gen_page(p, pg, system, images)
                done += 1
                await _step(pid, "generation", "running", f"Pages écrites : {done}/{len(pages)}")
                return pg["file"], html

            await _step(pid, "generation", "running", f"Pages écrites : 0/{len(pages)}")
            results = await asyncio.gather(*(page_task(pg) for pg in pages), return_exceptions=True)
            m = dict(system)
            failed = []
            for pg, r in zip(pages, results):
                if isinstance(r, BaseException):
                    failed.append(pg["file"])
                else:
                    m[r[0]] = r[1]
            if "index.html" not in m:
                raise RuntimeError("La page d'accueil n'a pas pu être générée")
            await _set(pid, files=files_list(m), pages=pages_from(m))
            await _step(pid, "generation", "done", f"{len([k for k in m if k.endswith('.html') and not k.startswith('_')])} pages" + (f" · échecs : {', '.join(failed)}" if failed else ""))
            p = await db.projects.find_one({"id": pid})

        current = "qa"
        await _step(pid, "qa", "running", "Liens, pages, JavaScript, images, mobile…")
        m = files_map(p)
        arch_files = [pg["file"] for pg in p["architecture"]["pages"]]
        missing_pages = [f for f in arch_files if f not in m]
        report: list[str] = []
        if missing_pages:
            system = {k: v for k, v in m.items() if k.startswith("_") or k in ("styles.css", "app.js")}
            for pg in [x for x in p["architecture"]["pages"] if x["file"] in missing_pages]:
                try:
                    m[pg["file"]] = await _gen_page(p, pg, system, images)
                    report.append(f"Page manquante régénérée : {pg['file']}")
                except Exception:
                    report.append(f"Page toujours manquante : {pg['file']}")
        issues, notes = await run_qa(m, set(p.get("asset_ids", [])))
        report += notes
        if issues:
            await _step(pid, "qa", "running", f"{sum(len(v) for v in issues.values())} défauts trouvés · correction ciblée…")
            await _fix(p, m, issues, images)
            remaining, notes2 = await run_qa(m, set(p.get("asset_ids", [])))
            report += [f"Corrigé : {i}" for k, v in issues.items() for i in v if i not in remaining.get(k, [])]
            report += [f"À revoir : {i}" for v in remaining.values() for i in v] + notes2
        await _set(pid, files=files_list(m), pages=pages_from(m), qa_report=report)
        await _step(pid, "qa", "done", f"{len(report)} point(s) traité(s)" if report else "Aucun défaut détecté")
        await snapshot(pid, "Génération initiale")
        await _msg(pid, "assistant", f"Votre site « {p['name']} » est prêt : {len(pages_from(m))} pages. Demandez-moi n'importe quelle modification, ou sélectionnez un élément dans l'aperçu.")
        await _set(pid, status="ready")
    except Exception as exc:
        log.exception("pipeline %s failed", pid)
        await _step(pid, current, "error", friendly_error(exc)[:200])
        await _set(pid, status="error", error=f"Échec à l'étape « {dict(STEPS)[current]} » : {friendly_error(exc)}")


# ---------------------------------------------------------------- chat edit

async def _run_edit(pid: str, message: str, page: str, selection: Optional[dict], media_ids: list[str]) -> None:
    try:
        p = await db.projects.find_one({"id": pid})
        m = files_map(p)
        media_lines = []
        for mid in media_ids:
            md = await db.media.find_one({"id": mid})
            if md and md.get("status") == "done":
                media_lines.append(f"- {md['kind']} {media_url(mid)} ({md.get('prompt','')[:120]})" + (" — utiliser <video autoplay muted loop playsinline>" if md["kind"] == "video" else ""))
        sel = ""
        if selection and selection.get("html"):
            sel = f"\nÉLÉMENT SÉLECTIONNÉ dans « {selection.get('page') or page} » (sélecteur {selection.get('selector','')}) :\n{selection['html']}\n"
        media_block = ("Médias à intégrer :\n" + "\n".join(media_lines)) if media_lines else ""
        files_dump = "\n\n".join(f"===FILE: {k}===\n{v}" for k, v in m.items() if k != "_guide.md")
        prompt = f"""Voici tous les fichiers du site (les pages contiennent <!--HEAD-->, <!--HEADER-->, <!--FOOTER--> remplacés par _head.html, _header.html, _footer.html).

{files_dump}

Page affichée : {page or 'index.html'}{sel}
{media_block}

DEMANDE : {message}

Applique la demande de façon CIBLÉE, sans régénérer le site. Conserve « {CREDIT} » dans le pied de page.
- Modification d'un fichier existant : blocs
===EDIT: chemin===
<<<<<<< SEARCH
(lignes exactes actuelles, assez pour être uniques)
=======
(nouvelles lignes)
>>>>>>> REPLACE
- Nouveau fichier (ex. nouvelle page, avec <!--HEAD-->, <!--HEADER-->, <!--FOOTER--> et app.js) : ===FILE: chemin=== puis le contenu complet. Pense à l'ajouter à la navigation (_header.html).
- Suppression d'une page : ===DELETE: chemin=== et retire ses liens.
Commence par une ligne `RÉSUMÉ: ...` (une phrase en français décrivant ce que tu as fait), puis les blocs, et termine par ===END===."""
        out = await complete(SYS_CODE, prompt, p.get("llm", "claude"), 24000)
        deleted = [d.strip() for d in re.findall(r"===DELETE:\s*([^\n=]+?)\s*===", out)]
        for d in deleted:
            if d in m and d != "index.html":
                m.pop(d)
        changed = _apply_output(m, out)
        summary_m = re.search(r"RÉSUMÉ\s*:\s*(.+)", out)
        summary = summary_m.group(1).strip() if summary_m else "Modification appliquée."
        if not changed and not deleted:
            await _msg(pid, "assistant", "Je n'ai pas pu appliquer cette modification de façon fiable. Pouvez-vous la reformuler ou sélectionner l'élément concerné ?")
            await _set(pid, status="ready")
            return
        issues, _notes = await run_qa(m, set(p.get("asset_ids", [])) | set(media_ids))
        await _set(pid, files=files_list(m), pages=pages_from(m), asset_ids=list(set(p.get("asset_ids", [])) | set(media_ids)))
        n = await snapshot(pid, message[:80])
        warn = f" (contrôle : {sum(len(v) for v in issues.values())} point(s) à vérifier)" if issues else ""
        await _msg(pid, "assistant", f"{summary} — fichiers modifiés : {', '.join(changed + deleted)}. Version {n}.{warn}")
        await _set(pid, status="ready")
    except Exception as exc:
        log.exception("edit %s failed", pid)
        await _msg(pid, "assistant", f"La modification a échoué : {friendly_error(exc)}")
        await _set(pid, status="ready")


def initial_steps() -> list[dict]:
    return [{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in STEPS]


# ------------------------------------------------------------------ GPU scheduling for the local engine

async def _local_slot(pid: str, kind: str, coro_factory) -> None:
    p = await db.projects.find_one({"id": pid}, {"llm": 1, "name": 1})
    if not p or p.get("llm") != "local":
        return await coro_factory()
    try:
        async with gpu_queue.slot(pid, kind, "Ollama + ComfyUI", p.get("name") or "Nouveau site", "project"):
            await coro_factory()
    except gpu_queue.JobCancelled:
        if kind == "site":
            await _set(pid, status="error", error="Génération annulée avant son démarrage (file d'attente GPU).")
        else:
            await _set(pid, status="ready")


async def run_pipeline(pid: str) -> None:
    await _local_slot(pid, "site", lambda: _run_pipeline(pid))


async def run_edit(pid: str, message: str, page: str, selection: Optional[dict], media_ids: list[str]) -> None:
    await _local_slot(pid, "edit", lambda: _run_edit(pid, message, page, selection, media_ids))
