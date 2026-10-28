"""FORMA quotation and verified final invoicing for *locally created* sites.

Market-reference prices are indicative catalogue inputs (French freelance and
agency pricing references as at Oct 2026); 30% discount is applied per line.
Never call an estimate an issued invoice or invent business/customer details.
Issue sequential non-reusable invoices only after explicit validation.
"""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
import json
import re
import threading

BRAND="FORMA"
SELLER_DEFAULT={"name":"Lilian Descombes","siret":"53784237900027"}
DISCOUNT=Decimal("0.30")
# Indicative 2026 baseline values, not a real-time market-price feed.
CATALOG={
 "vitrine":("Conception sur mesure d'un site vitrine",1500),
 "landing":("Conception d'une page de présentation",900),
 "multipage":("Architecture et navigation multipages",600),
 "booking":("Formulaire et expérience de demande de rendez-vous",400),
 "catalog":("Catalogue produits et navigation",800),
 "products":("Fiches et présentation détaillée des produits",350),
 "checkout":("Intégration du parcours de commande et paiement",650),
 "gallery":("Galerie et présentation de réalisations",220),
 "seo":("Optimisation SEO technique et métadonnées",200),
 "motion":("Animations et micro-interactions adaptées à la marque",450),
 "identity":("Direction artistique / identité graphique",600),
 "domain":("Configuration technique d'un domaine fourni",120),
 "maintenance":("Maintenance annuelle contractuelle (option)",450)
}
_REFERENCE_LINKS=[
 "https://onweb24.com/fr/guide/prix-site-internet",
 "https://dgtl.fr/tarif-creation-site-internet-professionnel/",
 "https://entreprendre.service-public.gouv.fr/vosdroits/F31808"
]
_LOCK=threading.RLock()

def money(value):
    return Decimal(str(value)).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)

def estimate(store,project_id):
    meta=store.meta(project_id)
    files=store.text_files(project_id)
    html="\n".join(x for key,x in files.items() if key.endswith((".html",".tsx",".jsx",".vue",".svelte")))
    code=html.lower()
    total_files=len(files)
    page_count=sum(1 for key in files if key.endswith(".html"))
    route_count=len(set(re.findall(r"""(?:href|to|path)\s*[:=]\s*["'](?:#)?/([\w-]{3,})""",html)))
    is_multi=page_count>=2 or route_count>=2
    tokens=set()
    if total_files>0:
        tokens.add("vitrine" if is_multi else "landing")
        tokens.add("identity") if "design_intent.md" in {x.lower() for x in files} else None
        if is_multi:tokens.add("multipage")
        if re.search(r"rendez.{0,6}vous|reservation|booking",code):
            if re.search(r"<form\b|<input\b|onsubmit",code):tokens.add("booking")
        if re.search(r"catalogue|catalog|produit",code):tokens.add("catalog")
        if re.search(r"fiche.{0,15}produit|product.?detail|pageproduit",code):
            tokens.add("products")
        if re.search(r"checkout|stripe|paymentintent|process.env.STRIPE",code):
            # Preliminary detection only; requires integration and payment test.
            tokens.add("checkout")
        if re.search(r"galerie|realisations|portfolio",code):tokens.add("gallery")
        if re.search(r"<meta.{0,100}description|<title>",html,re.I):tokens.add("seo")
        css="\n".join(value for key,value in files.items() if key.endswith(".css"))
        if "transition" in css or "animation" in css:tokens.add("motion")
        if (meta.get("deployment") or {}).get("custom_domain"):tokens.add("domain")
    # An empty starter project is not a delivered website and has no billable features.
    items=[]
    for ident in CATALOG:
        if ident not in tokens:continue
        description,market=CATALOG[ident]
        discounted=money(Decimal(market)*(Decimal(1)-DISCOUNT))
        items.append({"id":ident,"label":description,"market_eur":str(money(market)),
                      "discount_pct":30,"unit_eur":str(discounted),"qty":1,
                      "subtotal_eur":str(discounted),
                      "provisional":True})
    total=sum((money(item["subtotal_eur"]) for item in items),Decimal(0))
    return {"project_id":project_id,"project_name":meta.get("name",""),
            "items":items,"subtotal_eur":str(money(total)),
            "currency":"EUR","discount_pct":30,"estimate_only":True,
            "notice":"Chiffrage indicatif à vérifier : seules les fonctionnalités réellement livrées et acceptées peuvent être facturées. Achat du domaine et hébergement exclus. Ne constitue pas une facture ni un devis accepté. Ce PDF n'est pas une facture électronique structurée transmise par une plateforme agréée.",
            "sources":_REFERENCE_LINKS}


