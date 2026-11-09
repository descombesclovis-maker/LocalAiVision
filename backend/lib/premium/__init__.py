"""Premium site engine: the LLM writes structured content (sections + copy), this module renders it
with a hand-built library of animated sections. Works great with small local models (Ollama 7-14B)."""
import hashlib
import html
import json
import random
import re
import urllib.parse
from pathlib import Path

from lib.premium.themes import MOODS, pick_theme

HERE = Path(__file__).parent
RUNTIME_CSS = (HERE / "runtime.css").read_text()
RUNTIME_JS = (HERE / "runtime.js").read_text()

SECTION_TYPES = [
    "hero", "marquee", "story", "statement", "features", "hscroll", "stats", "configurator",
    "network", "gallery", "testimonials", "pricing", "process", "textimage", "faq", "logos", "cta", "contact",
]

CATALOG = """CATALOGUE DES SECTIONS (champ "type" obligatoire ; *mot* = mot mis en valeur en italique accentué) :
- hero : {"eyebrow", "title" (3 à 7 mots percutants), "subtitle", "cta": {"label","href"}, "cta2": {"label","href"}, "meta": [str ×2-3 courtes infos], "image": slot}
- marquee : {"items": [str ×4-7 mots ou expressions courtes]}
- story : récit épinglé au défilement {"eyebrow","title","steps": [{"kicker","title","text","image": slot} ×3-4]}
- statement : manifeste géant révélé mot à mot {"text" (1 à 2 phrases fortes), "author"}
- features : {"eyebrow","title","intro","items": [{"title","text","image": slot} ×3-6]}
- hscroll : galerie horizontale épinglée {"eyebrow","title","items": [{"title","text","image": slot} ×4-6]}
- stats : {"items": [{"value": nombre, "suffix": str (ex. "+", "%", " ans"), "label"} ×3-4]} (chiffres plausibles et prudents)
- configurator : composer/estimer en direct (menu, devis, formule) {"eyebrow","title","intro","base_price": nombre,"currency":"€","groups": [{"name","type":"single"|"multi","choices":[{"label","price": nombre}] ×2-5}] ×2-4, "cta": {"label","href"}}
- network : visuel 3D animé (réseau, global, tech, logistique) {"eyebrow","title","text","cta": {"label","href"}}
- gallery : collage éditorial d'images {"eyebrow","title","items": [{"caption","image": slot} ×4]}
- testimonials : {"items": [{"quote","author","role"} ×3]}
- pricing : carte, tarifs ou offres {"eyebrow","title","groups": [{"name","items":[{"name","desc","price": str,"tag": str|null}] ×3-6}] ×1-3}
- process : étapes {"eyebrow","title","items": [{"title","text"} ×3-5]}
- textimage : {"eyebrow","title","text","bullets":[str ×3-4],"image": slot,"cta": {"label","href"}}
- faq : {"title","items": [{"q","a"} ×4-6]}
- logos : partenaires/labels/marques travaillées {"title","items": [str ×5-8]}
- cta : appel final {"title","text","cta": {"label","href"}}
- contact : {"title","text","address","phone","email","hours":[str],"form": true}"""


def _seed(p: dict) -> str:
    return f"{p['id']}:{p.get('regen', 0)}"


def e(v) -> str:
    """Escape LLM text, then allow *emphasis*."""
    s = html.escape(str(v or "")).strip()
    s = re.sub(r"(?<!\w)\*([^*\n]{1,60}?)\*(?!\w)", r"<em>\1</em>", s)
    return s.replace("*", "")


def plain(v) -> str:
    return html.escape(re.sub(r"\*", "", str(v or ""))).strip()


def lst(v, n: int) -> list:
    return [x for x in (v if isinstance(v, list) else []) if x][:n]


