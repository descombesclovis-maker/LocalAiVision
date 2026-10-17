"""User-intent contract enforced on both HTML and React/Vite websites.

The checks protect explicit facts (brand, activity, sections, language, palette).
They are deliberately separate from subjective design critique. When uncertain,
the generator should ask for clarification rather than make up a different brand.
"""
from __future__ import annotations
import colorsys
import re
import unicodedata

GENERIC_NAMES={"nouveau projet","mon nouveau site","mon site web","mon premier site",
               "mon site","site web","untitled","website","preview"}
APP_EXT=(".html",".htm",".jsx",".tsx",".js",".ts",".vue",".svelte",".css",".json")
FR_MARKERS=r'\b(?:toilettage|toiletterie|toiletage|toiletteur|toiletteuse|bain|brossage|coupe|chien|chat|animaux|pelage)\b'
BOOKING=r'\b(?:rendez[\s-]*vous|rdv|reservation|reserver|prendre rendez[\s-]*vous)\b'
GALLERY=r'\b(?:realisations?|galerie|avant[\s/-]*apres|nos clients?|vos animaux|portfolio)\b'
SERVICES=r'\b(?:services?|prestations?|formules?|soins?|toilettages?)\b'
ENGLISH_UI=(
    "the workspace","why forma","try the workspace","make room for","your best work",
    "find your flow","your projects","our services","our work","book now",
    "book an appointment","contact us","get started","learn more","view pricing",
    "new project","how it works","a little clarity","your next chapter",
    "no signup needed","a calmer kind of","good things start with space",
    "welcome to your space","pricing","workspace", "your projects, plans",
)

def normalize(text):
    value=unicodedata.normalize("NFKD",str(text or "").casefold())
    return "".join(char for char in value if not unicodedata.combining(char))

def _brand_from_request(request):
    raw=str(request or "").strip()
    # Handles « PawMood est un site ... » and « Le site s'appelle Poisson-Trap ».
    match=re.match(r"^\s*([A-Za-zÀ-ÿ0-9][\wÀ-ÿ-]{2,65})\s+est\s+(?:un|une|le|la)\s+",raw,re.I)
    if match:return match.group(1)
    match=re.search(r"(?:site\s+)?s['’]appelle\s+[«\"']?([\wÀ-ÿ-]{3,65})",raw,re.I)
    return match.group(1) if match else ""

def specification(request, project_name=""):
    text=normalize(request)
    brand=_brand_from_request(request)
    candidate=str(project_name or "").strip()
    if not brand and candidate and normalize(candidate) not in GENERIC_NAMES and not candidate.startswith("web-"):
        brand=candidate
    groom=bool(re.search(r"\b(?:toilett\w*|toiletage|toileter|grooming)\b",text))
    pet=bool(re.search(r"\b(?:chien\w*|chat\w*|animau\w*|animal|canin|felin|toilett\w*)\b",text))
    grooming=groom and pet
    booking=bool(re.search(r"\b(?:rendez[\s-]*vous|rdv|reservation|reserver|prise de rdv)\b",text))
    gallery=bool(re.search(r"\b(?:realisations?|galerie|avant[\s/-]*apres|client\w*)\b",text))
    services=bool(re.search(r"\b(?:services?|prestations?|soins?|toilettage)\b",text))
    requested_colors=[]
    for word in ("bleu","vert","blanc","rouge","orange","noir","violet","rose","jaune"):
        if re.search(r"\b"+word+r"\w*\b",text):
            requested_colors.append(word)
    return {
        "request":str(request or ""),
        "brand":brand,
        "locale":"fr-FR",
        "business":"toilettage pour animaux" if grooming else "",
        "grooming":grooming,
        "booking":booking,
        "gallery":gallery,
        "services":services,
        "colors":requested_colors,
        "needs_photos":bool(re.search(r"\b(?:vrai\w* photo\w*|photograph\w*|photo\w* d.animaux|photo\w*)\b",text)),
    }

