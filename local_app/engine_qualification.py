"""Evidence-based public engine states; installed is never equivalent to qualified."""
import hashlib
import json
import re


def fingerprint(graph_hash, models, runtime):
    system = runtime.get('system') or {}
    stable_runtime = {'system':{k:system.get(k) for k in ('os','python_version','pytorch_version','comfyui_version','ram_total')},
                      'devices':[{k:d.get(k) for k in ('name','type','vram_total')} for d in runtime.get('devices',[])]}
    return hashlib.sha256(json.dumps({'graph':graph_hash,'models':models,'runtime':stable_runtime},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()


def assess(*, installed, available, reports=(), identity=None):
    valid = [r for r in reports if identity and r.get('identity')==identity and r.get('executed') is True
             and r.get('outputs_verified') is True and r.get('success') is True]
    # Repeated copies of the same receipt are one run, not three benchmarks.
    valid = list({r['prompt_id']:r for r in valid if r.get('prompt_id')}.values())
    reviewed = [r for r in valid if (r.get('quality_review') or {}).get('accepted') is True
                and (r.get('quality_review') or {}).get('reviewer') and r.get('models')
                and all(re.fullmatch(r'[a-f0-9]{64}',m.get('sha256') or '') for m in r['models'])]
    if not available:
        state='installed' if installed else 'unavailable'
    elif len(reviewed)>=3:
        state='qualified'
    elif valid:
        state='tested'
    else:
        state='available'
    if installed and not available:
        label='Installé — moteur indisponible'
    else:
        label={'unavailable':'Indisponible','available':'Disponible — non testé',
               'tested':'Testé — qualité non qualifiée','qualified':'Qualifié'}[state]
    return {'state':state,'label':label,'installed':bool(installed),'available':bool(available),
            'tested':bool(valid),'qualified':state=='qualified','successful_runs':len(valid),
            'reviewed_runs':len(reviewed),'identity':identity,
            'qualification_policy':'3 rendus vérifiés et acceptés visuellement sur la même identité modèle/workflow/runtime/matériel.'}
