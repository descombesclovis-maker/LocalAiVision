"""Local delivery dossiers. No outreach, provisioning, transfer, or transactions.

SQLite commits numbered immutable PDFs and their snapshots together. Project
sources are read only. Credentials and database rows never enter standard ZIPs.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
import sqlite3
import time
import zipfile
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit, quote
from local_app.business_time import business_date
from local_app import web_builder, web_sales_invoice

LEGAL_URL = 'https://entreprendre.service-public.gouv.fr/vosdroits/F31808'
EINVOICE_URL = 'https://www.impots.gouv.fr/facturation-electronique-et-plateformes-agreees'
LEGAL_NOTICE = "PDF local gratuit. Pour une opération soumise à la facturation électronique, transmettre via une plateforme agréée ; ce PDF seul ne remplace pas ce circuit. Vérifier le régime applicable avec votre comptable. Références vérifiées le 05/11/2026."
TEXT_EXT = {'.html','.htm','.css','.js','.mjs','.cjs','.ts','.tsx','.jsx','.json','.md','.txt','.svg','.toml','.sql','.yml','.yaml','.vue','.svelte','.py','.example','.lock','.gltf','.scss','.sass','.less','.graphql','.mdx','.xml'}
MEDIA_EXT = {'.png','.jpg','.jpeg','.webp','.gif','.avif','.ico','.woff','.woff2','.ttf','.otf','.mp4','.webm','.ogg','.mp3','.glb','.bin','.hdr','.exr','.wasm','.usdz'}
IGNORED = web_builder.IGNORED_DIRS | {'.ssh','.aws','.supabase','.temp','.cache','coverage','.idea','.vscode'}
SECRETS = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:sk_(?:live|test)_[A-Za-z0-9]{8,}|sb_secret_[\w-]{8,}|sbp_[a-f0-9]{20,}|gh[pousr]_[\w]{20,}|eyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}|AKIA[A-Z0-9]{16})|(?:postgres(?:ql)?|mysql)://[^\s]+|https?://[^\s/@]+:[^\s/@]+@', re.I)
ASSIGNMENT = re.compile(r'''["']?([\w.-]*(?:secret|password|passwd|private_key|api_key|access_token|service_role|authorization)[\w.-]*)["']?\s*[:=]\s*["']([^"'\n]{6,})["']''', re.I)
PARTY_FIELDS = {'name','address','siret','siren','vat_number','legal_form','capital','vat_mode','payment_details','late_penalty_rate','type','email','registration','order_number','vat_on_debits','company_size'}
SERVICE_FIELDS = {'hosting':{'provider','domain','url','project','costs','renewal_owner','instructions'},'vercel':{'project_id','team_id','domain','build_command','output_directory','instructions'},'supabase':{'project_ref','auth','storage','security','instructions'},'payment':{'provider','mode','client_account','functions','webhooks','instructions'}}


def text(value, limit=2500):
    value=str(value or '').strip()
    if len(value)>limit or any(ord(c)<32 and c not in '\n\t' for c in value):
        raise ValueError('Champ trop long ou caractères invalides.')
    return value


def secret_in(value):
    value=value.replace('\\"','"')
    if SECRETS.search(value):return True
    for match in ASSIGNMENT.finditer(value):
        v=match[2].lower()
        if not any(x in v for x in ('example','placeholder','your_','votre_','replace','changeme','process.env','os.getenv','<','${')):
            return True
    return False


def money(value):
    try:
        n=Decimal(str(value))
        if not n.is_finite() or n<0 or n>Decimal('10000000'):raise ValueError()
        return n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,ValueError,TypeError):
        raise ValueError('Montant positif attendu, en euros.') from None


@contextmanager
def database(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(root/'deliveries.sqlite',timeout=30)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript('''CREATE TABLE IF NOT EXISTS dossiers(pid TEXT PRIMARY KEY, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sequences(kind TEXT, year INTEGER, n INTEGER, PRIMARY KEY(kind,year));
    CREATE TABLE IF NOT EXISTS documents(number TEXT PRIMARY KEY, pid TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, pdf BLOB NOT NULL);
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, pid TEXT NOT NULL, quote TEXT NOT NULL, amount TEXT NOT NULL, source TEXT NOT NULL, reference TEXT NOT NULL, mode TEXT NOT NULL, at TEXT NOT NULL, UNIQUE(source,reference));
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, pid TEXT NOT NULL, data TEXT NOT NULL, at REAL NOT NULL);''')
    try:
        con.execute('BEGIN IMMEDIATE')
        yield con
        con.commit()
    except BaseException:
        con.rollback();raise
    finally:con.close()


def initial(store,pid):
    meta=store.meta(pid)
    business=meta.get('business') or {}
    services=public_configuration(store,pid,meta)
    return {'id':pid,'name':meta.get('name','Site'),'created_at':time.time(),'version':0,
        'seller':{},'customer':{'name':business.get('name',''),'address':business.get('address',''),'type':'business'},
        'items':[{'label':'Création du site '+meta.get('name',''),'quantity':'1','unit_eur':'0.00','vat_rate':'20'}],
        'scope':'Création et livraison du site. Prestations à préciser.','maintenance':'',
        'service_date':'','due_days':30,'valid_days':30,'require_payment':True,
        'services':services,'checks':{},'quote':None,'accepted_quote':None,'invoice':None,'credit':None,'delivered':None}


def public_configuration(store,pid,meta):
    """Prefill only public identifiers. Credentials and remote data are never read."""
    site=store.project_dir(pid)/'site';deploy=meta.get('deployment') or {};result={}
    config=site/'.vercel'/'project.json';linked={}
    if config.is_file() and config.resolve().is_relative_to(site.resolve()) and config.stat().st_size<100000:
        try:linked=json.loads(config.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
    project=str(linked.get('projectId') or '')
    if re.fullmatch(r'prj_[A-Za-z0-9_-]+',project):
        team=str(linked.get('orgId') or '')
        result['vercel']={'enabled':True,'reviewed':False,'project_id':project,
            'team_id':team if re.fullmatch(r'(?:team_|user_)[A-Za-z0-9_-]+',team) else '',
            'instructions':'Vérifier les commandes dans package.json et vercel.json. Reconfigurer les variables dans le compte client. Préparer un transfert officiel soumis à validation.'}
    url=str(deploy.get('production_url') or '')
    parsed=urlsplit(url)
    if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment:
        result['hosting']={'enabled':True,'reviewed':False,'provider':'Vercel' if project else '',
            'url':url,'domain':text(deploy.get('custom_domain') or parsed.hostname),'project':project,
            'instructions':'Vérifier le domaine, les coûts, le responsable du renouvellement et la propriété du compte client.'}
    reference=str(deploy.get('supabase_ref') or '')
    if re.fullmatch(r'[a-z0-9]{20}',reference):
        result['supabase']={'enabled':True,'reviewed':False,'project_ref':reference,
            'instructions':'Examiner les migrations et fonctions du dossier supabase. Reconfigurer Auth, Storage et les politiques RLS dans le projet client. Aucun export de données réelles.'}
    return result


def read(db,store,pid):
    store.meta(pid)
    row=db.execute('SELECT data FROM dossiers WHERE pid=?',(pid,)).fetchone()
    return json.loads(row[0]) if row else initial(store,pid)


def write(db,d,action):
    d['version']+=1
    db.execute('INSERT OR REPLACE INTO dossiers VALUES(?,?)',(d['id'],json.dumps(d,ensure_ascii=False)))
    db.execute('INSERT INTO events(pid,data,at) VALUES(?,?,?)',(d['id'],json.dumps({'action':action,'version':d['version']}),time.time()))


def lines(items,vat_mode):
    if not isinstance(items,list) or not 1<=len(items)<=100:raise ValueError('Prévoir de 1 à 100 prestations.')
    result=[]
    for item in items:
        label=text(item.get('label'),600)
        quantity=money(item.get('quantity',1));unit=money(item.get('unit_eur',0))
        rate=money(item.get('vat_rate',20)) if vat_mode=='standard' else Decimal(0)
        if not label or quantity<=0 or rate not in (0,Decimal('2.10'),Decimal('5.50'),10,20):raise ValueError('Prestation ou taux de TVA invalide.')
        ht=money(quantity*unit);vat=money(ht*rate/100)
        result.append({'label':label,'quantity':str(quantity),'unit_eur':str(unit),'vat_rate':str(rate),'subtotal_eur':str(ht),'vat_eur':str(vat)})
    return result


def totals(items):
    ht=sum((money(x['subtotal_eur']) for x in items),Decimal(0));vat=sum((money(x['vat_eur']) for x in items),Decimal(0))
    return {'subtotal_eur':str(ht),'vat_eur':str(vat),'total_eur':str(ht+vat)}


def payment_state(db,d):
    rows=[dict(x) for x in db.execute('SELECT * FROM payments WHERE pid=? AND quote=? ORDER BY id',(d['id'],d.get('quote') or ''))]
    paid=sum((Decimal(r['amount']) for r in rows if r['mode']=='live'),Decimal(0))
    test=sum((Decimal(r['amount']) for r in rows if r['mode']=='test'),Decimal(0))
    q=get_doc(db,d.get('quote'))
    total=Decimal(q['total_eur']) if q else Decimal(0)
    status='cancelled' if d.get('cancelled') else 'received' if total>0 and paid>=total else 'partial' if paid>0 else 'refunded' if rows and any(Decimal(r['amount'])<0 for r in rows) else 'pending'
    return {'status':status,'paid_eur':str(paid),'test_eur':str(test),'remaining_eur':str(max(Decimal(0),total-paid)),'receipts':rows,'manual_notice':'Les paiements manuels sont des déclarations de l’utilisateur, sans vérification bancaire.'}


def get_doc(db,number):
    row=db.execute('SELECT data FROM documents WHERE number=?',(number,)).fetchone() if number else None
    return json.loads(row[0]) if row else None


def issue_doc(db,d,kind,data):
    year=business_date().year
    row=db.execute('SELECT n FROM sequences WHERE kind=? AND year=?',(kind,year)).fetchone()
    n=(row[0] if row else 0)+1
    prefix={'quote':'DEV-LIV','invoice':'FAC-LIV','credit':'AV-LIV'}[kind]
    number=f'{prefix}-{year}-{n:05d}'
    doc={**data,'number':number,'kind':kind,'issued_at':business_date().isoformat(),'project_id':d['id'],'project_name':d['name']}
    pdf=render_pdf(doc)
    db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(number,d['id'],kind,json.dumps(doc,ensure_ascii=False),pdf))
    db.execute('INSERT OR REPLACE INTO sequences VALUES(?,?,?)',(kind,year,n))
    return number


def validate_commercial(d):
    parties=web_sales_invoice.validate_parties(d['seller'],d['customer'])
    items=lines(d['items'],parties['vat_mode'])
    if Decimal(totals(items)['total_eur'])<=0:raise ValueError('Le total du devis doit être supérieur à zéro.')
    for party in (d['seller'],d['customer']):
        if secret_in(json.dumps(party)):raise ValueError('Retirer les secrets des coordonnées de facturation.')
    customer=d['customer']
    if customer.get('type')=='business':
        siren=re.sub(r'\s','',customer.get('siren') or customer.get('siret','')[:9])
        if not re.fullmatch(r'\d{9}',siren):raise ValueError('SIREN du client professionnel requis.')
    try:worked=date.fromisoformat(d['service_date'])
    except ValueError:raise ValueError('Date de réalisation requise (AAAA-MM-JJ).') from None
    if worked>business_date():raise ValueError('La prestation doit avoir été réalisée, sans date future.')
    return {**parties,'items':items,**totals(items),'scope':d['scope'],'maintenance':d['maintenance'],
        'service_date':d['service_date'],'due_date':(business_date()+timedelta(days=d['due_days'])).isoformat(),
        'valid_until':(business_date()+timedelta(days=d['valid_days'])).isoformat(),'legal_notice':LEGAL_NOTICE}


def document(root,store,pid,number):
    with database(root) as db:
        store.meta(pid)
        row=db.execute('SELECT pdf FROM documents WHERE pid=? AND number=?',(pid,number)).fetchone()
        if not row:raise ValueError('Document absent de ce projet.')
        return bytes(row[0])


def inventory(store,pid):
    site=store.project_dir(pid)/'site';files={};excluded=[];blocked=[];services=set();total=0
    for path in sorted(site.rglob('*')):
        rel=path.relative_to(site);name=rel.as_posix();lower=path.name.lower()
        if any(p.lower() in IGNORED for p in rel.parts):continue
        if path.is_symlink():blocked.append(name+' : lien symbolique');continue
        if not path.resolve().is_relative_to(site.resolve()):blocked.append(name+' : chemin extérieur');continue
        if not path.is_file():continue
        if (lower.startswith('.env') or lower in {'seed.sql','data.sql','dump.sql','backup.sql','.npmrc','.pypirc','credentials.json','auth.json'}
            or path.suffix.lower() in {'.pem','.key','.p12','.pfx','.sqlite','.db','.csv','.log','.zip','.gz'}):
            excluded.append(name);continue
        ext=path.suffix.lower()
        if ext not in TEXT_EXT|MEDIA_EXT and lower not in {'dockerfile','license','licence'}:
            excluded.append(name);continue
        size=path.stat().st_size
        if size>30_000_000 or total+size>200_000_000:blocked.append(name+' : taille limite dépassée');continue
        blob=path.read_bytes();total+=size
        if SECRETS.search(blob.decode('latin-1')):blocked.append(name+' : secret potentiel à retirer');continue
        if ext in TEXT_EXT or lower in {'dockerfile','license','licence'}:
            try:content=blob.decode('utf-8')
            except UnicodeDecodeError:blocked.append(name+' : texte non UTF-8');continue
            if name=='index.html' and 'La prévisualisation devrait apparaitre ici.' in content:blocked.append('Le site contient encore la page de démarrage.')
            if secret_in(content):blocked.append(name+' : secret potentiel à retirer');continue
            if ext=='.sql' and re.search(r'\b(?:INSERT\s+INTO|COPY\s+.+\s+FROM|lo_import)\b',content,re.I):
                blocked.append(name+' : export de données exclu');continue
            for service,pattern in [('supabase',r'supabase'),('vercel',r'vercel'),('payment',r'stripe|paypal|paymentintent')]:
                if re.search(pattern,name+'\n'+content,re.I):services.add(service)
            # Package scripts are instructions only; no project code is executed here.
        files[name]=blob
    if (site/'.vercel'/'project.json').is_file():services.add('vercel')
    if (site/'supabase').is_dir():services.add('supabase')
    return files,excluded,blocked,services


def revision(files):
    digest=hashlib.sha256()
    for name,blob in sorted(files.items()):digest.update(name.encode()+b'\0'+hashlib.sha256(blob).digest())
    return digest.hexdigest()


def assess(db,store,d,files,excluded,blocked,detected):
    missing=list(blocked);payment=payment_state(db,d)
    if not files:missing.append('Sources du site manquantes.')
    if d.get('cancelled'):missing.append('Règlement annulé : dossier à rouvrir avant livraison.')
    if not d.get('quote'):missing.append('Devis à préparer.')
    if d.get('accepted_quote')!=d.get('quote') or not d.get('quote'):missing.append('Acceptation du devis à enregistrer.')
    if not d.get('invoice'):missing.append('Facture définitive à générer après règlement.')
    if d.get('credit'):missing.append('Facture annulée par avoir : établir un nouveau dossier commercial.')
    if d.get('require_payment') and payment['status']!='received':missing.append('Règlement complet requis avant livraison.')
    current=revision(files)
    checks=d.get('checks') or {}
    if checks.get('revision')!=current:missing.append('Validation finale à renouveler pour les sources actuelles.')
    for key,label in [('design','Design'),('pages','Pages et mobile'),('functions','Fonctions et formulaires'),('rights','Droits des ressources')]:
        if checks.get(key) is not True:missing.append(label+' à vérifier.')
    services=d.get('services') or {}
    used=detected|{k for k,v in services.items() if v.get('enabled')}
    for key in sorted(used):
        s=services.get(key) or {}
        required={'hosting':['provider','renewal_owner','instructions'],'vercel':['project_id','instructions'],
                  'supabase':['project_ref','auth','storage','security','instructions'],
                  'payment':['provider','client_account','mode','webhooks','instructions']}[key]
        if not all(s.get(f) for f in required) or s.get('reviewed') is not True:
            missing.append({'hosting':'Hébergement à compléter.','vercel':'Configuration Vercel à finaliser avant livraison.',
                'supabase':'Configuration Supabase à finaliser avant livraison.','payment':'Le compte de paiement du client doit encore être connecté et vérifié.'}[key])
        if key=='supabase' and not any(n.startswith('supabase/migrations/') and n.endswith('.sql') for n in files):missing.append('Migrations Supabase manquantes.')
        if key=='payment' and s.get('mode')!='live':missing.append('Plateforme de paiement du site en test, production non validée.')
    return {'ready':not missing,'missing':missing,'files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()],
        'excluded':excluded,'revision':current,'services':sorted(used),'payment':payment}


def snapshot(root,store,pid):
    files,excluded,blocked,detected=inventory(store,pid)
    with database(root) as db:
        d=read(db,store,pid)
        docs=[{k:r[k] for k in ('number','kind')} for r in db.execute('SELECT number,kind FROM documents WHERE pid=? ORDER BY rowid',(pid,))]
        return {**d,'documents':docs,'assessment':assess(db,store,d,files,excluded,blocked,detected),'legal_notice':LEGAL_NOTICE}


def listing(root,store):
    with database(root) as db:
        result=[]
        for row in db.execute('SELECT data FROM dossiers ORDER BY rowid DESC'):
            d=json.loads(row[0])
            try:store.meta(d['id'])
            except (ValueError,OSError):continue
            files,excluded,blocked,detected=inventory(store,d['id'])
            report=assess(db,store,d,files,excluded,blocked,detected)
            result.append({k:d.get(k) for k in ('id','name','created_at','quote','accepted_quote','invoice') }|{
                'delivered':d.get('delivered') if (d.get('delivered') or {}).get('revision')==report['revision'] else None,
                'preparation': 'ready' if report['ready'] else 'incomplete','missing_count':len(report['missing']),
                'customer_name':d['customer'].get('name',''),'payment':report['payment']['status']})
        return result


def stripe_receipt(store,d,reference):
    """Read-only reconciliation. Browser return parameters are never evidence."""
    from local_app import web_sales_orders
    if not re.fullmatch(r'cs_(?:test|live)_[a-zA-Z0-9]{10,200}',str(reference)):raise ValueError('Référence Checkout Stripe invalide.')
    key=web_sales_orders.setting('STRIPE_SECRET_KEY')
    if not key:raise ValueError('Configurer STRIPE_SECRET_KEY sur le serveur local pour vérifier le règlement.')
    from urllib.request import Request
    record=web_sales_orders._request(Request('https://api.stripe.com/v1/checkout/sessions/'+quote(reference,safe=''),headers={'Authorization':'Bearer '+key}))
    meta=record.get('metadata') or {}
    if record.get('id')!=reference or record.get('currency')!='eur' or record.get('payment_status')!='paid' or record.get('status')!='complete':
        raise ValueError('Stripe ne confirme pas ce règlement en euros.')
    if meta.get('delivery_quote')!=d.get('quote') or meta.get('project_id')!=d['id'] or record.get('client_reference_id')!=d['id']:
        raise ValueError('La session Stripe ne correspond pas au projet et au devis. Configurer metadata.delivery_quote et metadata.project_id ainsi que client_reference_id.')
    # A full refund or a later partial refund blocks release, even on repeated checks.
    intent=record.get('payment_intent')
    if not re.fullmatch(r'pi_[A-Za-z0-9]+',str(intent or '')):raise ValueError('Paiement Stripe sans référence vérifiable.')
    pi=web_sales_orders._request(Request('https://api.stripe.com/v1/payment_intents/'+intent+'?expand[]=latest_charge',headers={'Authorization':'Bearer '+key}))
    charge=pi.get('latest_charge') or {}
    if pi.get('status')!='succeeded' or not isinstance(charge,dict) or charge.get('amount_refunded',0)>0:
        raise ValueError('Paiement remboursé ou non vérifiable : livraison bloquée.')
    return money(Decimal(record['amount_total'])/100),'live' if record.get('livemode') is True else 'test'


def action(root,store,pid,body):
    if not isinstance(body,dict):raise ValueError('Requête invalide.')
    kind=body.get('action');files,excluded,blocked,detected=inventory(store,pid)
    with database(root) as db:
        d=read(db,store,pid)
        if body.get('version')!=d['version']:raise ValueError('Le dossier a changé : recharger avant de modifier.')
        if kind=='save':
            if d.get('quote'):raise ValueError('Le devis émis est figé. Utiliser les actions de suivi ou un avoir ; ses montants ne sont pas modifiés.')
            for key in ('seller','customer'):
                value=body.get(key,d[key]);d[key]={k:text(v) for k,v in value.items() if k in PARTY_FIELDS}
            d['items']=lines(body.get('items',d['items']),d['seller'].get('vat_mode'))
            for key in ('scope','maintenance','service_date'):
                d[key]=text(body.get(key,d[key]))
                if secret_in(d[key]):raise ValueError('Retirer les secrets du document commercial.')
            for key in ('due_days','valid_days'):
                value=int(body.get(key,d[key]));
                if not 0<=value<=120:raise ValueError('Durée hors limites (0 à 120 jours).')
                d[key]=value
            d['require_payment']=body.get('require_payment',True) is True
        elif kind=='technical':
            configs=body.get('services',{})
            clean={}
            for key,fields in SERVICE_FIELDS.items():
                value=configs.get(key,{})
                clean[key]={f:text(value.get(f)) for f in fields}
                clean[key].update(enabled=value.get('enabled') is True,reviewed=value.get('reviewed') is True)
                if secret_in(json.dumps(clean[key])):raise ValueError('Une fiche technique contient un secret : utiliser un canal distinct.')
            d['services']=clean
            checks=body.get('checks',{})
            d['checks']={key:checks.get(key) is True for key in ('design','pages','functions','rights')}
            d['checks']['revision']=revision(files)
            d['delivered']=None
        elif kind=='quote':
            if body.get('confirmed') is not True:raise ValueError('Valider les identités et les montants du devis.')
            if not d.get('quote'):d['quote']=issue_doc(db,d,'quote',validate_commercial(d))
        elif kind=='accept':
            if not d.get('quote') or body.get('confirmed') is not True:raise ValueError('Confirmer l’acceptation du devis par le client.')
            d['accepted_quote']=d['quote']
        elif kind=='cancel':
            if body.get('confirmed') is not True or Decimal(payment_state(db,d)['paid_eur'])>0:raise ValueError('Annulation réservée aux dossiers sans règlement reçu ; déclarer un remboursement si nécessaire.')
            d['cancelled']=not d.get('cancelled',False)
            d['delivered']=None
        elif kind in ('payment','stripe'):
            if d.get('cancelled'):raise ValueError('Rouvrir le dossier avant d’enregistrer un règlement.')
            if d.get('accepted_quote')!=d.get('quote') or not d.get('quote'):raise ValueError('Acceptation du devis requise.')
            if d.get('credit'):raise ValueError('Facture annulée par avoir.')
            if body.get('confirmed') is not True:raise ValueError('Confirmer le règlement déclaré et la préparation automatique de la facture.')
            ref=text(body.get('reference'),220)
            if not ref:raise ValueError('Référence du règlement obligatoire.')
            source='stripe' if kind=='stripe' else 'manual'
            amount,mode=stripe_receipt(store,d,ref) if kind=='stripe' else (money(body.get('amount')),'live')
            if amount<=0:raise ValueError('Montant reçu attendu.')
            old=db.execute('SELECT * FROM payments WHERE source=? AND reference=?',(source,ref)).fetchone()
            if old and (old['pid']!=pid or old['quote']!=d['quote'] or Decimal(old['amount'])!=amount):raise ValueError('Référence de règlement déjà utilisée.')
            state=payment_state(db,d);q=get_doc(db,d['quote'])
            if not old and amount+Decimal(state['paid_eur'])>Decimal(q['total_eur']) and mode=='live':raise ValueError('Le règlement dépasse le solde du devis.')
            if not old:db.execute('INSERT INTO payments(pid,quote,amount,source,reference,mode,at) VALUES(?,?,?,?,?,?,?)',(pid,d['quote'],str(amount),source,ref,mode,business_date().isoformat()))
            if mode=='live' and not d.get('invoice'):
                d['invoice']=issue_doc(db,d,'invoice',{**q,'quote_number':d['quote'],'payment':payment_state(db,d),'due_date':business_date().isoformat()})
        elif kind=='refund':
            if body.get('confirmed') is not True:raise ValueError('Confirmation du remboursement déclaré requise.')
            state=payment_state(db,d);amount=money(body.get('amount'));ref=text(body.get('reference'),220)
            if amount<=0 or amount>Decimal(state['paid_eur']) or not ref:raise ValueError('Remboursement ou référence invalide.')
            # Manual correction is a declaration, never an API refund.
            db.execute('INSERT INTO payments(pid,quote,amount,source,reference,mode,at) VALUES(?,?,?,?,?,?,?)',(pid,d['quote'],str(-amount),'manual-refund',ref,'live',business_date().isoformat()))
            d['delivered']=None
        elif kind=='credit':
            if body.get('confirmed') is not True or not d.get('invoice'):raise ValueError('Facture et validation explicite de l’avoir requises.')
            reason=text(body.get('reason'),600)
            if not reason:raise ValueError('Motif de l’avoir obligatoire.')
            if not d.get('credit'):d['credit']=issue_doc(db,d,'credit',{**get_doc(db,d['invoice']),'invoice_reference':d['invoice'],'reason':reason})
            d['delivered']=None
        elif kind=='delivered':
            report=assess(db,store,d,files,excluded,blocked,detected)
            if body.get('confirmed') is not True or not report['ready']:raise ValueError('Compléter et confirmer la livraison avant de la marquer effectuée.')
            d['delivered']={'at':business_date().isoformat(),'revision':report['revision'],'declaration':'Livraison déclarée par l’utilisateur ; aucun envoi automatique.'}
        else:raise ValueError('Action de livraison inconnue.')
        write(db,d,kind)
    return snapshot(root,store,pid)


def render_pdf(doc):
    """Flow layout supports long addresses, labels, and multiple pages."""
    from html import escape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    out=io.BytesIO();styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallLiv',fontName='Helvetica',fontSize=9,leading=13,spaceAfter=7))
    styles.add(ParagraphStyle(name='LivTitle',fontName='Helvetica-Bold',fontSize=24,leading=30,textColor=colors.HexColor('#392359'),spaceAfter=14))
    p=lambda value,style='SmallLiv':Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
    title=doc.get('title') or {'quote':'DEVIS','invoice':'FACTURE','credit':'AVOIR'}.get(doc.get('kind'),'LIVRAISON CLIENT')
    story=[p('LOCALAI STUDIO  /  '+doc.get('seller',{}).get('name','Livraison client')),p(title,'LivTitle'),p(doc.get('number','')+'  |  '+doc.get('project_name',''))]
    if doc.get('issued_at'):story.append(p('Émis le '+doc['issued_at']+' | Prestation : '+doc.get('service_date','')))
    if doc.get('valid_until') and doc.get('kind')=='quote':story.append(p('Devis gratuit valable jusqu’au '+doc['valid_until']))
    if doc.get('quote_number'):story.append(p('Devis de référence : '+doc['quote_number']))
    if doc.get('invoice_reference'):story.append(p('Annulation intégrale de la facture '+doc['invoice_reference']+' | Motif : '+doc.get('reason','')))
    for key,label in [('seller','PRESTATAIRE'),('customer','CLIENT')]:
        party=doc.get(key,{})
        if not party:continue
        story.extend([p(label,'Heading3'),p(party.get('name','')+' '+(party.get('legal_form','') if key=='seller' else '')),p(party.get('address',''))])
        for field,caption in [('siret','SIRET'),('siren','SIREN'),('vat_number','TVA'),('capital','Capital'),('registration','Immatriculation'),('order_number','Bon de commande')]:
            if party.get(field):story.append(p(caption+' : '+party[field]))
    if doc.get('scope'):story.extend([p('Prestations et périmètre','Heading3'),p(doc['scope'])])
    if doc.get('items'):
        rows=[[p(x) for x in ['Prestation','Qté','PU HT','TVA','Total HT']]]
        for item in doc['items']:rows.append([p(item['label']),p(item['quantity']),p(item['unit_eur']),p(item['vat_rate']+' %'),p(item['subtotal_eur'])])
        table=Table(rows,colWidths=[238,38,65,55,79],repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eee8f6')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#9879bb'))]))
        story.extend([Spacer(1,12),table,Spacer(1,12)])
        sign='-' if doc.get('kind')=='credit' else ''
        story.append(KeepTogether([p('Total HT : '+sign+doc['subtotal_eur']+' EUR'),p('TVA : '+sign+doc['vat_eur']+' EUR'),p('TOTAL TTC : '+sign+doc['total_eur']+' EUR','Heading2')]))
        seller=doc['seller'];customer=doc['customer']
        if doc.get('vat_mode')=='franchise':story.append(p('TVA non applicable, art. 293 B du CGI.'))
        story.extend([p('Nature : prestations de services.'),p('Modalités de paiement : '+seller.get('payment_details','')),p('Échéance : '+doc.get('due_date','')),p('Escompte pour paiement anticipé : néant.')])
        if seller.get('vat_on_debits')=='oui':story.append(p('Option pour le paiement de la taxe d’après les débits.'))
        if customer.get('type')=='business':story.extend([p('Pénalités de retard : '+seller.get('late_penalty_rate','')),p('Indemnité forfaitaire de recouvrement : 40 EUR (client professionnel).')])
    for heading,value in doc.get('sections',[]):story.extend([p(heading,'Heading3'),p(value)])
    if doc.get('maintenance'):story.extend([p('Maintenance','Heading3'),p(doc['maintenance'])])
    if doc.get('kind')=='quote':story.append(p('Acceptation : date, nom et signature du client. Aucun envoi ni accord enregistré automatiquement.'))
    story.extend([Spacer(1,12),p(LEGAL_NOTICE),p(LEGAL_URL),p(EINVOICE_URL)])
    def footer(canvas,document):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#725590'))
        canvas.drawString(42,25,'LocalAiStudio | Document local | Page '+str(document.page))
    SimpleDocTemplate(out,pagesize=(595.28,841.89),leftMargin=42,rightMargin=42,topMargin=36,bottomMargin=48,title=title).build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()


def package(root,store,pid,expected_revision=None,download=False,expected_version=None):
    files,excluded,blocked,detected=inventory(store,pid)
    with database(root) as db:
        d=read(db,store,pid)
        if expected_version!=d['version']:raise ValueError('Le dossier a changé : préparer à nouveau le paquet.')
        report=assess(db,store,d,files,excluded,blocked,detected)
        # Recheck live connected receipts before each release. Failure is closed.
        for row in report['payment']['receipts']:
            if row['source']=='stripe' and row['mode']=='live':stripe_receipt(store,d,row['reference'])
        if not report['ready']:raise ValueError('Livraison incomplète : '+' '.join(report['missing']))
        if expected_revision!=report['revision']:raise ValueError('Les sources ont changé : prévisualiser à nouveau le paquet.')
        payload={};prefix='Livraison_'+re.sub(r'[^a-zA-Z0-9_-]+','_',d['name']).strip('_')[:70]
        for name,blob in files.items():
            base='04_Base_de_Donnees/Supabase/' if name.startswith('supabase/') else '01_Site_Web/Sources/'
            payload[base+name]=blob
        for key,name in [('quote','Devis'),('invoice','Facture')]:
            row=db.execute('SELECT pdf FROM documents WHERE number=? AND pid=?',(d[key],pid)).fetchone()
            payload['02_Documents/'+name+'.pdf']=bytes(row[0])
        doc={'project_name':d['name'],'seller':d['seller'],'customer':d['customer'],'maintenance':d['maintenance'],
             'sections':[('Site',d['scope']),('Validation','Design, pages, fonctions, mobile et droits des ressources déclarés vérifiés pour la révision '+report['revision']),('Règlement',json.dumps(report['payment'],ensure_ascii=False)),('Livraison','Sources et documents préparés localement. Aucun transfert de compte ni envoi client automatique.')]}
        payload['02_Documents/Recapitulatif_Livraison.pdf']=render_pdf({**doc,'title':'RÉCAPITULATIF DE LIVRAISON'})
        guide='Installer les dépendances à partir du manifeste et du lockfile fournis. Examiner les scripts avant exécution. Configurer les variables nécessaires dans le compte du client, par un canal sécurisé distinct. Lancer les commandes prévues par le projet puis vérifier les pages, formulaires et la version mobile. Ne jamais réutiliser les clés personnelles du prestataire.'
        manifest_source={}
        if 'package.json' in files:
            try:manifest_source=json.loads(files['package.json'].decode())
            except (ValueError,UnicodeDecodeError):pass
        scripts=manifest_source.get('scripts') or {}
        if scripts:
            manager='pnpm' if 'pnpm-lock.yaml' in files else 'yarn' if 'yarn.lock' in files else 'npm'
            guide+='\nGestionnaire détecté : '+manager+'. Scripts disponibles : '+', '.join(scripts)+'. Examiner les commandes dans package.json avant exécution. Un script build permet la reconstruction s’il est présent.'
        else:guide+='\nAucun script de compilation détecté : servir les fichiers statiques avec un serveur HTTP et ouvrir index.html. Vérifier les routes et dépendances distantes du site.'
        variables=set()
        for name,blob in files.items():
            if Path(name).suffix.lower() in TEXT_EXT:
                content=blob.decode('utf-8')
                variables.update(re.findall(r'(?:process\.env|import\.meta\.env)\.([A-Z][A-Z0-9_]{1,100})',content))
        if variables:
            payload['01_Site_Web/Instructions/Variables.example.txt']=('Noms détectés dans les sources ; valeurs à renseigner dans le compte du client, par canal sécurisé.\n'+'\n'.join(v+'=<A_CONFIGURER>' for v in sorted(variables))).encode()
        payload['01_Site_Web/Instructions/Installation.txt']=guide.encode()
        for key in report['services']:
            value=d['services'].get(key,{})
            details='\n'.join(f'{k} : {v}' for k,v in value.items() if k not in {'enabled','reviewed'})
            if key=='vercel':details+='\nTransfert : depuis Settings > General > Transfer Project. Vérifier les droits des deux équipes. Validation explicite obligatoire avant toute opération. https://vercel.com/docs/projects/transferring-projects'
            if key=='supabase':details+='\nReconstruire dans le projet du client avec les migrations examinées, les fonctions et les politiques fournies. Reconfigurer Auth et Storage. Aucune ligne de données, identité Auth ou clé privilégiée incluse. https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore'
            if key=='payment':details+='\nConnecter le compte du client, recréer les secrets de webhook, vérifier signatures et événements en test puis en production. Aucun transfert de clés personnelles. Stripe pour encaissement du devis et plateforme du site sont deux configurations distinctes.'
            folder={'hosting':'03_Hebergement','vercel':'03_Hebergement/Vercel','supabase':'04_Base_de_Donnees/Supabase','payment':'05_Paiements'}[key]
            payload[folder+'/Configuration.txt']=details.encode()
        for title,sections in [('Guide_Client',[('Mise en service',guide)]),('Maintenance',[('Conditions',d['maintenance'] or 'Aucun contrat de maintenance renseigné. Définir les responsabilités et coûts avant toute prestation récurrente.')]),('Checklist_Livraison',[('Vérifications','\n'.join(['Sources contrôlées et révision figée.','Documents commerciaux présents.','Secrets exclus du ZIP.','Vérifier les comptes, domaines, renouvellements et droits du client.']+['Service configuré : '+s for s in report['services']]))])]:
            payload['06_Documentation/'+title+'.pdf']=render_pdf({'title':title.replace('_',' '),'project_name':d['name'],'sections':sections})
        manifest={'schema':1,'project_id':pid,'revision':report['revision'],'excluded':excluded,'files':[{'path':n,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in payload.items()]}
        payload['Manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
        if not download:return {'name':prefix+'.zip','revision':report['revision'],'version':d['version'],'files':manifest['files'],'notice':'Préparation locale uniquement. Aucun fichier envoyé au client.'}
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for name,blob in payload.items():z.writestr(prefix+'/'+name,blob)
        return prefix+'.zip',out.getvalue()
