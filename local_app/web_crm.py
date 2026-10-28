"""Private local customer/project/quote register for LocalAiWeb.

No payment gateway, automatic email outreach, public listener or fabricated
commercial identity. All mutations are local and explicit. Invoicing uses the
existing verified invoice service and is indexed here only AFTER issue().
"""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import json
import re
import threading
import uuid
import time

from local_app import web_sales_invoice as sales

_LOCK=threading.RLock()
STAGES=("prospect","contacted","proposal","accepted","in_progress","delivered","won","lost")
STAGE_LABELS={"prospect":"Prospect","contacted":"Contacté","proposal":"Devis préparé",
              "accepted":"Devis accepté","in_progress":"En production",
              "delivered":"Livré","won":"Client actif","lost":"Sans suite"}
CLIENT_ID=re.compile(r"^client-[a-f0-9]{12}$")
PROJECT_ID=re.compile(r"^web-[a-f0-9]{12}$")
QUOTE_ID=re.compile(r"^DEV-\d{4}-\d{5}$")


def _folder(root):
    path=Path(root).resolve()
    path.mkdir(parents=True,exist_ok=True)
    return path


def _read(root):
    path=_folder(root)/"register.json"
    if not path.exists():
        return {"version":1,"clients":[],"quotes":[],"invoices":[],"quote_sequence":{}}
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict) or not isinstance(data.get("clients"),list):
            raise ValueError("structure invalide")
        for key in ("quotes","invoices"):
            if not isinstance(data.get(key),list):
                raise ValueError("registre endommagé")
        data.setdefault("quote_sequence",{})
        return data
    except (OSError,ValueError,TypeError) as exc:
        raise RuntimeError("Le registre commercial est illisible : aucune donnée n'a été écrasée.") from exc


def _write(root,data):
    path=_folder(root)/"register.json"
    pending=path.with_name("register-"+uuid.uuid4().hex+".tmp")
    try:
        pending.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def _field(value,limit=180):
    value=str(value or "").strip()
    if len(value)>limit or any(ord(c)<32 for c in value):
        raise ValueError("Champ trop long ou contenant des caractères invalides.")
    return value


def _valid_project(store,project_id):
    if not PROJECT_ID.fullmatch(str(project_id or "")):
        raise ValueError("Projet associé invalide.")
    return store.meta(project_id)


def _client_by_project(data,project_id):
    return next((c for c in data["clients"] if project_id and project_id in c.get("project_ids",[])),None)


def _upsert(data,store,body,*,auto=False):
    if not isinstance(body,dict):
        raise ValueError("Fiche client invalide.")
    project_id=_field(body.get("project_id"),30)
    if project_id:_valid_project(store,project_id)
    requested=_field(body.get("id"),30)
    if requested and not CLIENT_ID.fullmatch(requested):
        raise ValueError("Identifiant client invalide.")
    existing=next((c for c in data["clients"] if c.get("id")==requested),None) if requested else (
        _client_by_project(data,project_id) if project_id else None)
    if requested and existing is None:
        raise ValueError("Fiche client inexistante.")
    if project_id:
        linked=_client_by_project(data,project_id)
        if linked and existing and linked.get("id")!=existing.get("id"):
            raise ValueError("Ce projet est déjà rattaché à une autre fiche client.")
    if not existing and len(data["clients"])>=10000:
        raise ValueError("Capacité du registre atteinte.")
    name=_field(body.get("name") or (existing or {}).get("name"),120)
    if len(name)<2:
        raise ValueError("Nom commercial ou raison sociale obligatoire.")
    stage=_field(body.get("stage") or (existing or {}).get("stage") or "prospect",25)
    if stage not in STAGES:
        raise ValueError("Étape commerciale inconnue.")
    email=_field(body.get("email", (existing or {}).get("email","")),150)
    if email and (not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email)):
        raise ValueError("Adresse électronique professionnelle invalide.")
    siret=_field(body.get("siret", (existing or {}).get("siret","")),20).replace(" ","")
    if siret and not re.fullmatch(r"\d{14}",siret):
        raise ValueError("SIRET client invalide (14 chiffres attendus).")
    due=_field(body.get("next_contact", (existing or {}).get("next_contact","")),12)
    if due:
        try:
            parsed=date.fromisoformat(due)
            if parsed.year<2000 or parsed.year>2100:
                raise ValueError()
        except (TypeError,ValueError):
            raise ValueError("Date de relance invalide (AAAA-MM-JJ).") from None
    if existing is None:
        existing={"id":"client-"+uuid.uuid4().hex[:12],"created_at":time.time(),"project_ids":[]}
        data["clients"].append(existing)
    existing.update({
        "name":name,"stage":stage,
        "email":email,"phone":_field(body.get("phone",(existing or {}).get("phone","")),35),
        "address":_field(body.get("address",(existing or {}).get("address","")),250),
        "siret":siret,
        "contact_name":_field(body.get("contact_name",(existing or {}).get("contact_name","")),120),
        "next_contact":due,
        "notes":_field(body.get("notes",(existing or {}).get("notes","")),1300),
        "updated_at":time.time()
    })
    if project_id and project_id not in existing["project_ids"]:
        existing["project_ids"].append(project_id)
    if auto:existing["source"]="OpenStreetMap · présence de site non confirmée"
    return existing


