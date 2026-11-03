"""Reconcile a provider-signed proposal and a voluntary Stripe Checkout payment."""
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from local_app import web_crm as crm


# Keep commercial credentials out of Codex, npm builds, preview checks and
# other child processes. Only the local HTTP server owns this configuration.
_private_config = {}
_SECRET_NAMES = ("LOCALAI_SALES_APPROVAL_CODE","LOCALAI_REGISTRAR_TOKEN","LOCALAI_REGISTRAR_MANDATES",
    "LOCALAI_VERCEL_READ_TOKEN","DROPBOX_SIGN_API_KEY","STRIPE_SECRET_KEY","STRIPE_WEBHOOK_SECRET")


def isolate_config():
    for name in _SECRET_NAMES:
        if name in os.environ:
            _private_config[name] = os.environ.pop(name)


def setting(name):
    return _private_config.get(name,os.getenv(name,""))


def _db(root):
    Path(root).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(Path(root)/"sales-orders.sqlite", timeout=15)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS orders(
          quote TEXT PRIMARY KEY, project TEXT NOT NULL, amount INTEGER NOT NULL,
          signature TEXT UNIQUE NOT NULL, mode TEXT NOT NULL, accepted REAL NOT NULL,
          session TEXT UNIQUE, checkout TEXT, requested REAL, intent TEXT UNIQUE,
          payment TEXT NOT NULL DEFAULT 'unpaid', refunded INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS requests(quote TEXT PRIMARY KEY, project TEXT NOT NULL,
          mode TEXT NOT NULL, reference TEXT, requested REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, quote TEXT NOT NULL,
          type TEXT NOT NULL, at REAL NOT NULL);
    """)
    return con


def _mode():
    return "live" if os.getenv("LOCALAI_SALES_MODE") == "live" else "test"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirection du prestataire refusée.")


def _request(request):
    with build_opener(_NoRedirect()).open(request, timeout=20) as response:
        return json.load(response)


def _quote(root, project, number):
    with crm._LOCK:
        row = next((q for q in reversed(crm._read(root)["quotes"])
                    if q["project_id"] == project and q["quote_number"] == number), None)
    if not row:
        raise ValueError("Devis absent de ce projet.")
    return row


def status(root, project):
    Path(root).mkdir(parents=True,exist_ok=True)
    with closing(_db(root)) as db:
        return [dict(row) for row in db.execute(
            "SELECT quote,mode,accepted,payment,amount,refunded,checkout FROM orders WHERE project=? AND mode=?",
            (project,_mode()))]


def signature_request(root, project, number):
    import uuid
    from datetime import date
    q = _quote(root,project,number)
    email = q["customer"].get("email","")
    key = setting("DROPBOX_SIGN_API_KEY")
    if not key or not email or q["valid_until"] < date.today().isoformat():
        raise ValueError("Clé Dropbox Sign, courriel client et devis valide requis.")
    pdf = crm.quote_file(root,number).read_bytes()
    mode = _mode()
    with closing(_db(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT * FROM requests WHERE quote=?", (number,)).fetchone()
        if previous:
            if previous["reference"] and previous["mode"]==mode:
                return previous["reference"]
            raise ValueError("Demande déjà réservée. Vérifier le fournisseur avant toute reprise.")
        db.execute("INSERT INTO requests VALUES(?,?,?,NULL,?)",(number,project,mode,time.time()))
    boundary = uuid.uuid4().hex
    fields = {"title":"Devis "+number, "signers[0][email_address]":email,
              "signers[0][name]":q["customer"]["name"], "test_mode":"1" if mode=="test" else "0",
              "metadata[sales_mode]":mode,"metadata[quote_number]":number,"metadata[quote_sha256]":hashlib.sha256(pdf).hexdigest()}
    parts = []
    for field,value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="{number}.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode())
    parts.extend([pdf,f'\r\n--{boundary}--\r\n'.encode()])
    result = _request(Request("https://api.hellosign.com/v3/signature_request/send",data=b"".join(parts),
        headers={"Authorization":"Basic "+base64.b64encode((key+":").encode()).decode(),
                 "Content-Type":"multipart/form-data; boundary="+boundary}))
    reference=result["signature_request"]["signature_request_id"]
    if not re.fullmatch(r"[a-zA-Z0-9]{16,100}",reference):
        raise ValueError("Référence inconnue. Réconcilier chez Dropbox Sign.")
    with closing(_db(root)) as db, db:
        db.execute("UPDATE requests SET reference=? WHERE quote=?",(reference,number))
    return reference


def verify_acceptance(root, project, number, recovery=None):
    quote = _quote(root,project,number)
    with closing(_db(root)) as db:
        sent=db.execute("SELECT * FROM requests WHERE quote=? AND project=? AND mode=?",(number,project,_mode())).fetchone()
    if not sent:
        raise ValueError("Aucune demande de signature réservée pour ce devis.")
    reference=sent["reference"] or recovery
    if not re.fullmatch(r"[a-zA-Z0-9]{16,100}", str(reference or "")):
        raise ValueError("Identifiant Dropbox Sign invalide.")
    key = setting("DROPBOX_SIGN_API_KEY")
    if not key:
        raise ValueError("Configurer DROPBOX_SIGN_API_KEY sur le serveur pour vérifier l’accord.")
    digest = hashlib.sha256(crm.quote_file(root,number).read_bytes()).hexdigest()
    auth = base64.b64encode((key+":").encode()).decode()
    data = _request(Request("https://api.hellosign.com/v3/signature_request/"+reference,
                            headers={"Authorization":"Basic "+auth}))["signature_request"]
    meta = data.get("metadata") or {}
    email = (quote["customer"].get("email") or "").casefold()
    signers = data.get("signatures") or []
    from datetime import datetime, timezone
    until = quote["valid_until"]
    def client_signed(s):
        if s.get("status_code") != "signed" or not email or str(s.get("signer_email_address")).casefold()!=email:
            return False
        stamp = datetime.fromtimestamp(int(s.get("signed_at") or 0),timezone.utc).date().isoformat()
        return quote["issued_at"] <= stamp <= until
    if (data.get("signature_request_id") != reference or data.get("is_complete") is not True
        or data.get("has_error") or data.get("is_declined")
        or meta.get("sales_mode") != _mode() or meta.get("quote_number") != number or meta.get("quote_sha256") != digest
        or not any(client_signed(s) for s in signers)):
        raise ValueError("Accord non vérifié : contrôler PDF, signataire, dates et environnement.")
    with closing(_db(root)) as db, db:
        db.execute("UPDATE requests SET reference=? WHERE quote=? AND reference IS NULL",(reference,number))
        db.execute("INSERT OR IGNORE INTO orders(quote,project,amount,signature,mode,accepted) VALUES(?,?,?,?,?,?)",
                   (number,project,int(Decimal(quote["total_eur"])*100),reference,_mode(),time.time()))
        row=db.execute("SELECT * FROM orders WHERE quote=? AND project=?", (number,project)).fetchone()
        if not row or row["signature"]!=reference or row["mode"]!=_mode():
            raise ValueError("Ce devis ou cet accord est déjà associé à une autre opération.")
    return status(root,project)


def checkout(root, project, number, recovery=None):
    mode = _mode()
    key = setting("STRIPE_SECRET_KEY")
    redirect = os.getenv("LOCALAI_CHECKOUT_RETURN_URL","")
    if not key.startswith("sk_"+mode+"_") or not setting("STRIPE_WEBHOOK_SECRET") or urlsplit(redirect).scheme!="https" or not urlsplit(redirect).hostname:
        raise ValueError("Configurer Stripe, son secret webhook et l’URL HTTPS de retour dans le même environnement.")
    with closing(_db(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT * FROM orders WHERE project=? AND quote=? AND mode=?",(project,number,mode)).fetchone()
        if not row:
            raise ValueError("Un accord vérifié pour ce devis est requis.")
        if row["session"]:
            return status(root,project)
        now=time.time()
        if not recovery and row["requested"] and now-row["requested"]>23*3600:
            raise ValueError("Demande ancienne à rapprocher dans Stripe avant toute nouvelle tentative.")
        db.execute("UPDATE orders SET requested=COALESCE(requested,?) WHERE quote=?",(now,number))
    fields={"mode":"payment","success_url":redirect,"cancel_url":redirect,"client_reference_id":number,
            "metadata[quote]":number,"payment_intent_data[metadata][quote]":number,
            "line_items[0][quantity]":1,"line_items[0][price_data][currency]":"eur",
            "line_items[0][price_data][unit_amount]":row["amount"],
            "line_items[0][price_data][product_data][name]":"Règlement du devis "+number}
    if recovery:
        if not re.fullmatch(r"cs_(?:live|test)_[A-Za-z0-9]{6,220}",str(recovery)):
            raise ValueError("Référence de session invalide.")
        data=_request(Request("https://api.stripe.com/v1/checkout/sessions/"+recovery,
                              headers={"Authorization":"Bearer "+key}))
    else:
        data=_request(Request("https://api.stripe.com/v1/checkout/sessions",data=urlencode(fields).encode(),
                              headers={"Authorization":"Bearer "+key,"Idempotency-Key":"localai-"+project+"-"+number}))
    url=str(data.get("url") or "")
    if (not data.get("id") or data.get("client_reference_id")!=number or (data.get("metadata") or {}).get("quote")!=number
        or (not url and not recovery) or (url and (urlsplit(url).scheme!="https" or urlsplit(url).hostname!="checkout.stripe.com"))
        or data.get("amount_total")!=row["amount"] or data.get("currency")!="eur" or data.get("livemode")!=(mode=="live")):
        raise ValueError("Session Stripe non confirmée.")
    with closing(_db(root)) as db, db:
        db.execute("UPDATE orders SET session=?,checkout=?,payment=CASE WHEN payment='unpaid' THEN 'pending' ELSE payment END WHERE quote=?",
                   (data["id"],url,number))
    return status(root,project)


def webhook(root, raw, header):
    secret=setting("STRIPE_WEBHOOK_SECRET")
    fields=[s.strip().partition("=") for s in header.split(",")]
    ts=next((v for k,_,v in fields if k=="t"),"")
    if not secret or not ts.isdigit() or abs(time.time()-int(ts))>300:
        raise ValueError("Signature Stripe invalide.")
    expected=hmac.new(secret.encode(),ts.encode()+b"."+raw,hashlib.sha256).hexdigest()
    if not any(k=="v1" and hmac.compare_digest(v,expected) for k,_,v in fields):
        raise ValueError("Signature Stripe invalide.")
    event=json.loads(raw)
    kind=event["type"]
    if kind not in ("checkout.session.completed","checkout.session.async_payment_succeeded",
                    "checkout.session.async_payment_failed","checkout.session.expired","charge.refunded"):
        return
    obj=event["data"]["object"]
    number=(obj.get("metadata") or {}).get("quote")
    if not number:
        return
    with closing(_db(root)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        row=db.execute("SELECT * FROM orders WHERE quote=?", (number,)).fetchone()
        if not row or event.get("livemode")!=(row["mode"]=="live"):
            return
        if db.execute("SELECT 1 FROM events WHERE id=?", (event["id"],)).fetchone():
            return
        if obj.get("currency")!="eur":
            raise ValueError("Devise incohérente.")
        if kind=="charge.refunded":
            if not row["intent"]:
                raise RuntimeError("Paiement à rapprocher avant remboursement.")
            if obj.get("payment_intent")!=row["intent"] or obj.get("amount")!=row["amount"]:
                raise ValueError("Remboursement non associé au paiement vérifié.")
            refund=max(row["refunded"],int(obj["amount_refunded"]))
            db.execute("UPDATE orders SET payment=?,refunded=? WHERE quote=?",
                       ("refunded" if refund==row["amount"] else "partially_refunded",refund,number))
        else:
            if not row["session"]:
                raise RuntimeError("Session à rapprocher. Réessayer le webhook.")
            if obj.get("id")!=row["session"] or obj.get("amount_total")!=row["amount"] or obj.get("client_reference_id")!=number:
                raise ValueError("Session ou montant incohérent.")
            if obj.get("payment_status")=="paid" and obj.get("payment_intent") and not row["refunded"]:
                db.execute("UPDATE orders SET payment='paid',intent=? WHERE quote=?", (obj["payment_intent"],number))
            elif kind.endswith(("failed","expired")) and row["payment"] in ("pending","unpaid"):
                db.execute("UPDATE orders SET payment='failed' WHERE quote=?",(number,))
        db.execute("INSERT INTO events VALUES(?,?,?,?)",(event["id"],number,kind,time.time()))
