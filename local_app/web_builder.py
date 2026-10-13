import base64, io, json, re, shutil, time, uuid, zipfile
from pathlib import Path

ALLOWED_TEXT_EXTENSIONS = {'.html','.htm','.css','.js','.mjs','.cjs','.ts','.tsx','.jsx','.json','.md','.txt','.svg','.toml','.sql','.yml','.yaml','.vue','.svelte','.py','.env','.example'}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PROJECT_FILES = 120

def safe_id(value):
    value = str(value or '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{6,80}', value):
        raise ValueError('Identifiant de projet LocalAiWeb invalide.')
    return value

def safe_rel(value):
    raw = str(value or '').replace('\\\\','/').lstrip('/')
    p = Path(raw)
    if not raw or '..' in p.parts:
        raise ValueError('Chemin de fichier LocalAiWeb invalide.')
    return p

class LocalAiWebStore:
    def __init__(self, root, llm_generate):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.llm_generate = llm_generate

    def project_dir(self, project_id):
        return self.root / safe_id(project_id)

    def meta(self, project_id):
        path = self.project_dir(project_id) / 'project.json'
        if not path.is_file():
            raise FileNotFoundError('Projet LocalAiWeb introuvable.')
        return json.loads(path.read_text(encoding='utf-8'))

    def write_meta(self, project_id, meta):
        root = self.project_dir(project_id)
        root.mkdir(parents=True, exist_ok=True)
        (root / 'project.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    def text_files(self, project_id):
        site = self.project_dir(project_id) / 'site'
        out = {}
        if not site.is_dir():
            return out
        for path in sorted(site.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_TEXT_EXTENSIONS:
                continue
            if len(out) >= MAX_PROJECT_FILES:
                break
            try:
                if path.stat().st_size <= MAX_FILE_BYTES:
                    out[path.relative_to(site).as_posix()] = path.read_text(encoding='utf-8')
            except Exception:
                pass
        return out

    def write_files(self, project_id, files, replace=False):
        if not isinstance(files, dict) or not files:
            raise ValueError('Aucun fichier à enregistrer.')
        if len(files) > MAX_PROJECT_FILES:
            raise ValueError('Trop de fichiers dans ce projet.')
        site = self.project_dir(project_id) / 'site'
        site.mkdir(parents=True, exist_ok=True)
        if replace:
            for old in list(site.rglob('*')):
                if old.is_file() and old.suffix.lower() in ALLOWED_TEXT_EXTENSIONS:
                    try:
                        old.unlink()
                    except OSError:
                        pass
        for rel, body in files.items():
            p = safe_rel(rel)
            if p.suffix.lower() not in ALLOWED_TEXT_EXTENSIONS:
                continue
            text = str(body or '')
            if len(text.encode('utf-8')) > MAX_FILE_BYTES:
                raise ValueError('Fichier trop volumineux : ' + str(rel))
            target = (site / p).resolve()
            if not target.is_relative_to(site.resolve()):
                raise ValueError('Chemin invalide.')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        return self.text_files(project_id)

    def snapshot(self, project_id, label='Version automatique'):
        files = self.text_files(project_id)
        if not files:
            return None
        versions = self.project_dir(project_id) / 'versions'
        versions.mkdir(parents=True, exist_ok=True)
        vid = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
        payload = {'id': vid, 'created_at': time.time(), 'label': str(label or 'Version automatique')[:120], 'files': files}
        (versions / (vid + '.json')).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return {k:v for k,v in payload.items() if k != 'files'}

    def versions(self, project_id):
        root = self.project_dir(project_id) / 'versions'
        out = []
        if root.is_dir():
            for path in root.glob('*.json'):
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    out.append({k:v for k,v in data.items() if k != 'files'})
                except Exception:
                    pass
        return sorted(out, key=lambda x:x.get('created_at',0), reverse=True)

    def assets(self, project_id):
        site = self.project_dir(project_id) / 'site'
        root = site / 'assets'
        out = []
        if root.is_dir():
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    out.append({'path': path.relative_to(site).as_posix(), 'size': path.stat().st_size})
        return out

    def payload(self, project_id):
        return {'project': self.meta(project_id), 'files': self.text_files(project_id),
                'versions': self.versions(project_id), 'assets': self.assets(project_id)}

    def create(self, name='Nouveau projet'):
        pid = 'web-' + uuid.uuid4().hex[:12]
        now = time.time()
        self.write_meta(pid, {'id': pid, 'name': str(name or 'Nouveau projet')[:80], 'created_at': now,
                                 'updated_at': now, 'framework':'Vanilla HTML/CSS/JS', 'status':'local',
                                 'settings': {'quality':'premium','responsive':True,'accessibility':True,
                                              'seo':True,'performance':True,'micro_interactions':True,
                                              'reduced_motion':True,'semantic_html':True,'language':'fr'}})
        starter = {
          'index.html': '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LocalAiWeb</title><link rel="stylesheet" href="styles.css"></head><body><main class="hero"><span class="eyebrow">LOCALAIWEB</span><h1>Ton prochain site commence ici.</h1><p>Décris ton projet dans le chat à droite. LocalAiWeb construira et modifiera les fichiers en direct.</p><button>Commencer</button></main><script src="app.js"></script></body></html>',
          'styles.css': ':root{font-family:Inter,system-ui,sans-serif;color:#f5f3ff;background:#12091f}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 20% 10%,#6d28d955,transparent 35%),#12091f}.hero{min-height:100vh;display:grid;place-content:center;gap:18px;padding:8vw;max-width:1000px}.eyebrow{letter-spacing:.22em;color:#c4b5fd;font-size:12px}h1{font-size:clamp(52px,9vw,118px);line-height:.88;letter-spacing:-.06em;margin:0}p{max-width:680px;color:#c4b5d4;font-size:19px;line-height:1.6}button{width:max-content;border:0;border-radius:999px;background:#8b5cf6;color:#fff;padding:14px 22px;font-weight:700}',
          'app.js': 'console.log("LocalAiWeb ready");'
        }
        self.write_files(pid, starter, replace=True)
        return self.payload(pid)

    def list_projects(self):
        out = []
        for root in self.root.iterdir() if self.root.is_dir() else []:
            if root.is_dir():
                try: out.append(json.loads((root/'project.json').read_text(encoding='utf-8')))
                except Exception: pass
        return sorted(out, key=lambda x:x.get('updated_at',0), reverse=True)

    def _extract_json(self, text):
        raw = (text or '').strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*','',raw,flags=re.I)
            raw = re.sub(r'\s*```$','',raw)
        a,b = raw.find('{'), raw.rfind('}')
        if a < 0 or b <= a:
            raise ValueError("Le modèle n'a pas renvoyé le projet au format JSON attendu.")
        return json.loads(raw[a:b+1])

    def generate(self, project_id, prompt):
        prompt = str(prompt or '').strip()
        if not prompt: raise ValueError('Décris la modification ou le site à créer.')
        current = self.text_files(project_id)
        self.snapshot(project_id, 'Avant : ' + prompt[:80])
        context = json.dumps(current, ensure_ascii=False)
        if len(context) > 90000: context = context[:90000]
        project_settings = self.meta(project_id).get('settings') or {}
        requirements = (
          ' Project requirements: premium visual quality; responsive desktop/tablet/mobile; '
          'semantic HTML; accessible keyboard focus; useful alt text; SEO title and meta description; '
          'performance-minded assets; prefers-reduced-motion support; polished hover/focus states; '
          'no TODO, FIXME or placeholder copy in the final result. '
          'Language=' + str(project_settings.get('language','fr')) + '. '
          'Quality=' + str(project_settings.get('quality','premium')) + '. '
        )
        system = (
          'You are LocalAiWeb, a senior product designer and full-stack front-end engineer. ' + requirements +
          'Build exceptionally polished, distinctive, production-quality responsive websites. '
          'Prioritize typography, spacing, interaction design, accessibility, responsive behavior, micro-interactions and coherent visual systems. '
          'Return ONLY valid JSON with this shape: {"summary":"short change summary","files":{"index.html":"...","styles.css":"...","app.js":"..."}}. '
          'You may add HTML/CSS/JS/JSON/SVG files when useful. Preserve requested existing behavior. '
          'Use relative local paths. Do not emit markdown fences. For images already present under assets/, reference them. '
          'Unless explicitly asked for a framework, produce dependency-free HTML/CSS/JS that runs immediately in preview.'
        )
        answer = self.llm_generate(system, context, prompt)
        parsed = self._extract_json(answer)
        files = parsed.get('files')
        if not isinstance(files, dict) or 'index.html' not in files:
            raise ValueError("Le modèle n'a pas produit un index.html exploitable.")
        saved = self.write_files(project_id, files, replace=False)
        meta = self.meta(project_id); meta['updated_at']=time.time(); meta['last_summary']=str(parsed.get('summary') or prompt)[:240]
        self.write_meta(project_id, meta)
        return {'ok':True,'summary':meta['last_summary'],'project':meta,'files':saved,'versions':self.versions(project_id)}

    def update_settings(self, project_id, patch):
        meta = self.meta(project_id)
        settings = dict(meta.get('settings') or {})
        allowed = {'quality','responsive','accessibility','seo','performance','micro_interactions',
                   'reduced_motion','semantic_html','language'}
        for key, value in (patch or {}).items():
            if key in allowed:
                settings[key] = value
        meta['settings'] = settings
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        return self.payload(project_id)

    def preflight(self, project_id):
        files = self.text_files(project_id)
        html = files.get('index.html','')
        css = '\n'.join(v for k,v in files.items() if k.endswith('.css'))
        checks = [
            {'id':'index','label':'Page principale','ok':bool(html.strip()),'weight':12},
            {'id':'viewport','label':'Responsive viewport','ok':('name="viewport"' in html or "name='viewport'" in html),'weight':8},
            {'id':'title','label':'Titre SEO','ok':bool(re.search(r'<title>[^<]{2,}</title>',html,re.I)),'weight':8},
            {'id':'description','label':'Meta description','ok':bool(re.search(r'name=["\\\']description["\\\']',html,re.I)),'weight':8},
            {'id':'semantic','label':'HTML sémantique','ok':any(tag in html.lower() for tag in ('<main','<header','<nav','<section','<footer')),'weight':8},
            {'id':'responsive_css','label':'CSS responsive','ok':('@media' in css or 'clamp(' in css),'weight':10},
            {'id':'focus','label':'Focus clavier','ok':(':focus' in css or ':focus-visible' in css),'weight':7},
            {'id':'reduced_motion','label':'Reduced motion','ok':('prefers-reduced-motion' in css),'weight':5},
        ]
        total = sum(x['weight'] for x in checks)
        score = round(100 * sum(x['weight'] for x in checks if x['ok']) / total) if total else 0
        blockers = [x for x in checks if not x['ok'] and x['weight'] >= 8]
        return {'ok': score >= 80 and not blockers, 'score': score, 'checks': checks, 'blockers': blockers}

    def restore(self, project_id, version_id):
        path = self.project_dir(project_id) / 'versions' / (safe_id(version_id)+'.json')
        if not path.is_file(): raise FileNotFoundError('Version introuvable.')
        self.snapshot(project_id, 'Avant restauration')
        data = json.loads(path.read_text(encoding='utf-8'))
        self.write_files(project_id, data.get('files') or {}, replace=True)
        meta=self.meta(project_id);meta['updated_at']=time.time();meta['last_summary']='Version restaurée';self.write_meta(project_id,meta)
        return self.payload(project_id)

    def export_zip(self, project_id):
        root = self.project_dir(project_id) / 'site'
        memory = io.BytesIO()
        with zipfile.ZipFile(memory,'w',zipfile.ZIP_DEFLATED) as archive:
            for path in root.rglob('*') if root.is_dir() else []:
                if path.is_file(): archive.write(path,path.relative_to(root).as_posix())
        return memory.getvalue()

    def save_asset(self, project_id, name, data_url):
        name = Path(str(name or 'asset.bin')).name
        try: data = base64.b64decode(str(data_url).split(',',1)[-1], validate=True)
        except Exception: raise ValueError('Asset invalide.')
        if len(data) > 20*1024*1024: raise ValueError('Asset limité à 20 Mo.')
        target=self.project_dir(project_id)/'site'/'assets'/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        meta=self.meta(project_id);meta['updated_at']=time.time();self.write_meta(project_id,meta)
        return {'ok':True,'path':'assets/'+name,'size':len(data)}