def upsert_client(root,store,body):
    with _LOCK:
        data=_read(root)
        result=_upsert(data,store,body)
        _write(root,data)
        return dict(result)


def attach_business_project(root,store,project_id,business):
    if not isinstance(business,dict) or not business.get("name"):
        return None
    with _LOCK:
        data=_read(root)
        profile=_upsert(data,store,{
            "project_id":project_id,
            "name":business.get("name"),
            "phone":business.get("phone") or "",
            "email":business.get("email") or "",
            "address":business.get("address") or "",
            "stage":"prospect"
        },auto=True)
        _write(root,data)
        return dict(profile)


def snapshot(root,store):
    with _LOCK:
        data=_read(root)
    projects=store.list_projects()
    by_id={x["id"]:x for x in projects}
    clients=[]
    for item in data["clients"]:
        record=dict(item)
        record["projects"]=[{"id":p,"name":by_id[p].get("name","Site"),
                             "status":by_id[p].get("status","local"),
                             "production_url":(by_id[p].get("deployment") or {}).get("production_url","")}
                            for p in item.get("project_ids",[]) if p in by_id]
        clients.append(record)
    assigned={p for c in clients for p in c.get("project_ids",[])}
    unlinked=[{"id":p["id"],"name":p.get("name","Sans nom"),
               "business":p.get("business",{})}
              for p in projects if p.get("project_kind")=="pro" and p["id"] not in assigned]
    stages={stage:sum(c["stage"]==stage for c in clients) for stage in STAGES}
    today=date.today().isoformat()
    followups=sorted(
        ({"id":c["id"],"name":c["name"],"due":c["next_contact"],"stage":c["stage"]}
         for c in clients if c.get("next_contact") and c["next_contact"]<=today
         and c.get("stage") not in ("lost","won")),
        key=lambda c:(c["due"],c["name"].casefold()))
    upcoming=sorted(
        ({"id":c["id"],"name":c["name"],"due":c["next_contact"],"stage":c["stage"]}
         for c in clients if c.get("next_contact") and c["next_contact"]>today
         and c.get("stage") not in ("lost","won")),
        key=lambda c:(c["due"],c["name"].casefold()))
    # Older PDF invoices are never deleted/migrated blindly. Read their
    # original metadata and present them as historical commercial records.
    # A prior invoice has no CRM client_id until explicitly linked.
    invoices=list(data["invoices"])
    seen={row.get("invoice_number") for row in invoices}
    archive=Path(root).resolve().parent/"invoices"
    if archive.is_dir():
        for path in sorted(archive.glob("FORMA-????-?????.json"))[:5000]:
            if path.stem in seen or path.stat().st_size>300_000:
                continue
            try:
                old=json.loads(path.read_text(encoding="utf-8"))
                if old.get("invoice_number")!=path.stem:
                    continue
                invoices.append({
                    "invoice_number":path.stem,
                    "project_id":old.get("project_id",""),
                    "client_id":_client_by_project(data,old.get("project_id","")).get("id") if _client_by_project(data,old.get("project_id","")) else "",
                    "total_eur":old.get("total_eur","0"),
                    "issue_date":old.get("issue_date",""),
                    "due_date":old.get("due_date",""),
                    "status":old.get("status","issued_unpaid"),
                    "download":"/api/web/invoice/file?number="+path.stem
                })
                seen.add(path.stem)
            except (OSError,ValueError,TypeError,AttributeError):
                continue
    return {"clients":sorted(clients,key=lambda x:x.get("updated_at",0),reverse=True),
            "unlinked_pro_projects":unlinked,
            "quotes":list(reversed(data["quotes"])),
            "invoices":sorted(invoices,key=lambda x:x.get("issue_date",""),reverse=True),
            "stages":stages,"projects_count":len(projects),
            "followups_due":followups,"followups_upcoming":upcoming[:15],
            "stage_labels":STAGE_LABELS,
            "notice":"Registre local privé. Coordonnées professionnelles à vérifier. Aucun message commercial envoyé automatiquement."}


