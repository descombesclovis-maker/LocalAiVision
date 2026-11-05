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
TERMINAL_STATES = ('done', 'error', 'cancelled')


def _db(root):
    path=Path(root)/'media-journal.sqlite'
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=15)
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''CREATE TABLE IF NOT EXISTS requests(
        ticket TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, digest TEXT NOT NULL,
        owner TEXT NOT NULL, record TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY, ticket TEXT NOT NULL, at REAL NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS renders(
        prompt_id TEXT PRIMARY KEY, ticket TEXT NOT NULL, state TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS renders_state ON renders(state);
        CREATE TABLE IF NOT EXISTS journal_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);''')
    # Backfill the existing JSON journal once, atomically. Old requests remain
    # intact; the index avoids a last-N cutoff and repeated full-history scans.
    if not db.execute("SELECT 1 FROM journal_meta WHERE key='renders_v1'").fetchone():
        with db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute("SELECT 1 FROM journal_meta WHERE key='renders_v1'").fetchone():
                for (raw,) in db.execute('SELECT record FROM requests'):
                    _index_renders(db, json.loads(raw))
                db.execute("INSERT INTO journal_meta VALUES('renders_v1','1')")
    return db


def _index_renders(db, record):
    for pid in record.get('prompt_ids') or []:
        state = (record.get('render_states') or {}).get(pid, 'queued')
        db.execute('INSERT INTO renders(prompt_id,ticket,state) VALUES(?,?,?) '
                   'ON CONFLICT(prompt_id) DO UPDATE SET state=excluded.state',
                   (pid, record['ticket'], state))


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
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT record FROM requests WHERE ticket=?',(record['ticket'],)).fetchone()
        if not old:return False
        previous=json.loads(old[0])
        incoming = record
        record={**previous,**incoming}
        states = {**previous.get('render_states', {}), **incoming.get('render_states', {})}
        # Worker snapshots may predate completion/cancellation; terminal receipts
        # cannot be erased or changed by a stale preparation status write.
        states.update({pid:state for pid,state in previous.get('render_states', {}).items()
                       if state in TERMINAL_STATES})
        if states:
            record['render_states'] = states
        ids=list(dict.fromkeys((previous.get('prompt_ids') or [])+(incoming.get('prompt_ids') or [])))
        if ids:record['prompt_ids']=ids
        db.execute('UPDATE requests SET record=? WHERE ticket=?',(json.dumps(record),record['ticket']))
        _index_renders(db, record)
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
    # Merge just the new ID inside save's write transaction. Loading a snapshot
    # here could lose an ID accepted concurrently by another worker/process.
    save(root, {'ticket': ticket, 'prompt_ids': [prompt_id]})


def monitorable(root):
    if not (Path(root)/'media-journal.sqlite').is_file():return []
    with closing(_db(root)) as db:
        rows=db.execute("SELECT renders.prompt_id, requests.record FROM renders "
                        "JOIN requests ON requests.ticket=renders.ticket "
                        "WHERE renders.state NOT IN ('done','error','cancelled')").fetchall()
    pending=[]
    for pid,raw in rows:
        record=json.loads(raw)
        pending.append({'prompt_id':pid,'kind':record.get('kind','image'),
                        'started_at':record.get('started_at'), 'private':record.get('private',False)})
    return pending


def render_finished(root,prompt_id,state):
    if state not in TERMINAL_STATES:
        raise ValueError('État final de génération invalide.')
    if not (Path(root)/'media-journal.sqlite').is_file():return
    with closing(_db(root)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT requests.record FROM renders JOIN requests '
                       'ON requests.ticket=renders.ticket WHERE renders.prompt_id=?',
                       (prompt_id,)).fetchone()
        if not row:return
        record=json.loads(row[0])
        states=record.setdefault('render_states',{})
        if states.get(prompt_id) in TERMINAL_STATES:return
        states[prompt_id]=state
        record.setdefault('render_finished_at',{})[prompt_id]=time.time()
        db.execute('UPDATE requests SET record=? WHERE ticket=?', (json.dumps(record),record['ticket']))
        db.execute('UPDATE renders SET state=? WHERE prompt_id=?',(state,prompt_id))
        db.execute('INSERT INTO events(ticket,at,state) VALUES(?,?,?)',
                   (record['ticket'],time.time(),state))
