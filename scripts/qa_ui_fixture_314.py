"""Only labelled fixtures inside the isolated QA store; no user projects."""
import json
from pathlib import Path
import sys
from local_app.web_builder import LocalAiWebStore

root = Path(sys.argv[1]).resolve()
if not root.name.startswith('studio-ui-314-'):
    raise ValueError('An isolated Build 314 QA store is required.')
store = LocalAiWebStore(root / 'localaiweb' / 'projects', lambda *_: '{}')
first = store.create('Recette 314 — prompt exact')['project']['id']
second = store.create('Recette 314 — à conserver')['project']['id']
legacy = store.create('Recette 314 — ancien projet')['project']['id']
preview = store.create('Recette 314 — aperçu GPU')['project']['id']
prompt = '  Site de démonstration QA\navec accents : café, création.\nEspaces conservés.  '
store.remember_original_prompt(first, prompt)
meta = store.meta(legacy)
del meta['original_prompt']
store.write_meta(legacy, meta)
store.write_files(preview, {'index.html': '<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Recette QA</title></head><body><main><h1>Aperçu LocalAiWeb de validation</h1><p>Projet de démonstration isolé pour vérifier la communication de cadence entre l’éditeur et son aperçu intégré.</p></main></body></html>'})
print(json.dumps({'first': first, 'second': second, 'legacy': legacy, 'preview': preview, 'prompt': prompt}))
