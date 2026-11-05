"""Explicit operator business acceptance, distinct from generated UI assertions."""
import json
import re
import time
import threading
from functools import wraps
from local_app import web_delivery
from local_app.atomic_storage import atomic_write, project_lock

_LOCK=threading.RLock()


def _guard(method):
    @wraps(method)
    def call(store,pid,*args,**kwargs):
        with _LOCK,project_lock(store.project_dir(pid)):
            return method(store,pid,*args,**kwargs)
    return call


STATUSES={'functional':'Fonctionnelle','requires_configuration':'Nécessite une configuration',
          'demonstration':'Démonstration','unavailable':'Non disponible','error':'En erreur'}


def describe(store,pid):
    root=store.project_dir(pid);site=root/'site';current=web_delivery.revision(site)
    path=site/'localai-functional.json'
    try:
        if path.stat().st_size>100000:raise ValueError('Contrat trop volumineux.')
        plan=json.loads(path.read_text(encoding='utf-8'))
        rows=plan.get('features')
        if not isinstance(rows,list) or not 1<=len(rows)<=30:raise ValueError('De 1 à 30 fonctionnalités attendues.')
        features=[];seen=set()
        for row in rows:
            key=str(row.get('id') or '')
            if not re.fullmatch(r'[a-z][a-z0-9_-]{1,60}',key) or key in seen:raise ValueError('Identifiant de fonctionnalité invalide ou répété.')
            seen.add(key)
            label=str(row.get('label') or '').strip()[:140]
            criterion=str(row.get('acceptance') or '').strip()[:900]
            if not label or not criterion:raise ValueError('Libellé et critère de recette requis.')
            status=row.get('status')
            if status not in STATUSES or status=='functional':status='demonstration'
            features.append({'id':key,'label':label,'acceptance':criterion,'required':row.get('required') is not False,
                             'status':status,'configuration':str(row.get('configuration') or '')[:900]})
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        return {'revision':current,'features':[],'verified':False,'error':'Contrat fonctionnel absent ou invalide : '+str(exc)}
    try:receipt=json.loads((root/'functional_checks.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):receipt={}
    checks=receipt.get('checks',{}) if receipt.get('revision')==current else {}
    for feature in features:
        check=checks.get(feature['id']) or {}
        if check.get('source')=='operator_manual' and check.get('outcome') in ('passed','failed'):
            feature.update(status='functional' if check['outcome']=='passed' else 'error',evidence=check)
        feature['status_label']=STATUSES[feature['status']]
    required=[f for f in features if f['required']]
    return {'revision':current,'features':features,'verified':bool(required) and all(f['status']=='functional' for f in required),
            'source':'Operator acceptance; not an automated backend/checkout certification.'}


@_guard
def record(store,pid,body):
    if body.get('confirmed') is not True:raise ValueError('Validation manuelle explicite requise.')
    plan=describe(store,pid)
    if body.get('revision')!=plan['revision']:raise ValueError('Le projet a changé ; refaire les tests sur cette version.')
    feature=next((f for f in plan['features'] if f['id']==body.get('feature_id')),None)
    if not feature:raise ValueError('Fonctionnalité absente du contrat.')
    outcome=body.get('outcome');evidence=str(body.get('evidence') or '').strip()
    if outcome not in ('passed','failed') or not 20<=len(evidence)<=2500:
        raise ValueError('Décris le test exécuté, son résultat et sa preuve (20 à 2500 caractères).')
    root=store.project_dir(pid)
    path=root/'functional_checks.json'
    try:previous=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):previous={}
    checks=previous.get('checks',{}) if previous.get('revision')==plan['revision'] else {}
    checks[feature['id']]={'source':'operator_manual','outcome':outcome,'evidence':evidence,
                          'acceptance':feature['acceptance'],'at_utc_epoch':time.time()}
    required=[f for f in plan['features'] if f['required']]
    verified=bool(required) and all((checks.get(f['id']) or {}).get('outcome')=='passed' for f in required)
    receipt={'schema':1,'revision':plan['revision'],'verified':verified,'checks':checks,'source':'operator_manual'}
    atomic_write(path,json.dumps(receipt,ensure_ascii=False,indent=2).encode())
    # Keep the old visual review bound to its original revision. Operator
    # acceptance must not accidentally certify screenshots from an older site.
    delivery=web_delivery.current(store,pid)
    if delivery.get('revision')==plan['revision'] and 'project_changed_since_review' not in delivery.get('blocking_reasons',[]):
        web_delivery.save(store,pid,delivery.get('technical') or {},delivery.get('visual') or {})
    return describe(store,pid)


def instructions():
    return '''FUNCTIONAL ACCEPTANCE CONTRACT: write localai-functional.json with schema 1 and features.
Each feature needs id (lowercase identifier), label, required (boolean), acceptance (a concrete test),
status (requires_configuration, demonstration, unavailable or error), configuration (missing setup).
List every requested business capability, including forms/receipt, bookings, cart/orders, login and test checkout when requested.
For a static site include navigation, responsive/keyboard usability and export acceptance.
An attractive button, alert or local placeholder is a demonstration, not a working backend.
Do not claim functional status or create operator test receipts: only observed tests/explicit operator acceptance may validate them.
Never perform real payments, purchases, publication or outreach as part of acceptance. Keep configuration requirements explicit.'''
