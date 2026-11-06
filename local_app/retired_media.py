"""Privacy compatibility for a removed workspace. No unlock, session or generation.

Original indexes and personal files are read only. An independent SQLite index
admits public media explicitly identified by the trusted local UI or a public
render receipt. Unknown legacy outputs are never made public by an upgrade.
"""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path


def file_key(filename,subfolder='',kind='output'):
    def valid(value):
        raw=str(value or '').replace('\\','/')
        if raw.startswith('/') or ':' in raw or '\x00' in raw or '..' in Path(raw).parts:raise ValueError('Chemin média invalide.')
        return raw
    name=valid(filename);folder=valid(subfolder)
    if not name or '/' in name or kind not in ('input','output','temp'):raise ValueError('Média invalide.')
    return kind+'/'+folder+'/'+name


def legacy(root):
    p=Path(root)/'private-access'/'ownership.json'
    if not p.exists():return {'jobs':{},'files':{}}
    d=json.loads(p.read_text(encoding='utf-8'))
    if d.get('schema')!=1 or not isinstance(d.get('jobs'),dict) or not isinstance(d.get('files'),dict):raise ValueError('Inventaire historique illisible ; accès refusé.')
    return d


def _db(root):
    folder=Path(root)/'retired-records';folder.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(folder/'access.sqlite',timeout=30)
    db.executescript('CREATE TABLE IF NOT EXISTS files(key TEXT PRIMARY KEY,retired INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,retired INTEGER NOT NULL);')
    return db


def is_retired_job(root,pid):
    if str(pid) in legacy(root)['jobs']:return True
    with closing(_db(root)) as db:
        row=db.execute('SELECT retired FROM jobs WHERE id=?',(str(pid),)).fetchone()
        return bool(row and row[0])


def allowed_job(root,pid):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',str(pid or '')) or is_retired_job(root,pid):return False
    receipt=Path(root)/'public-provenance'/(pid+'.json')
    if receipt.is_file():return True
    with closing(_db(root)) as db:
        return db.execute('SELECT 1 FROM jobs WHERE id=? AND retired=0',(pid,)).fetchone() is not None


def allowed_file(root,filename,subfolder='',kind='output'):
    key=file_key(filename,subfolder,kind)
    if key in legacy(root)['files']:return False
    with closing(_db(root)) as db:
        row=db.execute('SELECT retired FROM files WHERE key=?',(key,)).fetchone()
        return row is not None and row[0]==0


def classify(root,public,retired,public_jobs=None,retired_jobs=None):
    def keys(rows):
        if not isinstance(rows,list) or len(rows)>20000:raise ValueError('Inventaire historique invalide.')
        return [file_key(x.get('filename'),x.get('subfolder',''),x.get('type','output')) for x in rows]
    good,bad=keys(public),keys(retired)
    old=legacy(root);bad=set(bad)|set(old['files'])
    jobs_good=list(public_jobs or []);jobs_bad=list(retired_jobs or [])+list(old['jobs'])
    if len(jobs_good)+len(jobs_bad)>40000 or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',str(x)) for x in jobs_good+jobs_bad):raise ValueError('Identifiant historique invalide.')
    with closing(_db(root)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        for key in good:
            if key not in bad:db.execute('INSERT OR IGNORE INTO files VALUES(?,0)',(key,))
        for key in bad:db.execute('INSERT OR REPLACE INTO files VALUES(?,1)',(key,))
        for pid in jobs_good:
            if pid not in jobs_bad:db.execute('INSERT OR IGNORE INTO jobs VALUES(?,0)',(pid,))
        for pid in jobs_bad:db.execute('INSERT OR REPLACE INTO jobs VALUES(?,1)',(pid,))
    return {'public_indexed':len(good),'retired_preserved':len(bad)}


def register_outputs(root,pid,info):
    if not allowed_job(root,pid):return
    files=[x for node in info.get('outputs',{}).values() for kind in ('images','videos','gifs') for x in node.get(kind,[]) if x.get('filename')]
    classify(root,files,[],[pid])
