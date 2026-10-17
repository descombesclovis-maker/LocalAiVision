"""Windows Codex may report success despite a read-only workspace.
Use a bounded, validated JSON file bundle as a safe fallback.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

ALLOWED={'.html','.htm','.css','.js','.mjs','.jsx','.ts','.tsx','.json','.svg','.md','.vue','.svelte'}
SKIP={'node_modules','.git','.next','.localaiweb-qa','.vercel','.cache','__pycache__','dist','build','assets'}
APP={'.html','.css','.js','.mjs','.jsx','.ts','.tsx','.vue','.svelte'}
PLACEHOLDER='La prévisualisation devrait apparaitre ici.'
MAX_OUTPUT=4_000_000

def snapshot(site):
    root=Path(site)
    result={}
    if not root.is_dir():return result
    for file in root.rglob('*'):
        if not file.is_file():continue
        rel=file.relative_to(root)
        if any(p in SKIP or p.startswith('.') for p in rel.parts):continue
        if file.suffix.lower() not in ALLOWED:continue
        try: result[rel.as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
        except OSError:pass
    return result

def changed(before,after):
    return sorted(k for k,v in after.items() if before.get(k)!=v)

def changed_app(before,after):
    return any(PurePosixPath(p).suffix.lower() in APP for p in changed(before,after))

def placeholder(site):
    index=Path(site)/'index.html'
    if not index.is_file():return True
    try: content=index.read_text(encoding='utf-8')
    except (UnicodeError,OSError):return True
    return len(content)<100 or PLACEHOLDER in content

def parse_files(text):
    raw=str(text or '').strip()
    if not raw or len(raw)>MAX_OUTPUT:raise ValueError('Codex n’a pas fourni de fichiers exploitables.')
    fence=chr(96)*3
    if raw.startswith(fence):
        raw=re.sub(r'^' + fence + r'(?:json)?\s*','',raw,flags=re.I)
        raw=re.sub(r'\s*' + fence + r'$','',raw)
    try: value=json.loads(raw)
    except ValueError:
        first,last=raw.find('{'),raw.rfind('}')
        if first<0 or last<=first:raise ValueError('Codex n’a pas renvoyé de fichiers JSON.') from None
        try:value=json.loads(raw[first:last+1])
        except ValueError:raise ValueError('Réponse Codex JSON invalide.') from None
    if not isinstance(value,dict) or not isinstance(value.get('files'),dict):
        raise ValueError('Réponse Codex sans objet « files ».')
    return value['files']

def valid_path(root,name):
    if not isinstance(name,str) or not name or len(name)>260:
        raise ValueError('Nom de fichier Codex incorrect.')
    if name.startswith(('/','\\')) or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('Chemin de fichier Codex interdit.')
    parts=name.split('/')
    if any(not p or p in ('.','..') or p.startswith('.') or p in SKIP for p in parts):
        raise ValueError('Chemin Codex non autorisé.')
    if PurePosixPath(name).suffix.lower() not in ALLOWED:
        raise ValueError('Extension de fichier Codex non autorisée.')
    dest=(root/name).resolve()
    if not dest.is_relative_to(root):raise ValueError('Fichier Codex hors du projet.')
    return dest

def apply_bundle(site,text):
    root=Path(site).resolve()
    files=parse_files(text)
    if not files or len(files)>85:raise ValueError('Nombre de fichiers Codex invalide.')
    prepared={}
    total=0
    for name,body in files.items():
        dest=valid_path(root,name)
        if not isinstance(body,str):raise ValueError('Contenu Codex non textuel.')
        data=body.encode('utf-8')
        total+=len(data)
        if not data or len(data)>600_000 or total>3_500_000:
            raise ValueError('Fichier Codex vide ou trop volumineux.')
        prepared[dest]=data
    index=prepared.get(root/'index.html')
    if index is None and not (root/'index.html').is_file():
        raise ValueError('Le site ne contient aucun index.html.')
    if index is not None and (len(index)<100 or PLACEHOLDER.encode('utf-8') in index):
        raise ValueError('Codex a renvoyé un écran d’attente incomplet.')
    for dest,data in prepared.items():
        dest.parent.mkdir(parents=True,exist_ok=True)
        pending=dest.with_name(dest.name+'.localaiweb-pending')
        try:
            pending.write_bytes(data)
            os.replace(pending,dest)
        finally:
            pending.unlink(missing_ok=True)
    return [p.relative_to(root).as_posix() for p in prepared]

def structured_prompt(prompt,site):
    excerpts=[];budget=16000
    for name in sorted(snapshot(site)):
        if budget<=0:break
        try: src=(Path(site)/name).read_text(encoding='utf-8')
        except (OSError,UnicodeError):continue
        text=src[:min(budget,3500)]
        excerpts.append('FILE '+name+':\n'+text);budget-=len(text)
    return (
        'The Windows coding workspace is read-only. Return ONLY a single JSON object '
        'with a top-level key "files" mapping project-relative filenames to FULL '
        'UTF-8 text. No markdown, terminal commands, patches, commentary, or .env files. '
        'Build a complete premium responsive website. Supply index.html, styles.css, '
        'app.js or all source files for a working Vite app. Respect the brand/colors and '
        'functionality. Reuse available product images. No fake product photos. '
        'Return at most 2 MB and only changed or new files.\n\n'
        'USER REQUEST:\n'+str(prompt)[:26000]+
        '\n\nEXISTING PROJECT EXCERPTS:\n'+'\n\n'.join(excerpts)
    )
