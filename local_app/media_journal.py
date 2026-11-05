"""Durable media preparation receipts and idempotent submission reservation.

No prompt/image/video payload is stored. Recovery returns known accepted prompt
IDs, or an explicit interrupted state; it never restarts an inference silently.
"""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

BOOT=uuid.uuid4().hex


def _db(root):
    path=Path(root)/'media-journal.sqlite'
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''CREATE TABLE IF NOT EXISTS requests(
        ticket TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, digest TEXT NOT NULL,
        owner TEXT NOT NULL, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY, ticket TEXT NOT NULL, at REAL NOT NULL, state TEXT NOT NULL);''')
    return db


def reserve(root,body,record):
    key=str(body.get('request_key') or record['ticket'])
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key):raise ValueError('Identifiant de requête invalide.')
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with closing(_db(root)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        previous=db.execute('SELECT digest,record FROM requests WHERE request_key=?',(key,)).fetchone()
        if previous:
            if previous[0]!=digest:raise ValueError('Cette clé de requête appartient à une autre création.')
            return json.loads(previous[1]),False
        db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',(record['ticket'],key,digest,BOOT,json.dumps(record)))
        db.execute('INSERT INTO events(ticket,at,state) VALUES(?,?,?)',(record['ticket'],time.time(),record['state']))
    return record,True


def save(root,record):
    with closing(_db(root)) as db,db:
        old=db.execute('SELECT record FROM requests WHERE ticket=?',(record['ticket'],)).fetchone()
        if not old:return False
        previous=json.loads(old[0])
        record={**previous,**record}
        ids=list(dict.fromkeys((previous.get('prompt_ids') or [])+(record.get('prompt_ids') or [])))
        if ids:record['prompt_ids']=ids
        db.execute('UPDATE requests SET record=? WHERE ticket=?',(json.dumps(record),record['ticket']))
        if json.loads(old[0]).get('state')!=record.get('state'):
            db.execute('INSERT INTO events(ticket,at,state) VALUES(?,?,?)',(record['ticket'],time.time(),record['state']))
    return True


def load(root,ticket):
    # Do not create a database just because an unknown status is requested.
    if not (Path(root)/'media-journal.sqlite').is_file():return None
    with closing(_db(root)) as db:
        row=db.execute('SELECT owner,record FROM requests WHERE ticket=?',(str(ticket or ''),)).fetchone()
    if not row:return None
    record=json.loads(row[1])
    if row[0]!=BOOT and record.get('state')=='preparing':
        record.update(state='queued' if record.get('prompt_ids') else 'error',interrupted=True,
                      recovery='monitor_existing_outputs' if record.get('prompt_ids') else 'operator_review_before_retry')
        if not record.get('prompt_ids'):
            record['error']='Préparation interrompue par un redémarrage. Vérifie la file ComfyUI et les résultats avant de relancer ; aucune inférence redémarrée automatiquement.'
    return record


def accepted(root,ticket,prompt_id):
    record=load(root,ticket)
    if not record:return
    record.setdefault('prompt_ids',[])
    if prompt_id not in record['prompt_ids']:record['prompt_ids'].append(prompt_id)
    save(root,record)


def monitorable(root):
    if not (Path(root)/'media-journal.sqlite').is_file():return []
    with closing(_db(root)) as db:
        rows=db.execute('SELECT record FROM requests ORDER BY rowid DESC LIMIT 1000').fetchall()
    pending=[]
    for row in rows:
        record=json.loads(row[0])
        for pid in record.get('prompt_ids') or []:
            if (record.get('render_states') or {}).get(pid) not in ('done','error','cancelled'):
                pending.append({'prompt_id':pid,'kind':record.get('kind','image'),
                                'started_at':record.get('started_at'), 'private':record.get('private',False)})
    return pending


def render_finished(root,prompt_id,state):
    if not (Path(root)/'media-journal.sqlite').is_file():return
    with closing(_db(root)) as db:
        rows=db.execute('SELECT record FROM requests ORDER BY rowid DESC LIMIT 1000').fetchall()
    for row in rows:
        record=json.loads(row[0])
        if prompt_id in (record.get('prompt_ids') or []):
            states=record.setdefault('render_states',{})
            if states.get(prompt_id)!=state:
                states[prompt_id]=state;save(root,record)
            return
