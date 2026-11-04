"""Local provenance for public renders. No telemetry and no inferred benchmarks.

The submitted API graph is the effective parameter record. Missing model hashes,
RAM/VRAM peaks and split inference/encoding timings stay null until measured.
"""
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from local_app.atomic_storage import atomic_write

_LOCK = threading.RLock()
_MODEL_KEYS = {'ckpt_name','unet_name','clip_name','clip_name1','clip_name2','vae_name','lora_name'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',',':')).encode()).hexdigest()


def _path(root, prompt_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', str(prompt_id or '')):
        raise ValueError('Identifiant de génération invalide.')
    return Path(root) / 'public-provenance' / (prompt_id + '.json')


def submitted(root, prompt_id, *, build, workflow, graph, original_prompt, effective_prompt, negative, settings):
    models = sorted({str(value) for node in graph.values() for key,value in node.get('inputs',{}).items()
                     if key in _MODEL_KEYS and isinstance(value,str)})
    record = {'schema':1, 'id':prompt_id, 'state':'queued', 'submitted_at_utc_epoch':time.time(),
              'build':build, 'original_prompt':original_prompt, 'effective_prompt':effective_prompt,
              'effective_negative':negative, 'workflow_sha256':digest(workflow), 'submitted_graph_sha256':digest(graph),
              'submitted_graph':graph, 'requested_settings':settings,
              'models':[{'name':name,'sha256':None,'hash_status':'not_measured'} for name in models],
              'measurements':{'inference_seconds':None,'encoding_seconds':None,'peak_ram_bytes':None,'peak_vram_bytes':None},
              'outputs':[], 'error':None}
    with _LOCK:
        atomic_write(_path(root,prompt_id),json.dumps(record,ensure_ascii=False,indent=2).encode())
    return record


def read(root, prompt_id):
    with _LOCK:
        return json.loads(_path(root,prompt_id).read_text(encoding='utf-8'))


def complete(root, prompt_id, info):
    path = _path(root,prompt_id)
    with _LOCK:
        if not path.is_file():
            return None  # Private/legacy/external jobs have no public trace.
        record = read(root,prompt_id)
        status = info.get('status') or {}
        if record['state'] in ('done','error'):
            return record
        if not status.get('completed') and status.get('status_str') not in ('error','failed'):
            return record
        record['state'] = 'error' if status.get('status_str') in ('error','failed') else 'done'
        record['observed_finished_at_utc_epoch'] = time.time()
        record['elapsed_including_queue_seconds'] = record['observed_finished_at_utc_epoch'] - record['submitted_at_utc_epoch']
        record['engine_status'] = status
        record['outputs'] = [{**item, 'sha256':None,'hash_status':'not_measured'}
                             for node in info.get('outputs',{}).values() for kind in ('images','videos','gifs')
                             for item in node.get(kind,[]) if item.get('filename')]
        if record['state']=='error':
            record['error'] = status.get('messages',[])
        atomic_write(path,json.dumps(record,ensure_ascii=False,indent=2).encode())
        return record


def record_output_bytes(root, prompt_id, filename, subfolder, raw):
    with _LOCK:
        record=read(root,prompt_id)
        matched=False
        for output in record['outputs']:
            if output['filename']==filename and output.get('subfolder','')==subfolder:
                output.update(sha256=hashlib.sha256(raw).hexdigest(),hash_status='measured_on_download',size_bytes=len(raw))
                matched=True
        if matched:
            atomic_write(_path(root,prompt_id),json.dumps(record,ensure_ascii=False,indent=2).encode())
        return matched