class Ctx:
    """Rendering context: theme, images, pages, random source."""

    def __init__(self, p: dict, images: list[dict], page: str):
        self.p, self.art, self.page = p, p["art"], page
        self.theme = p["art"]["premium"]
        self.images = [i for i in images if i.get("url") and i.get("kind") != "video"]
        self.video = next((i for i in images if i.get("kind") == "video"), None)
        self.rnd = random.Random(f"{self.theme['seed']}:{page}")
        self.pages = {pg["file"] for pg in p["architecture"]["pages"]}
        self.n = 0
        self.used = 0

    def img(self, slot=None, cls: str = "", eager: bool = False, parallax: float = 0) -> str:
        im = None
        if isinstance(slot, str):
            im = next((i for i in self.images if i["slot"].lower() == slot.lower()), None)
        if im is None and self.images:
            im = self.images[self.used % len(self.images)]
            self.used += 1
        par = f' data-parallax="{parallax}"' if parallax else ""
        if not im:
            return f'<div class="pm-media {cls}"{par}><div class="pm-ph"></div></div>'
        alt = plain(im.get("desc", ""))[:140]
        if im.get("kind") == "video":
            return f'<div class="pm-media {cls}"{par}><video src="{im["url"]}" autoplay muted loop playsinline poster=""></video></div>'
        return f'<div class="pm-media {cls}"{par}><img src="{im["url"]}" alt="{alt}" data-ai="illustrative" loading="{"eager" if eager else "lazy"}"></div>'

    def hero_media(self, slot=None, parallax: float = 0) -> str:
        """Hero visual: the animated hero loop when one was rendered, otherwise the hero image."""
        if not self.video:
            return self.img(slot, eager=True, parallax=parallax)
        poster = self.img_url(slot)
        par = f' data-parallax="{parallax}"' if parallax else ""
        return (f'<div class="pm-media"{par}><video src="{self.video["url"]}" poster="{poster}" autoplay muted loop playsinline '
                f'preload="auto" aria-hidden="true"></video></div>')

    def img_url(self, slot=None) -> str:
        if not self.images:
            return ""
        im = next((i for i in self.images if isinstance(slot, str) and i["slot"].lower() == slot.lower()), None)
        return (im or self.images[self.used % len(self.images)])["url"]

    def href(self, h) -> str:
        h = str(h or "").strip().lstrip("./")
        if h.endswith(".html") and h in self.pages:
            return h
        if h.startswith(("tel:", "mailto:", "#")):
            return html.escape(h)
        contact = next((f for f in self.pages if "contact" in f or "reserv" in f), None)
        return contact or "index.html"

    def label(self) -> str:
        self.n += 1
        return html.escape(self.theme["label"].format(n=f"{self.n:02d}"))

    def btn(self, c, ghost: bool = False) -> str:
        if not isinstance(c, dict) or not c.get("label"):
            return ""
        return f'<a class="pm-btn{" ghost" if ghost else ""}" href="{self.href(c.get("href"))}"><span>{plain(c["label"])}</span><span class="arr">→</span></a>'

    def head(self, d: dict, split: bool = False, title_tag: str = "h2") -> str:
        eb = f'<p class="pm-eyebrow" data-reveal>{e(d.get("eyebrow"))}</p>' if d.get("eyebrow") else ""
        intro = d.get("intro") or d.get("text") or ""
        right = f'<p class="pm-lead" data-reveal style="--d:.15s">{e(intro)}</p>' if intro else ""
        if not d.get("title") and not eb:
            return ""
        t = f'<{title_tag} class="pm-h pm-h2" data-split>{e(d.get("title"))}</{title_tag}>'
        if split and right:
            return f'<div class="pm-head split"><div>{eb}{t}</div>{right}</div>'
        return f'<div class="pm-head">{eb}{t}{right}</div>'


# ------------------------------------------------------------------ sections