def create_quote(root,store,request):
    """Issue a clearly labelled commercial quotation, NOT a tax invoice."""
    if not isinstance(request,dict) or request.get("confirmed") is not True:
        raise ValueError("Validation explicite du devis requise.")
    project_id=str(request.get("project_id") or "")
    _valid_project(store,project_id)
    parties=sales.validate_parties(request.get("seller"),request.get("customer"))
    available={row["id"]:row for row in sales.estimate(store,project_id)["items"]}
    ids=list(dict.fromkeys(request.get("items") or []))
    if not ids or any(x not in available for x in ids):
        raise ValueError("Sélectionne des prestations réellement identifiées dans le projet.")
    try:days=int(request.get("valid_days",30))
    except (TypeError,ValueError):raise ValueError("Durée de validité incorrecte.") from None
    if not 1<=days<=90:raise ValueError("Validité du devis : de 1 à 90 jours.")
    lines=[available[k] for k in ids]
    subtotal=sum((sales.money(x["subtotal_eur"]) for x in lines),Decimal(0))
    vat=sales.money(subtotal*Decimal(".20")) if parties["vat_mode"]=="standard" else Decimal(0)
    total=sales.money(subtotal+vat)
    with _LOCK:
        data=_read(root)
        existing=_client_by_project(data,project_id)
        customer=parties["customer"]
        customer_name=_field(customer.get("name"),120)
        if existing:
            client=_upsert(data,store,{"id":existing["id"],
                "name":customer_name,"project_id":project_id,
                "address":customer.get("address"),"email":customer.get("email"),
                "siret":customer.get("siret"),"stage":"proposal"})
        else:
            client=_upsert(data,store,{"name":customer_name,"project_id":project_id,
                "address":customer.get("address"),"email":customer.get("email"),
                "siret":customer.get("siret"),"stage":"proposal"})
        today=date.today()
        count=int(data["quote_sequence"].get(str(today.year),0))+1
        number=f"DEV-{today.year}-{count:05d}"
        record={"quote_number":number,"project_id":project_id,"client_id":client["id"],
                "project_name":store.meta(project_id).get("name",""),
                "issued_at":today.isoformat(),"valid_until":(today+timedelta(days=days)).isoformat(),
                "seller":parties["seller"],"customer":parties["customer"],"items":lines,
                "subtotal_eur":str(sales.money(subtotal)),"vat_eur":str(vat),
                "total_eur":str(total),"vat_mode":parties["vat_mode"],
                "currency":"EUR","status":"issued_proposal",
                "notice":"Devis préparé, ni envoyé ni accepté automatiquement. Aucun paiement ni publication automatique."}
        pdf=quote_pdf(record)
        folder=_folder(root)/"quotes";folder.mkdir(exist_ok=True)
        path=folder/(number+".pdf")
        if path.exists():raise RuntimeError("Un devis porte déjà ce numéro.")
        path.write_bytes(pdf)
        data["quotes"].append(record)
        data["quote_sequence"][str(today.year)]=count
        _write(root,data)
    return {"ok":True,"quote_number":number,"total_eur":str(total),
            "download":"/api/web/crm/quote/file?number="+number,
            "client_id":client["id"],"status":"issued_proposal"}


def quote_file(root,number):
    if not QUOTE_ID.fullmatch(str(number or "")):
        raise ValueError("Numéro de devis invalide.")
    path=_folder(root)/"quotes"/(number+".pdf")
    if not path.is_file():
        raise FileNotFoundError("Devis introuvable.")
    return path


