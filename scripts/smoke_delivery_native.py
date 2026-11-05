"""Exercise the frozen EXE's delivery module with local fictional data only."""
import io
import json
import zipfile
from datetime import datetime
from urllib.request import Request, urlopen

BASE='http://127.0.0.1:3000'

def call(path,body=None,dedicated=False):
    headers={'Content-Type':'application/json'}
    if dedicated:headers.update({'Host':'ventes.localhost:3000','X-LocalAI-Delivery':'1','Origin':'http://ventes.localhost:3000'})
    req=Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urlopen(req,timeout=30) as response:
        data=response.read()
        return json.loads(data) if 'json' in response.headers.get('Content-Type','') else data

project=call('/api/web/project/create',{'name':'RECETTE EXE LIVRAISON FICTIVE'})
pid=project['project']['id']
call('/api/web/file/save',{'id':pid,'path':'index.html','content':'<!doctype html><html lang="fr"><title>Recette fictive</title><body>Site fictif pour recette native.</body></html>'})
d=call('/api/web/delivery/dossier?id='+pid,dedicated=True)
def action(name,**fields):
    global d
    d=call('/api/web/delivery/action',{'id':pid,'version':d['version'],'action':name,**fields},True)

action('save',seller={'name':'Émetteur fictif','siret':'53784237900027','address':'Adresse de test','legal_form':'EI','vat_mode':'franchise','payment_details':'Virement de test','late_penalty_rate':'Taux contractuel fictif'},customer={'name':'Client fictif','address':'Adresse fictive','type':'consumer'},service_date=datetime.now().date().isoformat(),items=[{'label':'Prestation fictive','quantity':'1','unit_eur':'100'}])
action('quote',confirmed=True)
action('accept',confirmed=True)
action('payment',amount='100',reference=pid+'-fixture',confirmed=True)
action('technical',checks={k:True for k in ('design','pages','functions','rights')})
assert d['assessment']['ready'],d['assessment']['missing']
for number in (d['quote'],d['invoice']):assert call('/api/web/delivery/document?id='+pid+'&number='+number,dedicated=True).startswith(b'%PDF-')
prepared=call('/api/web/delivery/prepare',{'id':pid,'version':d['version'],'revision':d['assessment']['revision']},True)
blob=call('/api/web/delivery/download',{'id':pid,'version':prepared['version'],'revision':prepared['revision']},True)
with zipfile.ZipFile(io.BytesIO(blob)) as archive:
    assert archive.testzip() is None
    assert any(n.endswith('Facture.pdf') for n in archive.namelist())
print('FROZEN DELIVERY PASS: real EXE HTTP, SQLite, quote/invoice PDFs, local declared receipt, ZIP. No real transaction.')