def project_request(store, project_id, latest):
    """Preserve the original activity during later prompts like 'make it prettier'.

    The first substantial user brief or the saved pre-generation brief is treated
    as the ongoing contract, unless the user explicitly asks to start over.
    """
    request=str(latest or '').strip()
    if re.search(r"\b(?:change compl[eè]tement de secteur|change d'activit[eé]|nouveau cahier des charges)\b",
                 request,re.I):
        return request
    meta=store.meta(project_id)
    plan=meta.get('generation_plan') or {}
    original=str(plan.get('original') or '').strip()
    if not original:
        for entry in store.chat_history(project_id):
            if entry.get('role')!='user':continue
            candidate=str(entry.get('text') or '').strip()
            if len(candidate)>=65 and (
                re.search(r"\b(?:site|boutique|application|salon|toilett\w*|commerce)\b",
                          normalize(candidate))):
                original=candidate
                break
    if not original or original==request:return request
    return ('CAHIER DES CHARGES INITIAL À PRÉSERVER :\n'+original+
            '\n\nDEMANDE ACTUELLE POUR MODIFIER LE SITE :\n'+request)


def agent_instructions(spec):
    colors=", ".join(spec["colors"]) if spec["colors"] else "selon le brief"
    parts=[
      "CONTRAT CLIENT PRIORITAIRE — EXIGENCES NON NÉGOCIABLES :",
      "LANGUE DU SITE : français de France (fr-FR) UNIQUEMENT. Tous les textes visibles "
      "(en-têtes, navigation, boutons, descriptions, formulaires, messages, SEO, titres, "
      "légendes, attributs alt) doivent être rédigés en français. "
      "Utilise <html lang=\"fr\">. L'anglais est réservé uniquement aux noms de bibliothèques "
      "et aux identifiants techniques de code. Ne pas créer d'interface en anglais.",
      "IDENTITÉ CLIENT : "+(spec["brand"] or "nom à déterminer du brief")+
      ". N'invente aucune autre marque ou produit SaaS.",
      "PALETTE EXPLICITE : "+colors+". Respecte-la dans les éléments visibles.",
      "DEMANDE ORIGINALE EXACTE (ne jamais la remplacer par un template) :\n"+spec["request"],
      "Ne jamais générer une marque générique telle que forma., ni un espace de "
      "productivité, une landing page de SaaS ou un tableau de bord à la place de "
      "l'activité demandée. Les prompts exemples trouvés dans le code préexistant ne "
      "sont PAS le cahier des charges.",
    ]
    if spec["grooming"]:
        parts.append(
            "MÉTIER : site de toilettage pour animaux, PAS de logiciel de productivité. "
            "Visuels de chiens/chats et d'un salon de toilettage, textes parlant de "
            "bain, coupe, brossage et soins appropriés; univers accueillant et rassurant. "
            "Reste simple, élégant et professionnel ; aucune 3D obligatoire.")
    if spec["booking"]:
        parts.append(
            "RENDEZ-VOUS : propose un véritable formulaire ergonomique avec coordonnées, "
            "animal, prestation, date et horaire souhaités, validation et états "
            "compréhensibles en français. Si aucun backend n'est connecté, précise "
            "qu'il s'agit d'une demande de rendez-vous et NE SIMULE PAS une réservation "
            "confirmée ou enregistrée côté serveur.")
    if spec["gallery"]:
        parts.append(
            "RÉALISATIONS : montre une galerie de toilettages avec photographies adéquates "
            "si elles existent; ne prétends pas que des images synthétiques sont de "
            "véritables travaux réalisés sur des clients identifiables.")
    if spec["services"]:
        parts.append(
            "SERVICES : présente des prestations réelles et cohérentes avec l'activité, "
            "sans inventer de tarifs confirmés par le propriétaire.")
    if spec["needs_photos"]:
        parts.append(
            "PHOTOS : privilégie de véritables photos d'animaux libres de droits avec "
            "licence vérifiée ou les assets présents dans le projet. Si seuls des visuels "
            "générés par IA sont disponibles, présente-les comme ILLUSTRATIFS, jamais "
            "comme de vraies réalisations de clients. Ne fabrique pas de preuve sociale.")
    return "\n".join(parts)

