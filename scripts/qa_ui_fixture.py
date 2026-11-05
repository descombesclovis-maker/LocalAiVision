"""Explicitly labelled test site in the isolated QA store, never user projects."""
from pathlib import Path
import json
import sys
from local_app import web_builder, web_google_maps

root=Path(sys.argv[1]).resolve()
if not root.name.startswith('studio-ui-313-'):
    raise ValueError('This helper requires the temporary UI QA store.')
store=web_builder.LocalAiWebStore(root/'localaiweb'/'projects',lambda *_:'{}')
if sys.argv[2]=='pro':
    payload,_=web_google_maps.create_reference_project(store,{'google_place_id':'UI_QA_PLACE_313'})
else:
    pid=sys.argv[2]
    store.meta(pid)
    store.write_files(pid,{'index.html':'<!doctype html><html lang="fr"><meta charset="utf-8"><title>Site de recette technique</title><style>body{font:18px system-ui;margin:3rem;color:#123}h1{font-weight:500}</style><main><p>RECETTE TECHNIQUE — DONNÉES DE TEST</p><h1>Vraie prévisualisation HTML</h1><p>Ce site de test valide aperçu, sources, export et versions. Il ne provient pas d’une génération IA.</p></main></html>'})
    store.write_files(pid,{'localai-functional.json':json.dumps({'schema':1,'features':[
        {'id':'navigation','label':'Navigation de recette — données de test',
         'acceptance':'Fixture technique : ouvrir les pages prévues, sans génération IA ni opération commerciale.',
         'status':'demonstration','required':True}]})})
    store.snapshot(pid,'Version de recette')
    payload=store.payload(pid)
print(json.dumps({'id':payload['project']['id']}))