def register_invoice(root,store,result):
    """Index a real invoice after issue succeeded; never issue two invoices."""
    record=result.get("data") or {}
    project_id=record.get("project_id")
    customer=record.get("customer") or {}
    if not project_id or not record.get("invoice_number"):
        raise ValueError("Facture à associer invalide.")
    with _LOCK:
        data=_read(root)
        if any(x.get("invoice_number")==record["invoice_number"] for x in data["invoices"]):
            return
        client=_upsert(data,store,{"project_id":project_id,
            "name":customer.get("name"),"email":customer.get("email"),
            "address":customer.get("address"),"siret":customer.get("siret"),
            "stage":"delivered"})
        data["invoices"].append({
            "invoice_number":record["invoice_number"],"client_id":client["id"],
            "project_id":project_id,"total_eur":record.get("total_eur"),
            "issue_date":record.get("issue_date"),"due_date":record.get("due_date"),
            "status":record.get("status","issued_unpaid"),
            "download":result.get("download","")
        })
        _write(root,data)


def quote_pdf(data):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    out=BytesIO()
    pdf=canvas.Canvas(out,pagesize=A4)
    pdf.setTitle("LocalAiWeb | Devis "+data["quote_number"])
    w,h=A4
    def show(x,y,value,size=10,bold=False,color="#23172f"):
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica",size)
        pdf.setFillColor(colors.HexColor(color))
        safe=str(value or "").encode("latin-1","replace").decode("latin-1")
        pdf.drawString(x,y,safe[:92])
    pdf.setFillColor(colors.HexColor("#28163e"));pdf.rect(0,h-124,w,124,fill=1,stroke=0)
    show(48,h-67,"LOCALAIWEB  /  PRO",25,True,"#ffffff")
    show(48,h-96,"DEVIS - Proposition commerciale",11,False,"#e2cbff")
    show(48,h-162,"DEVIS "+data["quote_number"],16,True)
    show(48,h-184,"Date : "+data["issued_at"]+"   |   Valable jusqu'au : "+data["valid_until"],10)
    seller=data["seller"];customer=data["customer"]
    show(48,h-224,"PRESTATAIRE",10,True,"#7240b3")
    show(48,h-244,seller["name"],11,True)
    show(48,h-261,"SIRET : "+seller["siret"]+"  /  "+seller["legal_form"],9)
    show(48,h-278,seller.get("address",""),9)
    show(310,h-224,"DESTINATAIRE",10,True,"#7240b3")
    show(310,h-244,customer.get("name",""),11,True)
    show(310,h-261,customer.get("address",""),9)
    show(310,h-278,"SIRET : "+customer.get("siret",""),9)
    y=h-330
    show(48,y,"PRESTATIONS",10,True)
    show(w-150,y,"MONTANT HT",10,True)
    y-=26
    for row in data["items"]:
        if y<200:
            pdf.showPage();y=h-60
        show(48,y,row["label"],9)
        show(w-144,y,str(row["subtotal_eur"])+" EUR",9)
        y-=23
    pdf.setStrokeColor(colors.HexColor("#bbacd0"));pdf.line(47,y,w-45,y)
    y-=28
    show(315,y,"Sous-total HT",10,True)
    show(w-142,y,data["subtotal_eur"]+" EUR",10,True)
    y-=22
    show(315,y,"TVA",10)
    show(w-142,y,data["vat_eur"]+" EUR",10)
    y-=28
    show(315,y,"TOTAL TTC",12,True,"#6630aa")
    show(w-142,y,data["total_eur"]+" EUR",11,True,"#6630aa")
    y-=34
    if data["vat_mode"]=="franchise":
        show(48,y,"TVA non applicable, article 293 B du CGI.",9);y-=18
    show(48,y,"Modalites de paiement : "+seller.get("payment_details",""),9);y-=18
    if customer.get("type")=="business":
        show(48,y,"Penalites de retard : "+seller.get("late_penalty_rate",""),9);y-=18
    show(48,y,"Devis non accepte ; accord ecrit du client requis avant engagement.",9);y-=18
    show(48,y,"Projet concerne : "+data["project_name"],9)
    pdf.setFillColor(colors.HexColor("#58318b"));pdf.rect(0,0,w,38,fill=1,stroke=0)
    show(48,14,"LocalAiWeb Pro  |  Aucun paiement ou envoi automatique",8,color="#ffffff")
    pdf.save()
    return out.getvalue()
