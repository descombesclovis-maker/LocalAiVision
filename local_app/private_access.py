"""Server-side private-session gate and non-destructive media ownership index.

This is access control for the application HTTP surface, not disk encryption or
protection from another process running as the same Windows user. Existing PIN
semantics are preserved; legacy browser-only media must be indexed on unlock.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from pathlib import Path
from local_app.atomic_storage import atomic_write

_LOCK=threading.RLock()
_sessions={}
_failures=[]
COOKIE='localai_private_session'
_TTL=8*3600
_DEFAULT_HASH='65004614046659cba944b13593730e6c784f1fe2e76d79f9db023be1b0d59cb5'


def unlock(code):
    now=time.time()
    with _LOCK:
        _failures[:]=[stamp for stamp in _failures if now-stamp<60]
        if len(_failures)>=5:raise ValueError('Trop de tentatives. Réessayer dans une minute.')
        actual=hashlib.pbkdf2_hmac('sha256',str(code).encode(),b'LocalAiStudio-existing-access',200000).hex()
        configured=os.getenv('LOCALAI_PRIVATE_PIN')
        expected=hashlib.pbkdf2_hmac('sha256',configured.encode(),b'LocalAiStudio-existing-access',200000).hex() if configured else _DEFAULT_HASH
        if not hmac.compare_digest(actual,expected):
            _failures.append(now);raise ValueError('Code d’accès incorrect.')
        _failures.clear()
        token=secrets.token_urlsafe(32)
        _sessions[hashlib.sha256(token.encode()).hexdigest()]=now+_TTL
        return token,now+_TTL


def session(cookie):
    try:
        parsed=SimpleCookie();parsed.load(cookie or '')
        token=parsed[COOKIE].value
    except (KeyError,ValueError):return None
    now=time.time()
    with _LOCK:
        for key,expires in list(_sessions.items()):
            if expires<=now:_sessions.pop(key,None)
        expires=_sessions.get(hashlib.sha256(token.encode()).hexdigest())
        return {'authenticated':True,'expires_at':expires} if expires and expires>now else None


def revoke(cookie):
    parsed=SimpleCookie()
    try:
        parsed.load(cookie or '')
        with _LOCK:_sessions.pop(hashlib.sha256(parsed[COOKIE].value.encode()).hexdigest(),None)
    except (KeyError,ValueError):pass


def _read(root):
    path=Path(root)/'private-access'/'ownership.json'
    if not path.exists():return {'schema':1,'jobs':{},'files':{}}
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!=1 or not isinstance(data.get('jobs'),dict) or not isinstance(data.get('files'),dict):
        raise ValueError('Index privé illisible ; accès refusé.')
    return data


def _write(root,data):
    atomic_write(Path(root)/'private-access'/'ownership.json',json.dumps(data,ensure_ascii=False).encode())


def file_key(filename,subfolder='',kind='output'):
    def normalize(value):
        raw=str(value or '').replace('\\','/')
        p=Path(raw)
        if p.is_absolute() or '..' in p.parts or ':' in raw or '\x00' in raw:raise ValueError('Chemin média invalide.')
        return p.as_posix() if raw else ''
    name=normalize(filename);folder=normalize(subfolder)
    if not name or '/' in name or kind not in ('input','output','temp'):raise ValueError('Média invalide.')
    return str(kind)+'/'+folder+'/'+name


def register_job(root,prompt_id):
    with _LOCK:
        data=_read(root);data['jobs'][str(prompt_id)]={'completed':False};_write(root,data)


def register_outputs(root,prompt_id,info):
    with _LOCK:
        data=_read(root)
        if str(prompt_id) not in data['jobs']:return
        for node in info.get('outputs',{}).values():
            for kind in ('images','videos','gifs'):
                for output in node.get(kind,[]):
                    if output.get('filename'):
                        data['files'][file_key(output['filename'],output.get('subfolder',''),output.get('type','output'))]=True
        if info.get('status',{}).get('completed') or info.get('status',{}).get('status_str') in ('error','failed'):
            data['jobs'][str(prompt_id)]['completed']=True
        _write(root,data)


def index_legacy(root,files):
    if not isinstance(files,list) or len(files)>20000:raise ValueError('Inventaire privé invalide.')
    # Validate the entire inventory before replacing the index. Original media
    # and browser saves are never moved, deleted or rewritten.
    keys=[file_key(row.get('filename'),row.get('subfolder',''),row.get('type','output')) for row in files]
    with _LOCK:
        data=_read(root)
        for key in keys:data['files'][key]=True
        _write(root,data)
    return len(keys)


def private_job(root,prompt_id):
    with _LOCK:return str(prompt_id) in _read(root)['jobs']


def private_file(root,filename,subfolder='',kind='output'):
    key=file_key(filename,subfolder,kind)
    with _LOCK:return key in _read(root)['files']


def pending_jobs(root):
    with _LOCK:return [pid for pid,row in _read(root)['jobs'].items() if not row.get('completed')]


def begin_submission(root):
    # Persist uncertainty BEFORE contacting ComfyUI. If the process dies between
    # queue acceptance and ownership registration, unauthenticated media access
    # stays closed after restart instead of exposing an unindexed private output.
    atomic_write(Path(root)/'private-access'/'pending-submission.json',json.dumps({'at':time.time()}).encode())


def uncertain_submission(root):
    return (Path(root)/'private-access'/'pending-submission.json').exists()


def finish_submission(root):
    (Path(root)/'private-access'/'pending-submission.json').unlink(missing_ok=True)