def s_hero(c: Ctx, d: dict, first: bool) -> str:
    v = c.theme["hero"] if c.page == "index.html" else c.rnd.choice(["page", "split", "page"])
    if v == "network" and c.page != "index.html":
        v = "page"
    tag = "h1"
    eb = f'<p class="pm-eyebrow" data-reveal>{e(d.get("eyebrow"))}</p>' if d.get("eyebrow") else ""
    title = e(d.get("title") or c.p.get("name"))
    sub = f'<p class="pm-lead" data-reveal style="--d:.35s">{e(d.get("subtitle"))}</p>' if d.get("subtitle") else ""
    btns = f'<div class="pm-btns" data-reveal style="--d:.5s">{c.btn(d.get("cta"))}{c.btn(d.get("cta2"), True)}</div>'
    meta = "".join(f"<span>{plain(m)}</span>" for m in lst(d.get("meta"), 3))
    scroll = '<span class="pm-scroll"><i></i>Défiler</span>'
    if v == "cinematic":
        return f'''<section class="hero hero-cinematic"><div class="hero-bg">{c.hero_media(d.get("image"))}</div>
<div class="pm-wrap">{eb}<{tag} class="pm-h pm-h1" data-split style="margin-top:1.2rem">{title}</{tag}>{sub}{btns}
<div class="hero-meta">{scroll}<div class="hero-side">{meta}</div></div></div></section>'''
    if v == "editorial":
        words = title.split(" ")
        k = max(1, len(words) // 2)
        img = c.hero_media(d.get("image")).replace('class="pm-media', 'class="ed-img pm-media', 1)
        t = " ".join(words[:k]) + f" {img} " + " ".join(words[k:])
        badge = f'''<div class="pm-badge" aria-hidden="true"><svg viewBox="0 0 128 128"><defs><path id="bp" d="M64,64 m-50,0 a50,50 0 1,1 100,0 a50,50 0 1,1 -100,0"/></defs><text><textPath href="#bp">{plain(c.p.get("name"))[:22]} • {plain(d.get("eyebrow") or "depuis toujours")[:22]} • </textPath></text></svg><b>↓</b></div>'''
        return f'''<section class="hero hero-editorial"><div class="pm-wrap">{eb}<{tag} class="pm-h pm-h1" data-split style="margin-top:1.4rem">{t}</{tag}>
<div class="ed-cols">{sub}<div>{btns}</div>{badge}</div></div></section>'''
    if v == "split":
        tagc = f'<div class="pm-tag" data-reveal style="--d:.7s"><b>{plain((lst(d.get("meta"), 1) or [c.p.get("name")])[0])[:28]}</b>{plain(d.get("eyebrow"))[:60]}</div>' if d.get("eyebrow") or d.get("meta") else ""
        return f'''<section class="hero hero-split"><div class="pm-wrap"><div>{eb}<{tag} class="pm-h pm-h1" data-split style="margin-top:1.2rem">{title}</{tag}>{sub}{btns}</div>
<div class="split-media" data-reveal="mask">{c.hero_media(d.get("image"), parallax=0.08)}{tagc}</div></div></section>'''
    if v == "kinetic":
        words = plain(d.get("eyebrow") or c.p.get("name") or "")
        row = lambda cls: f'<div class="kin-row {cls}">' + "".join(f"<div>{(words + ' ✦ ') * 3}</div>" for _ in range(2)) + "</div>"
        return f'''<section class="hero hero-kinetic"><div class="kin-rows" aria-hidden="true">{row("")}{row("rev out")}</div>
<div class="kin-card" data-tilt data-reveal="scale">{c.hero_media(d.get("image"))}</div>
<div class="pm-wrap"><div><{tag} class="pm-h pm-h2" data-split>{title}</{tag}>{sub}</div>{btns}</div></section>'''
    if v == "network":
        bg = f'<div class="hero-bg" style="opacity:.35">{c.hero_media(d.get("image"))}</div>' if c.video else ""
        return f'''<section class="hero hero-network">{bg}<canvas data-network="globe" aria-hidden="true"></canvas>
<div class="pm-wrap">{eb}<{tag} class="pm-h pm-h1" data-split style="margin-top:1.2rem;max-width:11ch">{title}</{tag}>{sub}{btns}<div class="hero-meta">{scroll}<div class="hero-side">{meta}</div></div></div></section>'''
    return f'''<section class="hero hero-page"><div class="pm-wrap">{eb}<{tag} class="pm-h pm-h1" data-split style="margin-top:1.2rem">{title}</{tag}>{sub}
<div class="page-strip" data-reveal="mask">{c.hero_media(d.get("image"), parallax=0.1) if c.page == "index.html" else c.img(d.get("image"), eager=True, parallax=0.1)}</div></div></section>'''


def s_marquee(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 8)
    if not items:
        return ""
    band = c.rnd.random() < 0.5
    inner = "".join(f"<span>{plain(i)}</span><b>✦</b>" for i in items)
    return f'<div class="pm-marquee{" band" if band else ""}" aria-hidden="true"><div class="track"><div>{inner}</div><div>{inner}</div></div></div>'


def s_story(c: Ctx, d: dict) -> str:
    steps = lst(d.get("steps"), 5)
    if not steps:
        return ""
    side = c.rnd.choice(["", "right"])
    media = "".join(c.img(s.get("image"), "on" if i == 0 else "") for i, s in enumerate(steps))
    body = "".join(
        f'''<div class="story-step"><span class="lbl">{c.label()} {plain(s.get("kicker"))}</span>
<h3 class="pm-h pm-h2">{e(s.get("title"))}</h3><p class="pm-lead">{e(s.get("text"))}</p><span class="m">{c.img(s.get("image"))}</span></div>''' for s in steps)
    return f'''<section class="pm-section"><div class="pm-wrap">{c.head(d)}
<div class="story {side}"><div class="story-media">{media}<span class="story-count">01/{len(steps):02d}</span></div><div class="story-steps">{body}</div></div></div></section>'''


def s_statement(c: Ctx, d: dict) -> str:
    if not d.get("text"):
        return ""
    words = " ".join(f'<span class="sw">{w}</span>' for w in e(d["text"]).split(" "))
    cite = f"<cite>— {plain(d.get('author'))}</cite>" if d.get("author") else ""
    return f'<section class="pm-section statement"><div class="pm-wrap"><p>{words}</p>{cite}</div></section>'


def s_features(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 6)
    if not items:
        return ""
    if c.rnd.random() < 0.5:
        rows = "".join(
            f'''<div class="feat-row" data-reveal{f' data-peek="{c.img_url(i.get("image"))}"' if c.images else ""}><span class="num">{c.label()}</span>
<h3 class="pm-h">{e(i.get("title"))}</h3><p>{e(i.get("text"))}</p></div>''' for i in items)
        return f'<section class="pm-section"><div class="pm-wrap">{c.head(d, split=True)}<div class="feat-rows">{rows}</div></div></section>'
    cards = "".join(
        f'''<article class="card" data-tilt data-reveal style="--d:{k * 0.08:.2f}s"><span class="num">{c.label()}</span>
<div><h3 class="pm-h pm-h3">{e(i.get("title"))}</h3><p style="margin-top:.7rem">{e(i.get("text"))}</p></div></article>''' for k, i in enumerate(items))
    return f'<section class="pm-section alt"><div class="pm-wrap">{c.head(d, split=True)}<div class="feat-cards">{cards}</div></div></section>'


def s_hscroll(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 7)
    if not items:
        return ""
    cards = "".join(f'<article class="hs-item">{c.img(i.get("image"))}<h3 class="pm-h pm-h3">{e(i.get("title"))}</h3><p>{e(i.get("text"))}</p></article>' for i in items)
    return f'<section class="hs"><div class="hs-sticky"><div class="pm-wrap">{c.head(d, split=True)}</div><div class="hs-track">{cards}</div></div></section>'


def s_stats(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 4)
    if not items:
        return ""
    out = ""
    for i in items:
        try:
            val = float(str(i.get("value", 0)).replace(" ", "").replace(",", "."))
        except ValueError:
            val = 0
        val_s = f"{val:g}"
        out += f'<div class="stat" data-reveal><b><span data-count="{val_s}">0</span><small>{plain(i.get("suffix"))}</small></b><span>{e(i.get("label"))}</span></div>'
    return f'<section class="pm-section"><div class="pm-wrap">{c.head(d)}<div class="stats">{out}</div></div></section>'


def _num(v) -> float:
    try:
        return float(re.sub(r"[^\d.,-]", "", str(v)).replace(",", ".") or 0)
    except ValueError:
        return 0.0


def s_configurator(c: Ctx, d: dict) -> str:
    groups = [g for g in lst(d.get("groups"), 4) if lst(g.get("choices"), 6)]
    if not groups:
        return ""
    cur = plain(d.get("currency") or "€")
    gh = ""
    for g in groups:
        opts = ""
        for ch in lst(g.get("choices"), 6):
            price, lab = _num(ch.get("price")), plain(ch.get("label"))
            extra = f"<small>+{price:g} {cur}</small>" if price else ""
            opts += f'<button type="button" class="cfg-opt" data-label="{lab}" data-price="{price:g}">{lab}{extra}</button>'
        kind = "multi" if g.get("type") == "multi" else "single"
        gh += f'<div class="cfg-group" data-type="{kind}"><h3>{plain(g.get("name"))}</h3><div class="cfg-opts">{opts}</div></div>'
    return f'''<section class="pm-section alt"><div class="pm-wrap">{c.head(d, split=True)}
<div class="cfg" data-cfg data-base="{_num(d.get("base_price")):g}" data-currency="{cur}"><div class="cfg-view" data-reveal><p class="pm-eyebrow">Votre sélection</p><div class="cfg-list"></div>
<div class="cfg-total"><span class="pm-muted">Total estimé</span><b>0 {cur}</b></div><div class="pm-btns">{c.btn(d.get("cta") or {"label": "Valider", "href": ""})}</div></div>
<div>{gh}</div></div></div></section>'''


def s_network(c: Ctx, d: dict) -> str:
    mode = c.rnd.choice(["globe", "grid"])
    return f'''<section class="net"><canvas data-network="{mode}" aria-hidden="true"></canvas><div class="pm-wrap">
{f'<p class="pm-eyebrow" data-reveal>{e(d.get("eyebrow"))}</p>' if d.get("eyebrow") else ""}<h2 class="pm-h pm-h2" data-split style="max-width:13ch;margin-top:1rem">{e(d.get("title"))}</h2>
<p class="pm-lead" data-reveal style="margin-top:1.4rem">{e(d.get("text"))}</p><div class="pm-btns">{c.btn(d.get("cta"))}</div></div></section>'''


def s_gallery(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 8) or [{"caption": ""} for _ in range(4)]
    figs = "".join(f'<figure data-reveal="mask">{c.img(i.get("image"), parallax=c.rnd.choice([0.04, 0.08, 0.12]))}<figcaption>{c.label()} {plain(i.get("caption"))}</figcaption></figure>' for i in items)
    return f'<section class="pm-section"><div class="pm-wrap">{c.head(d, split=True)}<div class="collage">{figs}</div></div></section>'


def s_testimonials(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 4)
    if not items:
        return ""
    qs = "".join(f'<figure class="quote"><blockquote>« {e(i.get("quote"))} »</blockquote><figcaption><b>{plain(i.get("author"))}</b> · {plain(i.get("role"))}</figcaption></figure>' for i in items)
    bars = "".join(f'<button type="button" aria-label="Avis {k + 1}"></button>' for k in range(len(items)))
    return f'''<section class="pm-section alt"><div class="pm-wrap">{c.head(d)}<div data-quotes><div class="quotes">{qs}</div><div class="q-bars">{bars}</div></div>
<p class="pm-note">Avis d'exemple à remplacer par de vrais témoignages clients.</p></div></section>'''


def s_pricing(c: Ctx, d: dict) -> str:
    groups = [g for g in lst(d.get("groups"), 3) if lst(g.get("items"), 8)]
    if not groups:
        return ""
    tabs = "".join(f'<button type="button" class="{"on" if k == 0 else ""}">{plain(g.get("name"))}</button>' for k, g in enumerate(groups)) if len(groups) > 1 else ""
    panels = ""
    for k, g in enumerate(groups):
        its = "".join(
            f'''<div class="menu-item"><div class="top"><h3 class="pm-h">{e(i.get("name"))}{f'<span class="tag">{plain(i["tag"])}</span>' if i.get("tag") else ""}</h3><i></i><b>{plain(i.get("price"))}</b></div><p>{e(i.get("desc"))}</p></div>'''
            for i in lst(g.get("items"), 8))
        panels += f'<div class="tab-panel menu-list{" on" if k == 0 else ""}">{its}</div>'
    return f'<section class="pm-section"><div class="pm-wrap">{c.head(d)}<div data-tabs>{f"<div class=tabs>{tabs}</div>" if tabs else ""}{panels}</div></div></section>'


def s_process(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 6)
    if not items:
        return ""
    ps = "".join(f'<div class="proc" data-reveal><span class="lbl">{c.label()}</span><h3 class="pm-h pm-h3">{e(i.get("title"))}</h3><p>{e(i.get("text"))}</p></div>' for i in items)
    return f'<section class="pm-section"><div class="pm-wrap">{c.head(d, split=True)}<div class="process"><span class="line"></span>{ps}</div></div></section>'


def s_textimage(c: Ctx, d: dict) -> str:
    rev = c.rnd.random() < 0.5
    bl = "".join(f"<li>{e(b)}</li>" for b in lst(d.get("bullets"), 5))
    eb = f'<p class="pm-eyebrow" data-reveal>{e(d.get("eyebrow"))}</p>' if d.get("eyebrow") else ""
    return f'''<section class="pm-section"><div class="pm-wrap ti{" rev" if rev else ""}"><div class="ti-media" data-reveal="mask">{c.img(d.get("image"), parallax=0.08)}</div>
<div>{eb}<h2 class="pm-h pm-h2" data-split style="margin-top:1rem">{e(d.get("title"))}</h2><p class="pm-lead" data-reveal style="margin-top:1.4rem">{e(d.get("text"))}</p>
{f"<ul data-reveal>{bl}</ul>" if bl else ""}<div class="pm-btns">{c.btn(d.get("cta"))}</div></div></div></section>'''


def s_faq(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 8)
    if not items:
        return ""
    qs = "".join(f'<details><summary>{plain(i.get("q"))}<i></i></summary><p>{e(i.get("a"))}</p></details>' for i in items)
    return f'<section class="pm-section"><div class="pm-wrap">{c.head(d)}<div class="faq">{qs}</div></div></section>'


def s_logos(c: Ctx, d: dict) -> str:
    items = lst(d.get("items"), 10)
    if not items:
        return ""
    inner = "".join(f"<span>{plain(i)}</span>" for i in items)
    t = f'<div class="pm-wrap"><p class="pm-eyebrow" style="margin-bottom:1.6rem">{e(d.get("title"))}</p></div>' if d.get("title") else ""
    return f'<section class="pm-section" style="padding-block:4rem">{t}<div class="pm-marquee logos"><div class="track"><div>{inner}</div><div>{inner}</div></div></div></section>'


def s_cta(c: Ctx, d: dict) -> str:
    cta = d.get("cta") if isinstance(d.get("cta"), dict) else {"label": "Nous contacter", "href": ""}
    return f'''<section class="pm-section cta-giant alt"><div class="pm-wrap"><h2 class="pm-h pm-h1" data-split>{e(d.get("title"))}</h2>
<div class="cta-row" style="margin-top:2.5rem"><p class="pm-lead" data-reveal>{e(d.get("text"))}</p><a class="pm-circle" href="{c.href(cta.get("href"))}">{plain(cta.get("label"))} →</a></div></div></section>'''


def s_contact(c: Ctx, d: dict) -> str:
    rows = [("Adresse", d.get("address")), ("Téléphone", d.get("phone")), ("E-mail", d.get("email"))]
    dl = "".join(f"<div><dt>{k}</dt><dd>{plain(v)}</dd></div>" for k, v in rows if v)
    hours = lst(d.get("hours"), 7)
    if hours:
        dl += "<div><dt>Horaires</dt><dd>" + "<br>".join(plain(h) for h in hours) + "</dd></div>"
    form = '''<form class="pm-form" data-reveal><div class="pm-field"><input id="f-n" name="nom" placeholder=" " required><label for="f-n">Nom</label></div>
<div class="pm-field"><input id="f-e" name="email" type="email" placeholder=" " required><label for="f-e">E-mail</label></div>
<div class="pm-field"><input id="f-t" name="tel" placeholder=" "><label for="f-t">Téléphone</label></div>
<div class="pm-field"><textarea id="f-m" name="message" placeholder=" " required></textarea><label for="f-m">Votre message</label></div>
<button class="pm-btn" type="submit"><span>Envoyer</span><span class="arr">→</span></button><p class="ok">Merci ! Votre message a bien été envoyé (démonstration : à relier à votre messagerie).</p></form>'''
    return f'''<section class="pm-section"><div class="pm-wrap contact"><div><h2 class="pm-h pm-h2" data-split>{e(d.get("title") or "Parlons-en")}</h2>
<p class="pm-lead" data-reveal style="margin-top:1.2rem">{e(d.get("text"))}</p><dl data-reveal>{dl}</dl></div>{form}</div></section>'''


MAX_PER_PAGE = {"features": 2, "textimage": 2, "marquee": 2, "pricing": 2}

RENDER = {
    "marquee": s_marquee, "story": s_story, "statement": s_statement, "features": s_features, "hscroll": s_hscroll,
    "stats": s_stats, "configurator": s_configurator, "network": s_network, "gallery": s_gallery,
    "testimonials": s_testimonials, "pricing": s_pricing, "process": s_process, "textimage": s_textimage,
    "faq": s_faq, "logos": s_logos, "cta": s_cta, "contact": s_contact,
}


# ------------------------------------------------------------------ public API

def direction_prompt(p: dict, nimg: int) -> str:
    moods = ", ".join(f'"{k}" ({v["label"]})' for k, v in MOODS.items())
    return f"""Brief : {json.dumps(p['brief'], ensure_ascii=False)}
Choisis la direction artistique la plus forte et la plus juste pour ce projet. JSON :
{{"concept": str (idée créative en une phrase), "mood": un de [{moods}], "photo_style": str (en anglais : lumière, cadrage, grain, palette), "image_briefs": [{{"slot": str (hero, puis ambiance, produit, equipe, detail, lieu…), "prompt": str (en anglais, scène précise, cinématographique), "aspect": "16:9"|"4:5"|"1:1"}}] ({nimg} éléments, le premier = hero en 16:9)}}"""


def make_art(p: dict, raw: dict) -> dict:
    theme = pick_theme(str(raw.get("mood", "")), _seed(p))
    return {
        "concept": raw.get("concept", ""),
        "fonts": theme["fonts"],
        "palette": theme["palette"],
        "photo_style": raw.get("photo_style", ""),
        "image_briefs": raw.get("image_briefs") or [],
        "motion": "Révélations au défilement, texte découpé, sections épinglées, curseur et boutons magnétiques",
        "layout_signature": f"{theme['mood_label']} · hero {theme['hero']} · en-tête {theme['header']}",
        "use_three": False,
        "premium": theme,
    }


def page_prompt(p: dict, page: dict, images: list[dict]) -> str:
    home = page["file"] == "index.html"
    slots = ", ".join(i["slot"] for i in images) or "aucune (laisser image vide)"
    pages = ", ".join(f"{pg['file']} ({pg['title']})" for pg in p["architecture"]["pages"])
    n = "8 à 11 sections, commence par hero, varie les rythmes, termine par cta puis contact ou cta seul" if home else "4 à 7 sections, commence par hero, termine par cta ou contact"
    hints = {
        "restaurant": "pense à configurator (composer son plat/menu), pricing (la carte), story (savoir-faire).",
        "boutique": "pense à hscroll (produits), configurator (personnalisation), pricing.",
        "services": "pense à process, configurator (estimation de devis), stats, network si tech/logistique.",
        "immobilier": "pense à hscroll (biens), configurator (simulateur), stats.",
    }.get((p.get("brief") or {}).get("site_type", ""), "")
    return f"""CONTEXTE : {json.dumps({"brief": p.get("brief"), "concept": p["art"].get("concept")}, ensure_ascii=False)}
Pages du site : {pages}. Images disponibles (slots) : {slots}.

{CATALOG}

Écris le contenu de la page « {page['file']} » — {page['title']} — rôle : {page.get('purpose', '')} — sujets : {', '.join(page.get('sections', []))}.
Contraintes : {n}. N'utilise jamais deux fois le même type à la suite. {hints}
Textes en français, concrets, persuasifs, propres à CE métier (meilleurs arguments de vente, bénéfices, preuves), jamais de lorem ipsum ni de formules creuses. Titres courts et marquants, utilise *un mot* en emphase de temps en temps. Les "href" pointent vers les pages ci-dessus.
JSON attendu : {{"title": str (balise title SEO), "description": str (meta description), "sections": [{{"type": ..., ...champs}}]}}"""


def _fonts_link(theme: dict) -> str:
    fams = []
    for f in dict.fromkeys([theme["fonts"]["heading"], theme["fonts"]["body"]]):
        fams.append("family=" + urllib.parse.quote_plus(f) + (":ital,wght@0,400;0,600;0,700;1,400" if f == theme["fonts"]["body"] else ""))
    return "https://fonts.googleapis.com/css2?" + "&".join(fams) + "&display=swap"


def system_files(p: dict, images: list[dict]) -> dict[str, str]:
    t = p["art"]["premium"]
    pal = t["palette"]
    name = plain(p.get("name") or "Studio")
    nav_pages = [pg for pg in p["architecture"]["pages"] if pg.get("purpose") != "Page légale"]
    contact = next((pg["file"] for pg in nav_pages if "contact" in pg["file"] or "reserv" in pg["file"]), nav_pages[-1]["file"] if nav_pages else "index.html")
    links = "".join(f'<a href="{pg["file"]}">{plain(pg["title"])}</a>' for pg in nav_pages if pg["file"] != "index.html")
    mlinks = "".join(f'<a href="{pg["file"]}">{plain(pg["title"])}</a>' for pg in nav_pages)
    words = name.split(" ")
    logo = " ".join(words[:-1]) + (" " if len(words) > 1 else "") + f"{words[-1]}<i>.</i>"
    head = f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{_fonts_link(t)}" rel="stylesheet">
<link rel="stylesheet" href="styles.css">
<style>:root{{--bg:{pal["background"]};--surface:{pal["surface"]};--text:{pal["text"]};--muted:{pal["muted"]};--accent:{pal["accent"]};--accent2:{pal["accent2"]};--accent-ink:{t["accent_ink"]};--font-h:"{t["fonts"]["heading"]}";--font-b:"{t["fonts"]["body"]}";--h-case:{t["case"]};--h-weight:{t["weight"]};--h-track:{t["tracking"]};--radius:{t["radius"]};--r-media:{ {"0px": "0px", "6px": "8px", "18px": "20px"}.get(t["radius"], "26px") };--scale:{t["scale"]};color-scheme:{"dark" if t["dark"] else "light"}}}</style>'''
    loader = f'<div class="pm-loader" aria-hidden="true"><b>{name}</b><span>0</span></div>' if t["loader"] else ""
    header = f'''{loader}<div class="pm-curtain" aria-hidden="true"></div>{'<div class="pm-cursor" aria-hidden="true"></div>' if t["cursor"] != "none" else ""}{'<div class="pm-grain" aria-hidden="true"></div>' if t["grain"] else ""}<div class="pm-peek" aria-hidden="true"><img alt=""></div>
<header class="pm-header"><div class="pm-wrap"><a class="pm-logo" href="index.html">{logo}</a><nav class="pm-nav" aria-label="Navigation principale">{links}</nav>
<a class="pm-btn pm-cta" href="{contact}"><span>Nous contacter</span><span class="arr">→</span></a><button class="pm-burger" type="button" aria-label="Menu" aria-expanded="false"><i></i><i></i></button></div></header>
<nav class="pm-menu" aria-label="Menu mobile">{mlinks}</nav>'''
    brief = p.get("brief") or {}
    giant = f'<div class="foot-word" aria-hidden="true">{name}</div>' if t["footer"] == "giant" else ""
    footer = f'''<footer class="pm-footer"><div class="pm-wrap"><div class="foot-grid">
<div><a class="pm-logo" href="index.html">{logo}</a><p class="pm-muted" style="margin-top:1rem;max-width:30ch">{plain(brief.get("positioning"))[:160]}</p></div>
<div><h4>Navigation</h4><ul>{"".join(f'<li><a href="{pg["file"]}">{plain(pg["title"])}</a></li>' for pg in nav_pages)}</ul></div>
<div><h4>Contact</h4><ul><li><a href="{contact}">Écrire un message</a></li><li>[TÉLÉPHONE]</li><li>[ADRESSE]</li></ul></div>
<div><h4>Informations</h4><ul><li><a href="mentions-legales.html">Mentions légales</a></li><li><a href="confidentialite.html">Confidentialité</a></li></ul></div>
</div>{giant}<div class="foot-bottom"><span>© <span data-year></span> {name}</span>{"<span>Images illustratives générées par IA</span>" if images else ""}<span class="forma-credit">Site web créé par Forma</span></div></div></footer>'''
    return {"_head.html": head, "_header.html": header, "_footer.html": footer, "styles.css": RUNTIME_CSS, "app.js": RUNTIME_JS}


def body_class(p: dict) -> str:
    t = p["art"]["premium"]
    return f"pm cursor-{t['cursor']} header-{t['header']} mood-{t['mood']}"


def render_page(p: dict, page: dict, content: dict, images: list[dict]) -> str:
    c = Ctx(p, images, page["file"])
    secs = [s for s in (content.get("sections") or []) if isinstance(s, dict) and s.get("type") in SECTION_TYPES]
    if not secs or secs[0].get("type") != "hero":
        secs.insert(0, {"type": "hero", "title": page.get("title"), "subtitle": page.get("purpose")})
    out, prev, seen = [], None, {}
    for k, s in enumerate(secs[:14]):
        t = s["type"]
        if t == prev or (t == "hero" and k) or seen.get(t, 0) >= MAX_PER_PAGE.get(t, 1):
            continue
        seen[t] = seen.get(t, 0) + 1
        c.n = 0
        try:
            out.append(s_hero(c, s, k == 0) if t == "hero" else RENDER[t](c, s))
        except Exception:  # a malformed section must never break the page
            continue
        prev = t
    title = plain(content.get("title") or f"{page.get('title')} — {p.get('name')}")[:90]
    desc = plain(content.get("description") or page.get("purpose") or "")[:170]
    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<!--HEAD-->
<title>{title}</title>
<meta name="description" content="{desc}">
</head>
<body class="{body_class(p)}">
<!--HEADER-->
<main>
{chr(10).join(o for o in out if o)}
</main>
<!--FOOTER-->
<script src="app.js" defer></script>
</body>
</html>
'''


def seed_hash(p: dict) -> str:
    return hashlib.sha1(_seed(p).encode()).hexdigest()[:8]
