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
prompt = '  Site de démonstration QA\navec accents : café, création.\nEspaces conservés.  '
store.remember_original_prompt(first, prompt)
meta = store.meta(legacy)
del meta['original_prompt']
store.write_meta(legacy, meta)
print(json.dumps({'first': first, 'second': second, 'legacy': legacy, 'prompt': prompt}))