def _site_sources(files):
    chunks=[]
    for name,value in files.items():
        path=str(name).replace("\\","/").lower()
        if path.endswith(APP_EXT) and not any(p in path.split("/") for p in
                                                   ("node_modules","dist","build",".next")):
            if path.endswith(("package.json","package-lock.json","tsconfig.json")):continue
            chunks.append(str(value))
    return "\n".join(chunks)

def _color_hues(source):
    values=[]
    for value in re.findall(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b",source):
        bits=value.lstrip("#")
        if len(bits)==3:bits="".join(x*2 for x in bits)
        if len(bits)!=6:continue
        try:
            rgb=[int(bits[i:i+2],16)/255 for i in (0,2,4)]
            hue,luminance,saturation=colorsys.rgb_to_hls(*rgb)
            values.append((hue*360,luminance,saturation))
        except ValueError:pass
    return values

def check(files, spec):
    """Return precise, actionable violations; does not claim to assess artistic beauty."""
    source=_site_sources(files)
    norm=normalize(source)
    index=str(files.get("index.html") or "")
    findings=[]
    def fail(key,fix):
        findings.append({"id":key,"fix":fix})
    brand=spec["brand"]
    if brand and normalize(brand) not in norm:
        fail("brand_identity",f"Le nom {brand} doit apparaître dans le contenu visible de la page, pas seulement dans le nom du projet.")
    if spec["grooming"]:
        if len(re.findall(FR_MARKERS,norm))<2:
            fail("wrong_business","Le site doit parler de toilettage pour chiens/chats et d'animaux. Supprimer les contenus SaaS, bureaux, productivité, workspace.")
        if re.search(r"\b(?:forma\.|workspace|best work|productivity|project management)\b",norm) and (
            not re.search(r"\b(?:toilettage|toiletterie|animaux|chien|chat)\b",norm)):
            fail("foreign_template","Ne réutilise pas de template forma./productivité au lieu du salon de toilettage.")
    if spec["booking"]:
        if not re.search(BOOKING,norm):
            fail("booking_content","Créer une section Prendre rendez-vous / Demander un rendez-vous.")
        if not re.search(r"<form\b|onsubmit\b|onSubmit\b|<input\b|<textarea\b|<select\b",source):
            fail("booking_form","Créer un véritable formulaire de prise de rendez-vous, pas un simple bouton.")
    if spec["services"] and not re.search(SERVICES,norm):
        fail("services","Créer une présentation des services de l'activité.")
    if spec["gallery"] and not re.search(GALLERY,norm):
        fail("customer_gallery","Créer une section Réalisations ou Galerie.")
    if not re.search(r"<html\b[^>]*\blang\s*=\s*['\"]fr(?:-FR)?['\"]",index,re.I):
        fail("french_document","Définir <html lang=\"fr\"> pour la langue du document.")
    en=[phrase for phrase in ENGLISH_UI if re.search(r"(?<![a-z])"+re.escape(phrase)+r"(?![a-z])",norm)]
    if en:
        fail("english_ui","Remplacer TOUS les textes anglais visibles par du français, dont : "+", ".join(en[:6])+".")
    if "bleu" in spec["colors"]:
        hues=_color_hues(source)
        if not any(188<=h<=265 and sat>.24 and .10<lum<.93 for h,lum,sat in hues) and not re.search(r"\b(?:blue|cyan|sky|bleu)\b",source,re.I):
            fail("blue_palette","Inclure la couleur bleue souhaitée dans les éléments visuels réels du site.")
    if "vert" in spec["colors"]:
        hues=_color_hues(source)
        if not any(75<=h<=175 and sat>.2 and .1<lum<.93 for h,lum,sat in hues) and not re.search(r"\b(?:green|emerald|teal|vert|lime)\b",source,re.I):
            fail("green_palette","Inclure le vert souhaité dans la palette réelle du site.")
    return findings
