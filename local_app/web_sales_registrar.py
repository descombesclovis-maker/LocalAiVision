"""Exact-cost, single-attempt domain registration against a separately supplied mandate."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import quote, urlencode
from urllib.request import Request
from local_app import web_sales_orders as orders
from local_app.web_sales_pipeline import registrar_search


def _mandate(store, pid, number):
    folder = orders.setting("LOCALAI_REGISTRAR_MANDATES")
    if not folder or orders._mode() != "live":
        raise ValueError("Achat désactivé. Mandat financier local et mode réel requis.")
    area = Path(folder).resolve()
    if area.is_relative_to(store.root.resolve()):
        raise ValueError("Les mandats doivent être conservés hors des projets.")
    project = store.meta(pid)
    if project.get("project_kind") != "pro":
        raise ValueError("Un projet client Pro est requis.")
    file = area/(pid+".json")
    if not file.is_file() or file.stat().st_size>16000:
        raise ValueError("Mandat financier absent.")
    mandate = json.loads(file.read_text(encoding="utf-8"))
    if (mandate.get("quote")!=number or mandate.get("project")!=pid
        or not time.time()<float(mandate.get("expires_at",0))<=time.time()+86400
        or mandate.get("holder_consented") is not True or mandate.get("autoRenew") is not False):
        raise ValueError("Mandat expiré ou incomplet.")
    # Only accounts with confirmed zero additional tax/fees are supported: the
    # documented registrar expectedPrice caps the registration price, not tax.
    price = mandate.get("price_usd")
    if (not isinstance(price,(float,int)) or not 0<price<=100000
        or price!=mandate.get("all_in_usd") or mandate.get("billing_verified") is not True
        or not mandate.get("billing_evidence")):
        raise ValueError("Coût final exact non vérifié. Achat bloqué.")
    contact = mandate.get("contactInformation",{})
    if not isinstance(contact,dict) or not all(isinstance(contact.get(k),str) and contact[k].strip()
        for k in ("firstName","lastName","email","phone","address1","city","state","zip","country")):
        raise ValueError("Coordonnées du titulaire client incomplètes.")
    domain = mandate.get("domain","")
    if not re.fullmatch(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",domain):
        raise ValueError("Nom de domaine du mandat invalide.")
    target = store.project_dir(pid)/"site"/".vercel"/"project.json"
    if not target.is_file():
        raise ValueError("Associer le projet au compte Vercel du client au préalable.")
    link=json.loads(target.read_text(encoding="utf-8"))
    if (not mandate.get("teamId") or not mandate.get("projectId") or link.get("orgId")!=mandate["teamId"]
        or link.get("projectId")!=mandate["projectId"]):
        raise ValueError("Projet ou organisation différents du mandat.")
    return mandate


def _db(root):
    db=orders._db(root)
    db.execute("""CREATE TABLE IF NOT EXISTS domains(
        domain TEXT PRIMARY KEY, project TEXT UNIQUE NOT NULL, quote TEXT NOT NULL,
        team TEXT NOT NULL, project_ref TEXT NOT NULL, price REAL NOT NULL,
        renewal REAL NOT NULL, years INTEGER NOT NULL, mandate_digest TEXT NOT NULL,
        order_id TEXT UNIQUE, state TEXT NOT NULL, reserved REAL NOT NULL)""")
    return db


def _provider(m, path, body=None):
    token=orders.setting("LOCALAI_REGISTRAR_TOKEN")
    if not token:
        raise ValueError("Configurer un jeton Vercel dédié au registrar.")
    return orders._request(Request("https://api.vercel.com/v1/registrar/"+path+"?"+urlencode({"teamId":m["teamId"]}),
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}))


def prepare(root, store, pid, number):
    m=_mandate(store,pid,number)
    q=orders._quote(root,pid,number)
    if m.get("customer_name")!=q["customer"]["name"]:
        raise ValueError("Le bénéficiaire du mandat doit correspondre au client du devis.")
    if str(m["contactInformation"]["email"]).casefold()!=str(q["customer"].get("email","")).casefold():
        raise ValueError("Le titulaire ne correspond pas au client signataire.")
    with closing(_db(root)) as db:
        paid=db.execute("SELECT 1 FROM orders WHERE quote=? AND project=? AND mode='live' AND payment='paid' AND refunded=0",
                        (number,pid)).fetchone()
    if not paid:
        raise ValueError("Accord et règlement réel du devis requis.")
    actual=registrar_search(m["domain"])
    if not actual["available"] or not all(isinstance(actual[k],(int,float)) for k in ("price","renewal","years")):
        raise ValueError("Disponibilité ou tarif numérique non confirmé.")
    if (actual["price"]!=m["price_usd"] or actual["renewal"]!=m.get("renewal_usd")
        or actual["years"]!=m.get("years") or not actual["years"]>0):
        raise ValueError("Tarif ou durée modifiés. Un nouveau mandat est nécessaire.")
    digest=hashlib.sha256(json.dumps(m,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {"domain":m["domain"],"total":m["all_in_usd"],"renewal":actual["renewal"],
            "years":actual["years"],"team":m["teamId"],"holder":q["customer"]["name"],
            "autoRenew":False,"approval":digest},m


def buy(root, store, pid, number, approval):
    offer,m=prepare(root,store,pid,number)
    if not approval or approval!=offer["approval"]:
        raise ValueError("Confirmer la proposition exacte juste avant l’achat.")
    if not orders.setting("LOCALAI_REGISTRAR_TOKEN"):
        raise ValueError("Jeton du registrar absent.")
    with closing(_db(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM domains WHERE domain=? OR project=?", (offer["domain"],pid)).fetchone():
            raise ValueError("Commande existante ou incertaine. Vérifier son statut sans répéter l’achat.")
        if not db.execute("SELECT 1 FROM orders WHERE quote=? AND payment='paid' AND refunded=0",(number,)).fetchone():
            raise ValueError("Paiement non confirmé.")
        db.execute("INSERT INTO domains VALUES(?,?,?,?,?,?,?,?,?,NULL,'uncertain',?)",
                   (offer["domain"],pid,number,m["teamId"],m["projectId"],offer["total"],offer["renewal"],
                    offer["years"],approval,time.time()))
    result=_provider(m,"domains/"+quote(m["domain"],safe="")+"/buy",
          {"years":offer["years"],"expectedPrice":offer["total"],"autoRenew":False,
           "contactInformation":m["contactInformation"]})
    order_id=result.get("orderId")
    if not isinstance(order_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,150}",order_id):
        raise ValueError("Commande incertaine. Rapprochement manuel chez Vercel requis.")
    with closing(_db(root)) as db,db:
        db.execute("UPDATE domains SET order_id=?,state='pending' WHERE project=?",(order_id,pid))
    return details(root,pid)


def details(root,pid,refresh=False,recovery=None):
    with closing(_db(root)) as db, db:
        row=db.execute("SELECT domain,team,order_id,state,price,renewal,years FROM domains WHERE project=?",(pid,)).fetchone()
        if not row:return None
        result=dict(row)
        reference=row["order_id"] or recovery
        if refresh and reference:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,150}",str(reference)):
                raise ValueError("Référence de commande invalide.")
            response=_provider({"teamId":row["team"]},"orders/"+reference)
            line=next((d for d in response.get("domains",[]) if d.get("domainName")==row["domain"] and d.get("purchaseType")=="purchase"),{})
            state=line.get("status")
            if response.get("orderId")!=reference or line.get("price")!=row["price"] or line.get("years")!=row["years"] or state not in ("pending","completed","failed","refunded","refund-failed"):
                raise ValueError("Le registrar ne confirme pas cette commande.")
            result["state"]=state
            result["order_id"]=reference
            db.execute("UPDATE domains SET state=?,order_id=? WHERE project=?",(state,reference,pid))
        return result