def validate_parties(seller,customer):
    if not isinstance(seller,dict) or not isinstance(customer,dict):
        raise ValueError("Renseigne les deux identités de facturation.")
    name=str(seller.get("name") or SELLER_DEFAULT["name"]).strip()
    siret=re.sub(r"\s","",str(seller.get("siret") or SELLER_DEFAULT["siret"]))
    if not re.fullmatch(r"\d{14}",siret):
        raise ValueError("Le SIRET du prestataire doit contenir 14 chiffres.")
    doubled=sum((n*2//10+n*2%10) if idx%2==0 else n
                for idx,n in enumerate(map(int,siret)))
    if doubled%10:
        raise ValueError("Le SIRET fourni échoue au contrôle de validité.")
    if not str(seller.get("address") or "").strip():
        raise ValueError("Adresse professionnelle de FORMA obligatoire.")
    legal=str(seller.get("legal_form") or "").strip()
    if legal not in ("EI","micro-entrepreneur EI","SASU","SAS","EURL","SARL","autre société"):
        raise ValueError("Précise la forme juridique réelle du prestataire (EI, SASU, etc.).")
    if legal in ("SASU","SAS","EURL","SARL","autre société") and not str(seller.get("capital") or "").strip():
        raise ValueError("Capital social à renseigner pour une société.")
    vat_mode=str(seller.get("vat_mode") or "")
    if vat_mode not in ("franchise","standard"):
        raise ValueError("Confirme le régime de TVA avant d'émettre une facture.")
    if vat_mode=="standard" and not str(seller.get("vat_number") or ""):
        raise ValueError("Numéro de TVA intracommunautaire requis si assujetti.")
    if not str(customer.get("name") or "").strip():
        raise ValueError("Nom ou raison sociale du client obligatoire.")
    if not str(customer.get("address") or "").strip():
        raise ValueError("Adresse de facturation du client obligatoire.")
    if str(customer.get("type") or "") not in ("business","consumer"):
        raise ValueError("Précise si le client est une entreprise ou un particulier.")
    if not str(seller.get("payment_details") or "").strip():
        raise ValueError("Coordonnées ou instructions de paiement obligatoires.")
    if customer.get("type")=="business" and not str(seller.get("late_penalty_rate") or "").strip():
        raise ValueError("Précise le taux de pénalités de retard applicable au client professionnel.")
    return {"seller":dict(seller,name=name,siret=siret),"customer":dict(customer),
            "vat_mode":vat_mode}


def issue(store,project_id,invoice_store,seller,customer,item_ids,
          accepted=False,service_date="",due_days=30):
    """Generate final numbered invoice ONLY after explicit seller approval."""
    if accepted is not True:
        raise ValueError("Validation explicite de la facture et des prestations exigée.")
    validated=validate_parties(seller,customer)
    estimate_data=estimate(store,project_id)
    available={item["id"]:item for item in estimate_data["items"]}
    selected=list(dict.fromkeys(item_ids or []))
    if not selected or any(x not in available for x in selected):
        raise ValueError("Sélectionne uniquement des fonctionnalités réellement chiffrées.")
    if not service_date:
        raise ValueError("Date de réalisation de la prestation obligatoire.")
    try:
        worked=date.fromisoformat(service_date)
    except ValueError:
        raise ValueError("Date de prestation invalide (AAAA-MM-JJ).") from None
    if worked>date.today():
        raise ValueError("La date de prestation doit correspondre à une réalisation effective (pas une date future).")
    try:days=int(due_days)
    except (ValueError,TypeError):days=30
    if days<0 or days>120:raise ValueError("Échéance de paiement invalide.")
    items=[available[x] for x in selected]
    subtotal=sum((money(x["subtotal_eur"]) for x in items),Decimal(0))
    vat=money(subtotal*Decimal(".20")) if validated["vat_mode"]=="standard" else Decimal(0)
    total=money(subtotal+vat)
    store.meta(project_id)
    folder=Path(invoice_store).resolve();folder.mkdir(parents=True,exist_ok=True)
    with _LOCK:
        registry=folder/"invoice-sequence.json"
        try:sequence=json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else {}
        except (ValueError,OSError):raise RuntimeError("Registre des factures endommagé : ne pas émettre de numéro en double.")
        current=date.today()
        key=str(current.year)
        number=int(sequence.get(key) or 0)+1
        invoice_id=f"FORMA-{current.year}-{number:05d}"
        data={
            "invoice_number":invoice_id,"issue_date":current.isoformat(),
            "service_date":service_date,
            "due_date":(current+timedelta(days=days)).isoformat(),
            "project_id":project_id,"project_name":estimate_data["project_name"],
            "seller":validated["seller"],"customer":validated["customer"],
            "items":items,"subtotal_eur":str(money(subtotal)),
            "vat_mode":validated["vat_mode"],"vat_eur":str(vat),
            "total_eur":str(total),"currency":"EUR","status":"issued_unpaid",
            "discount_pct":30,"references":_REFERENCE_LINKS,
            "confirmation":"Validation explicite par l'émetteur sur les parties, les montants et la prestation."
        }
        # Produce final PDF before committing sequence and archive.
        pdf=pdf_bytes(data)
        path=folder/(invoice_id+".pdf")
        if path.exists():raise RuntimeError("Numéro déjà attribué : archivage non écrasé.")
        path.write_bytes(pdf)
        (folder/(invoice_id+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        sequence[key]=number
        tmp=folder/"invoice-sequence.new"
        tmp.write_text(json.dumps(sequence,indent=2),encoding="utf-8")
        tmp.replace(registry)
    return {"ok":True,"invoice_number":invoice_id,"total_eur":str(total),
            "download":"/api/web/invoice/file?number="+invoice_id,
            "status":"issued_unpaid","data":data}


def pdf_bytes(data):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    out=BytesIO()
    p=canvas.Canvas(out,pagesize=A4)
    p.setTitle("FORMA | Facture "+data["invoice_number"])
    w,h=A4
    def label(x,y,value,size=10,bold=False,color="#282331"):
        p.setFillColor(colors.HexColor(color))
        p.setFont("Helvetica-Bold" if bold else "Helvetica",size)
        p.drawString(x,y,str(value)[:108])
    p.setFillColor(colors.HexColor("#161221"));p.rect(0,h-132,w,132,fill=1,stroke=0)
    p.setFillColor(colors.HexColor("#b99bea"))
    p.setFont("Helvetica-Bold",34);p.drawString(48,h-82,"FORMA")
    p.setFillColor(colors.white);p.setFont("Helvetica",10);p.drawString(48,h-108,"STUDIO WEB  /  DOCUMENT COMMERCIAL")
    label(48,h-176,"FACTURE "+data["invoice_number"],16,True)
    label(48,h-199,"Émise le "+data["issue_date"]+"   |   Prestation : "+data["service_date"],9)
    label(48,h-217,"À régler avant le "+data["due_date"],9)
    seller=data["seller"];client=data["customer"]
    label(48,h-252,"ÉMETTEUR",10,True,"#7250ab")
    label(48,h-271,SELLER_DEFAULT["name"]+" | FORMA",10,True)
    label(48,h-288,str(seller["legal_form"])+"   |   SIRET "+str(seller["siret"]),8)
    label(48,h-305,seller.get("address",""),9)
    label(320,h-252,"CLIENT",10,True,"#7250ab")
    label(320,h-271,client.get("name",""),10,True)
    label(320,h-288,client.get("address",""),9)
    label(320,h-305,client.get("siret",""),8)
    if seller.get("vat_number"):label(48,h-323,"TVA : "+seller["vat_number"],8)
    if seller.get("capital"):label(320,h-323,"Capital social : "+seller["capital"],8)
    p.setFillColor(colors.HexColor("#efebf4"));p.roundRect(45,h-382,w-90,35,6,fill=1,stroke=0)
    label(56,h-370,"PRESTATION",9,True)
    label(w-135,h-370,"MONTANT HT",9,True)
    y=h-407
    for item in data["items"]:
        if y<190:
            p.showPage();y=h-55
        label(56,y,item["label"],9)
        label(w-130,y,format(float(item["subtotal_eur"]),".2f")+" EUR",9)
        y-=25
    y-=10
    p.setStrokeColor(colors.HexColor("#b7a8ce"));p.line(50,y,w-50,y)
    label(w-246,y-22,"Total HT",10,True);label(w-132,y-22,data["subtotal_eur"]+" EUR",10,True)
    label(w-246,y-43,"TVA",9);label(w-132,y-43,data["vat_eur"]+" EUR",9)
    p.setFillColor(colors.HexColor("#271b40"));p.roundRect(w-264,y-93,220,33,7,fill=1,stroke=0)
    label(w-253,y-82,"TOTAL",10,True,"#ffffff")
    label(w-134,y-82,data["total_eur"]+" EUR",11,True,"#ffffff")
    foot=max(65,y-126)
    if data["vat_mode"]=="franchise":
        label(48,foot,"TVA non applicable, art. 293 B du CGI.",9)
        foot-=16
    label(48,foot,"Modalités de paiement : "+str(seller.get("payment_details",""))[:72],8)
    foot-=16
    label(48,foot,"Escompte pour paiement anticipé : néant.",8)
    foot-=16
    if client.get("type")=="business":
        label(48,foot,"Pénalités de retard : "+str(seller.get("late_penalty_rate",""))[:50]+".",8)
        foot-=16
        label(48,foot,"Indemnité forfaitaire de recouvrement (professionnels) : 40 EUR.",8)
    p.setFillColor(colors.HexColor("#9177b5"));p.rect(0,0,w,36,fill=1,stroke=0)
    p.setFillColor(colors.white);p.setFont("Helvetica",8)
    p.drawString(48,14,"FORMA  |  Création web sur mesure  |  Document à conserver")
    p.save()
    return out.getvalue()
