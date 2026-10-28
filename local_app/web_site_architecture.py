"""Site-map planning: make multi-page websites only when structure warrants it.

This guidance complements the user's aesthetic choices. It does not force 3D,
React, or multiple pages on a small landing page.
"""
import re
import unicodedata


def plain(text):
    s=unicodedata.normalize("NFKD",str(text or "").lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def plan(request):
    text=plain(request)
    single=bool(re.search(
        r"\b(?:one[\s-]*page|monopage|page unique|une seule page|landing page|site vitrine une page)\b",
        text))
    explicit_multi=bool(re.search(
        r"\b(?:plusieurs pages|multi[\s-]*pages|pages distinctes|page dediee|page separee)\b",
        text))
    services=bool(re.search(r"\b(?:services?|prestations?|soins?|toilett\w*)\b",text))
    portfolio=bool(re.search(r"\b(?:realisations?|portfolio|galerie|avant.apres|photos? client\w*)\b",text))
    booking=bool(re.search(r"\b(?:prise de rdv|rendez[\s-]*vous|reservation|reserver|formulaire.*rdv)\b",text))
    shop=bool(re.search(r"\b(?:boutique en ligne|e-?commerce|catalogue|fiche\w* produit|panier)\b",text))
    contact=bool(re.search(r"\b(?:contact|adresse|horaires?|localisation|acces)\b",text))
    about=bool(re.search(r"\b(?:a propos|notre equipe|qui sommes-nous|notre histoire)\b",text))
    # Industry-aware defaults. A stylist needs a short booking path;
    # a handmade-soap retailer needs proper catalog and product details.
    salon=bool(re.search(r"\b(?:coiffeur\w*|coiffure|barbier\w*|hairdress\w*|barber\w*)\b",text))
    products=bool(re.search(
        r"\b(?:savon\w*|cosmetique\w*|produit\w* artisan\w*|e-?commerce|boutique en ligne)\b",text))
    # A company map brief often says 'do not invent appointment booking' in
    # disclaimers. Do not turn that negative instruction into a requirement.
    if salon and not (single and not explicit_multi):
        return {"mode":"multi","pages":[("home","Accueil","/"),
                ("booking","Rendez-vous","/rendez-vous")],
                "reason":"Coiffure : présentation rapide sur l'accueil et parcours de rendez-vous dédié."}
    if products and not (single and not explicit_multi):
        return {"mode":"multi","pages":[("home","Accueil","/"),
                ("catalog","Catalogue","/catalogue"),
                ("product","Fiches produits","/produits"),
                ("contact","Contact et informations","/contact")],
                "reason":"Commerce de produits : catalogue, fiches individuelles et accès aux informations utiles."}
    # A typical professional service business has one focused home plus
    # dedicated pages for service details, past work and scheduling.
    roles=[]
    if services:roles.append(("services","Prestations","/prestations"))
    if portfolio:roles.append(("gallery","Réalisations","/realisations"))
    if booking:roles.append(("booking","Rendez-vous","/rendez-vous"))
    if shop:roles.append(("catalog","Boutique","/boutique"))
    if about:roles.append(("about","À propos","/a-propos"))
    if contact and not booking:roles.append(("contact","Contact","/contact"))
    if single and not explicit_multi:
        return {"mode":"single","pages":[("home","Accueil","/")],
                "reason":"La demande décrit explicitement une page unique."}
    if len(roles)<2 and not explicit_multi:
        return {"mode":"single","pages":[("home","Accueil","/")],
                "reason":"Une page d'accueil soignée suffit pour ce contenu."}
    return {"mode":"multi","pages":[("home","Accueil","/")]+roles,
            "reason":"Séparer les parcours importants évite une page d'accueil surchargée."}


def instructions(request):
    architecture=plan(request)
    if architecture["mode"]=="single":
        return (
            "ARCHITECTURE: une SEULE page est appropriée à cette demande. "
            "Sections courtes, hiérarchie claire, navigation d'ancrage si nécessaire. "
            "Ne fabrique pas de sous-pages inutiles. "
            "Si l'utilisateur demande ensuite plus de fonctionnalités, tu peux créer des pages."
        )
    pages=architecture["pages"]
    page_list="; ".join(label+" -> "+route for _,label,route in pages)
    return (
        "ARCHITECTURE MULTI-PAGES EXIGÉE PAR LE CONTENU : "+page_list+". "
        "Créer de VRAIES pages/pages de navigation, PAS uniquement une longue homepage "
        "avec des ancres #services / #galerie. La page d'accueil doit introduire l'activité, "
        "montrer une courte sélection et offrir des appels à l'action vers les pages dédiées; "
        "laisser les services détaillés, la galerie complète et la réservation sur leurs pages. "
        "Tous les liens de navigation doivent fonctionner DANS l'aperçu local. "
        "En HTML utiliser de vrais documents (prestations.html, realisations.html, rendez-vous.html) "
        "et des liens relatifs corrects. En React/Vite, créer des composants de pages et un "
        "véritable système de navigation compatible avec un serveur statique (hash router "
        "#/prestations, #/realisations, #/rendez-vous, ou routeur avec fallback explicite). "
        "Les données et le style doivent être partagés, chaque page doit avoir un vrai contenu. "
        "NE PAS imposer cet agencement à une landing page explicitement monopage."
    )


_ROUTE_ALIASES={
 "services":("prestations","services","soins","nos-services"),
 "gallery":("realisations","galerie","portfolio","avant-apres"),
 "booking":("rendez-vous","reservation","rendezvous","prendre-rdv","rdv"),
 "catalog":("boutique","catalogue","produits","shop"),
 "product":("produits","produit","fiches-produits","product"),
 "about":("a-propos","about","equipe","histoire"),
 "contact":("contact",),
}

def check(files,request):
    layout=plan(request)
    if layout["mode"]!="multi":
        return []
    paths=[plain(str(p).replace("\\","/")) for p in files]
    source="\n".join(str(x) for key,x in files.items()
                     if str(key).endswith((".html",".jsx",".tsx",".js",".ts",".vue",".svelte")))
    normalized=plain(source)
    # Page sections alone are not routes; verify actual navigation targets.
    linked = re.findall(
        r"""(?:href|to|path|navigate|location\.hash|router\.push|window\.location)\s*
             (?:=|\(|:)\s*["']([^"']{1,110})["']""",
        normalized, re.I | re.X,
    )
    # Literal href values and route constants also cover generated JSX menus.
    linked += re.findall(r"""["']((?:#?/)?[a-z0-9-]+(?:/[a-z0-9-]+)*\.html|#?/[a-z0-9/-]+)["']""",
                         normalized)
    linked = [plain(x) for x in linked]
    is_spa = any(str(key).endswith((".jsx",".tsx",".vue",".svelte")) for key in files) or (
        any(str(key).endswith(("package.json",)) for key in files))
    missing=[]
    for role,title,route in layout["pages"][1:]:
        aliases=_ROUTE_ALIASES.get(role,(role,))
        def valid_name(value):
            return any(re.search(r"(^|/|#|-)" + re.escape(alias) + r"([/?#.-]|$)",value)
                       for alias in aliases)
        in_path = any(valid_name(p) and p.endswith(".html") for p in paths)
        in_link = any(valid_name(link) and not re.match(r"^#(?!/)",link)
                      for link in linked)
        # HTML multi-page sites must link to a corresponding real document.
        # SPAs must have routes in the source. Anchors like #services are not pages.
        if not in_link or (not is_spa and not in_path):
            missing.append(title)
    if not missing:
        return []
    return [{"id":"site_architecture","fix":
             "Le site doit avoir des pages dédiées et accessibles dans la navigation pour : "+
             ", ".join(missing)+
             ". Garde sur l'accueil uniquement une introduction et des aperçus avec liens. "
             "Ne remplace pas ces pages par des ancres dans une seule page."}]
