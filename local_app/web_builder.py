import base64, io, json, re, shutil, time, uuid, zipfile
from pathlib import Path
from local_app import web_briefing

ALLOWED_TEXT_EXTENSIONS = {'.html','.htm','.css','.js','.mjs','.cjs','.ts','.tsx','.jsx','.json','.md','.txt','.svg','.toml','.sql','.yml','.yaml','.vue','.svelte','.py','.env','.example'}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_PROJECT_FILES = 120
PRIVATE_NAMES = {'.env', '.env.local', '.env.production', '.env.development'}
IGNORED_DIRS = {'.git', '.vercel', 'node_modules', '.next', 'dist', 'build', '__pycache__', '.localaiweb-qa'}


# Original LocalAiWeb presets inspired by common website/app categories (not third-party copies).
SITE_KINDS = {
 'auto':('Automatique','Infer a suitable website or app type from the user request.'),
 'website':('Site vitrine','Create a clear, fast, content-focused business website.'),
 'landing':('Landing page','Create a persuasive landing page with a clear conversion goal.'),
 'store':('Boutique','Design a functional storefront UI; never pretend checkout or inventory is connected if it is not.'),
 'portfolio':('Portfolio','Use polished case studies and expressive but accessible layouts.'),
 'saas':('SaaS','Design real product flows, responsive screens, empty and error states.'),
 'dashboard':('Dashboard','Use legible data visualizations, filters and meaningful sample data explicitly labeled.'),
 'ai_app':('Application IA','Build usable AI tool interfaces with loading and error states; avoid simulating unavailable providers.'),
 'mobile':('Application mobile web','Prioritize touch-first and PWA-friendly patterns; do not claim native iOS or Android builds.'),
 'extension':('Extension navigateur','Scaffold a browser extension and manifest as needed; browser-extension runtime is not available in the website preview.'),
 'editorial':('Editorial / magazine','Use long-form storytelling, photography, clear visual hierarchy and legible typography.'),
 'event':('Evenement / campagne','Create an expressive campaign or event site with schedules and clear calls to action.')
}
ART_DIRECTIONS = {
 'auto':('Libre / selon la demande','Choose the best direction for product, target audience and brand. Do not default to 3D.'),
 'minimal':('Sobre / essentiel','Prioritize clarity, restrained typography, speed and accessibility over decorative motion.'),
 'professional':('Professionnel premium','Use refined typography, polished components, intentional spacing and high-quality interaction design.'),
 'editorial':('Editorial artistique','Use typographic storytelling, art direction and asymmetric compositions while staying legible.'),
 'cinematic':('Cinematique','Use scroll-linked narrative, carefully staged transitions and graceful static fallbacks.'),
 'spatial3d':('3D produit immersive','If real 3D assets exist, implement interactive product scenes, cinematic camera motion, loading states and mobile/reduced-motion fallbacks. Never invent model assets or claim a 3D reconstruction exists without source data.'),
 'experimental':('Experimental / creatif','Use distinctive compositions and original motion without sacrificing usability or accessibility.')
}

def generation_direction(settings, request=''):
    """Consistent site category and visual direction for local and connected agents."""
    settings = settings or {}
    kind = str(settings.get('site_kind') or 'auto')
    art = str(settings.get('art_direction') or 'auto')
    if kind not in SITE_KINDS: kind = 'auto'
    if art not in ART_DIRECTIONS: art = 'auto'
    return (
       'Category: ' + SITE_KINDS[kind][0] + '. ' + SITE_KINDS[kind][1] + ' '
       'Art direction: ' + ART_DIRECTIONS[art][0] + '. ' + ART_DIRECTIONS[art][1] + ' '
       'Every site type can use every artistic direction: immersive experiences can present ANY product or industry. '
       'Plain and simple sites must remain just as valid as spectacular ones. '
       'Respect explicit user preferences, prioritize real interactions and do not copy proprietary third-party templates. '
       'If the user asks for 3D, use actual Three.js r186 or compatible WebGL rendering with GLTFLoader for supplied GLB assets, '
       'scroll-linked camera/object choreography, physically based material response (metalness, roughness, clearcoat), ' 
       'HDRI or PMREM studio environment lighting, realistic reflections and shadows, loading/error states, adaptive rendering resolution and mobile fallback. '
       'Do not replace real 3D interaction with a screenshot or pre-rendered video; do not invent a product model. '
       'If modifying an existing 3D project, preserve its scene, GLB loading, quality.mjs adaptive renderer, HDR lighting and user assets unless explicitly told otherwise. '
       'Use compressed glTF textures and geometry when available, prioritize a stable 60 FPS on desktop and 30 FPS on mobile, '
       'and reduce expensive effects before sacrificing interactivity. '
       'Keep animations accessible and respect prefers-reduced-motion. '
       'Never fake working integrations or external services.'
    )

def safe_id(value):
    value = str(value or '')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{6,80}', value):
        raise ValueError('Identifiant de projet LocalAiWeb invalide.')
    return value

def safe_rel(value):
    raw = str(value or '').replace(chr(92),'/').lstrip('/')
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
            rel_parts = path.relative_to(site).parts if path.exists() else ()
            if any(part in IGNORED_DIRS for part in rel_parts):
                continue
            if path.name in PRIVATE_NAMES:
                continue
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
                try:
                    rel_parts = old.relative_to(site).parts
                except Exception:
                    rel_parts = ()
                if any(part in IGNORED_DIRS for part in rel_parts) or old.name in PRIVATE_NAMES:
                    continue
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

    def chat_history(self, project_id):
        path = self.project_dir(project_id) / 'chat.json'
        if not path.is_file():
            return []
        try:
            rows = json.loads(path.read_text(encoding='utf-8'))
            return rows if isinstance(rows, list) else []
        except Exception:
            return []

    def append_chat(self, project_id, role, text):
        rows = self.chat_history(project_id)
        rows.append({'role': str(role or 'assistant'), 'text': str(text or '')[:12000], 'time': time.time()})
        rows = rows[-200:]
        path = self.project_dir(project_id) / 'chat.json'
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        return rows

    def payload(self, project_id):
        return {'project': self.meta(project_id), 'files': self.text_files(project_id),
                'versions': self.versions(project_id), 'assets': self.assets(project_id),
                'chat': self.chat_history(project_id)}

    def create(self, name='Nouveau projet', template='default'):
        if template not in ('default', 'cinematic3d'):
            raise ValueError('Modèle de projet inconnu.')
        pid = 'web-' + uuid.uuid4().hex[:12]
        now = time.time()
        self.write_meta(pid, {'id': pid, 'name': str(name or 'Nouveau projet')[:80], 'created_at': now,
                                 'updated_at': now, 'framework':'Vanilla HTML/CSS/JS', 'status':'local',
                                 'settings': {'quality':'premium','responsive':True,'accessibility':True,
                                              'seo':True,'performance':True,'micro_interactions':True,
                                              'reduced_motion':True,'semantic_html':True,'language':'fr',
                                              'site_kind':'landing' if template == 'cinematic3d' else 'auto',
                                              'art_direction':'spatial3d' if template == 'cinematic3d' else 'auto'},
                                 'template':template})
        starter = {
          'index.html': '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prévisualisation LocalAiWeb</title><link rel="stylesheet" href="styles.css"></head><body><main class="hero"><p>La prévisualisation devrait apparaitre ici.</p></main></body></html>',
          'styles.css': 'html,body{margin:0;min-height:100%;font-family:Inter,system-ui,sans-serif;background:#0e0e12;color:#bcbac7}main{min-height:100vh;display:grid;place-items:center;padding:24px;text-align:center}p{font-size:clamp(16px,2vw,22px);font-weight:500}@media(max-width:600px){p{font-size:16px}}',
          'app.js': '// L’IA remplacera le placeholder au premier rendu.',
          '.gitignore': '.env\n.env.local\n.env.production\n.env.development\n.vercel\nnode_modules\n.next\ndist\nbuild\n.localaiweb-qa\n',
          '.env.example': '# Variables publiques du projet uniquement. Ne committez jamais de secrets.\n'
        }
        if template == 'cinematic3d':
            root = Path(__file__).resolve().parent / 'web' / 'templates' / 'cinematic3d'
            for file_name in ('index.html', 'styles.css', 'app.js', 'quality.mjs', 'README.md'):
                starter[file_name] = (root / file_name).read_text(encoding='utf-8')
        self.write_files(pid, starter, replace=True)
        return self.payload(pid)

    def delete_file(self, project_id, rel):
        p = safe_rel(rel)
        site = (self.project_dir(project_id) / 'site').resolve()
        target = (site / p).resolve()
        if not target.is_relative_to(site):
            raise ValueError('Chemin invalide.')
        if target.name in PRIVATE_NAMES or any(part in IGNORED_DIRS for part in target.relative_to(site).parts):
            raise ValueError('Ce fichier système ne peut pas être supprimé depuis l’éditeur.')
        self.snapshot(project_id, 'Avant suppression de ' + p.as_posix())
        if target.is_file():
            target.unlink()
        meta = self.meta(project_id); meta['updated_at'] = time.time(); self.write_meta(project_id, meta)
        return self.payload(project_id)

    def rename_file(self, project_id, old_rel, new_rel):
        old = safe_rel(old_rel); new = safe_rel(new_rel)
        site = (self.project_dir(project_id) / 'site').resolve()
        source = (site / old).resolve(); target = (site / new).resolve()
        if not source.is_relative_to(site) or not target.is_relative_to(site):
            raise ValueError('Chemin invalide.')
        if not source.is_file():
            raise FileNotFoundError('Fichier introuvable.')
        if target.exists():
            raise ValueError('Un fichier existe déjà avec ce nom.')
        if target.name in PRIVATE_NAMES or any(part in IGNORED_DIRS for part in target.relative_to(site).parts):
            raise ValueError('Nom réservé.')
        self.snapshot(project_id, 'Avant renommage de ' + old.as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)
        meta = self.meta(project_id); meta['updated_at'] = time.time(); self.write_meta(project_id, meta)
        return self.payload(project_id)

    def rename_project(self, project_id, name):
        meta = self.meta(project_id)
        meta['name'] = str(name or 'Projet LocalAiWeb')[:80]
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        return self.payload(project_id)

    def delete_project(self, project_id):
        root = self.project_dir(project_id)
        if root.is_dir():
            shutil.rmtree(root)
        return {'ok': True, 'id': project_id}

    def duplicate_project(self, project_id, name=None):
        source = self.project_dir(project_id)
        if not source.is_dir():
            raise FileNotFoundError('Projet LocalAiWeb introuvable.')
        new_id = 'web-' + uuid.uuid4().hex[:12]
        target = self.project_dir(new_id)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git','.vercel','node_modules','.next','dist','build',
                                                                  '.env','.env.local','.env.production','.env.development'))
        meta = json.loads((target / 'project.json').read_text(encoding='utf-8'))
        now = time.time()
        meta['id'] = new_id
        meta['name'] = str(name or (meta.get('name','Projet') + ' — copie'))[:80]
        meta['created_at'] = now
        meta['updated_at'] = now
        meta['status'] = 'local'
        meta['deployment'] = {'github_repo':'','github_branch':'main','github_private':True,'supabase_ref':'','vercel_target':'production','production_url':'','preview_url':'','custom_domain':'','last_deployed_at':0}
        # Keep design/settings in a duplicate but clear deployment credentials/targets.
        self.write_meta(new_id, meta)
        versions = target / 'versions'
        if versions.is_dir():
            shutil.rmtree(versions)
        return self.payload(new_id)

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

    def brief_status(self, project_id):
        meta = self.meta(project_id)
        plan = meta.get('generation_plan') or {}
        return {'plan': plan, 'question': web_briefing.pending_question(plan) if plan else None,
                'ready': bool(plan.get('ready'))}

    def brief_begin(self, project_id, prompt):
        request = str(prompt or '').strip()
        if not request: raise ValueError('Décris le site souhaité.')
        plan = web_briefing.new_plan(request)
        meta = self.meta(project_id)
        meta['generation_plan'] = plan
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        self.append_chat(project_id, 'user', request)
        if plan['questions']:
            q = web_briefing.pending_question(plan)
            self.append_chat(project_id, 'assistant', q['question'])
        return {'plan':plan, 'question':web_briefing.pending_question(plan), 'ready':plan['ready']}

    def brief_answer(self, project_id, response):
        meta = self.meta(project_id)
        plan = meta.get('generation_plan') or {}
        if not plan: raise ValueError('Aucun questionnaire en cours.')
        web_briefing.answer_plan(plan, response)
        meta['generation_plan'] = plan
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        self.append_chat(project_id, 'user', response)
        question = web_briefing.pending_question(plan)
        if question: self.append_chat(project_id, 'assistant', question['question'])
        return {'plan':plan, 'question':question, 'ready':plan['ready'],
                'prompt':web_briefing.full_prompt(plan) if plan['ready'] else None}

    def generate(self, project_id, prompt, agent_context=''):
        prompt = str(prompt or '').strip()
        if not prompt: raise ValueError('Décris la modification ou le site à créer.')
        self.append_chat(project_id, 'user', prompt)
        current = self.text_files(project_id)
        self.snapshot(project_id, 'Avant : ' + prompt[:80])
        context = json.dumps({'files': current, 'assets': self.assets(project_id)}, ensure_ascii=False)
        if len(context) > 90000: context = context[:90000]
        project_meta = self.meta(project_id)
        from local_app import web_content_contract
        full_brief = web_content_contract.project_request(self, project_id, prompt)
        exact_spec = web_content_contract.specification(full_brief, project_meta.get('name',''))
        project_settings = project_meta.get('settings') or {}
        project_design = project_meta.get('design') or {}
        requirements = (
          ' Project requirements: premium visual quality; responsive desktop/tablet/mobile; '
          'semantic HTML; accessible keyboard focus; useful alt text; SEO title and meta description; '
          'performance-minded assets; prefers-reduced-motion support; polished hover/focus states; '
          'no TODO, FIXME or placeholder copy in the final result. '
          'Language=' + str(project_settings.get('language','fr')) + '. '
          'Quality=' + str(project_settings.get('quality','premium')) + '. '
          + generation_direction(project_settings, prompt) + ' '
          'Design tokens: brand=' + str(project_design.get('brand','#7c3aed')) +
          ', accent=' + str(project_design.get('accent','#a78bfa')) +
          ', background=' + str(project_design.get('background','#0f0718')) +
          ', text=' + str(project_design.get('text','#f7f2ff')) +
          ', font=' + str(project_design.get('font','Inter,system-ui,sans-serif')) +
          ', radius=' + str(project_design.get('radius',14)) + 'px. '
        )
        system = (
          'You are LocalAiWeb, a senior product designer and full-stack front-end engineer. ' + requirements +
          'Build complete, distinctive, high-quality responsive websites of ANY category: minimal, editorial, '
          'e-commerce, SaaS, dashboards, applications, landing pages and cinematic WebGL experiences. '
          'Match the explicit level of complexity: a simple brief deserves a beautifully simple website; '
          'an immersive brief deserves serious art direction, real 3D scenes when justified, precise motion and visual storytelling. '
          'Treat the user conversation as an iterative specification: implement their requested pages and interactions, '
          'retain all previously approved features and avoid replacing the full site with a mockup. '
          'Do not claim a live payment, database, account system or reservation when its provider is not connected. '
          'Prioritize typography, spacing, interaction design, accessibility, responsive behavior, micro-interactions and coherent visual systems. '
          'Return ONLY valid JSON with this shape: {"summary":"short change summary","files":{"index.html":"...","styles.css":"...","app.js":"..."}}. '
          'You may add HTML/CSS/JS/JSON/SVG files when useful. Preserve requested existing behavior. '
          'Use relative local paths. Do not emit markdown fences. For images already present under assets/, reference them. '
          'Unless a 3D experience or framework is requested, produce dependency-free HTML/CSS/JS that runs immediately in preview. '
          'For 3D scenes, Three.js ES modules are supported via version-pinned import maps and actual GLTFLoader, with a CSS fallback when WebGL or CDN is unavailable.'
        )
        # The user's explicitly stated requirements outrank default purple design tokens.
        system += (
            ' CRITICAL: Respect the exact user brief ABOVE all defaults. Never recolor a blue/green '
            'brand to violet; obey requested business name, pages, taxonomy, content, search behavior '
            'and layout. Deliver a fully styled, deliberately art-directed design on the FIRST generation, '
            'not a flat wireframe. Real working interactions: search filters products, categories navigate, '
            'buttons have destinations, forms validate. No fake payment or auth integrations. '
            'Use photography only when legitimate supplied assets exist; otherwise design elegant CSS/SVG '
            'visuals or original Three.js geometry, never pretend to show a real product photo. '
            'A simple website should be expertly simple, not forced into 3D. '
            'Include meaningful visual hierarchy, responsive grids, professional typography, '
            'responsive navigation, polished original copy, and coherent page composition.'
        )
        system += '\n' + web_content_contract.agent_instructions(exact_spec)
        if agent_context:
            system += '\nADDITIONAL AUTOMATED CREATIVE ASSET MANIFEST:\n' + str(agent_context)[:12000]
        answer = self.llm_generate(system, context, prompt)
        parsed = self._extract_json(answer)
        files = parsed.get('files')
        if not isinstance(files, dict) or 'index.html' not in files:
            raise ValueError("Le modèle n'a pas produit un index.html exploitable.")
        # Hold candidate in memory until structural and contractual checks pass.
        contract = web_briefing.audit(files, full_brief)
        contract.extend(web_content_contract.check(files,exact_spec))
        if contract:
            fail_text = '\n'.join('- '+x['fix'] for x in contract)
            repair_request = (
                'FIRST ATTEMPT FAILED THE CUSTOMER CONTRACT. Repair all issues. '
                'Return the full corrected JSON file set, not a description.\n' + fail_text
                + '\nOriginal customer request: '+prompt
            )
            revised = self.llm_generate(system, json.dumps({'files':files,'assets':self.assets(project_id)},ensure_ascii=False)[:90000],repair_request)
            candidate = self._extract_json(revised).get('files')
            if isinstance(candidate,dict) and 'index.html' in candidate:
                files.update(candidate)
                contract = web_briefing.audit(files,full_brief)
                contract.extend(web_content_contract.check(files,exact_spec))
        if contract:
            reason = '; '.join(x['id'] for x in contract[:6])
            raise ValueError('Qualité insuffisante : '+reason+'. Aucune maquette non conforme n’a été appliquée. Précise les ressources ou réessaie.')
        saved = self.write_files(project_id, files, replace=False)
        meta = self.meta(project_id)
        quality = self.preflight(project_id)
        repaired = False
        if str((meta.get('settings') or {}).get('quality','premium')) == 'premium' and not quality.get('ok'):
            failed = ', '.join(x.get('label','') for x in quality.get('checks',[]) if not x.get('ok'))
            repair_request = (
                'Quality verification failed on: ' + failed + '. '
                'Repair the project without removing working features. Ensure production-ready SEO, accessibility, '
                'responsive behavior, keyboard focus, semantic HTML, valid local asset references and reduced-motion support.'
            )
            repair_context = json.dumps({'files': self.text_files(project_id), 'assets': self.assets(project_id)}, ensure_ascii=False)
            repair_answer = self.llm_generate(system, repair_context[:90000], repair_request)
            repair_parsed = self._extract_json(repair_answer)
            repair_files = repair_parsed.get('files')
            if isinstance(repair_files, dict) and 'index.html' in repair_files:
                saved = self.write_files(project_id, repair_files, replace=False)
                repaired = True
                quality = self.preflight(project_id)
        meta = self.meta(project_id)
        meta['updated_at']=time.time()
        meta['last_summary']=str(parsed.get('summary') or prompt)[:240]
        meta['last_quality_score']=quality.get('score')
        self.write_meta(project_id, meta)
        self.append_chat(project_id, 'assistant', meta['last_summary'])
        return {'ok':True,'summary':meta['last_summary'],'project':meta,'files':saved,
                'versions':self.versions(project_id),'assets':self.assets(project_id),
                'chat':self.chat_history(project_id),'quality':quality,'auto_repaired':repaired}

    def apply_design(self, project_id, design):
        meta = self.meta(project_id)
        current = dict(meta.get('design') or {})
        allowed = {'brand','accent','background','text','font','radius'}
        for key, value in (design or {}).items():
            if key not in allowed:
                continue
            if key in {'brand','accent','background','text'}:
                value = str(value or '').strip()
                if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                    raise ValueError('Couleur invalide : ' + key)
            elif key == 'radius':
                value = max(0, min(int(value), 48))
            else:
                value = str(value or '')[:120]
            current[key] = value

        self.snapshot(project_id, 'Avant modification du design system')
        files = self.text_files(project_id)
        css_path = 'styles.css' if 'styles.css' in files else next((k for k in files if k.endswith('.css')), 'styles.css')
        css = files.get(css_path, '')
        block = (
            ':root{\n'
            '  --law-brand:' + current.get('brand','#7c3aed') + ';\n'
            '  --law-accent:' + current.get('accent','#a78bfa') + ';\n'
            '  --law-bg:' + current.get('background','#0f0718') + ';\n'
            '  --law-text:' + current.get('text','#f7f2ff') + ';\n'
            '  --law-radius:' + str(current.get('radius',14)) + 'px;\n'
            '  --law-font:' + current.get('font','Inter,system-ui,sans-serif') + ';\n'
            '}\n'
            'html,body{font-family:var(--law-font);}\n'
            'body{background-color:var(--law-bg);color:var(--law-text);}\n'
            'a{color:var(--law-accent);}\n'
            ':where(button,.btn,[class*="button"],[class*="btn"]){border-radius:var(--law-radius);}\n'
            ':where(.primary,.cta,[data-variant="primary"]){background-color:var(--law-brand);color:#fff;}\n'
        )
        css = re.sub(r'/\* LocalAiWeb Design System:start \*/.*?/\* LocalAiWeb Design System:end \*/\s*',
                     '', css, flags=re.S)
        css = '/* LocalAiWeb Design System:start */\n' + block + '/* LocalAiWeb Design System:end */\n' + css
        self.write_files(project_id, {css_path: css}, replace=False)
        meta = self.meta(project_id)
        meta['design'] = current
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        return self.payload(project_id)

    def update_deployment(self, project_id, patch):
        meta = self.meta(project_id)
        deployment = dict(meta.get('deployment') or {})
        allowed = {'github_repo','github_branch','github_private','supabase_ref','vercel_target','production_url','preview_url','custom_domain','last_deployed_at'}
        for key, value in (patch or {}).items():
            if key in allowed:
                deployment[key] = value
        meta['deployment'] = deployment
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        return self.payload(project_id)

    def update_settings(self, project_id, patch):
        meta = self.meta(project_id)
        settings = dict(meta.get('settings') or {})
        allowed = {'quality','responsive','accessibility','seo','performance','micro_interactions',
                   'reduced_motion','semantic_html','language','ai_provider','site_kind','art_direction'}
        for key, value in (patch or {}).items():
            if key in allowed:
                if key == 'site_kind' and value not in SITE_KINDS:
                    raise ValueError('Type de projet inconnu.')
                if key == 'art_direction' and value not in ART_DIRECTIONS:
                    raise ValueError('Direction artistique inconnue.')
                settings[key] = value
        meta['settings'] = settings
        meta['updated_at'] = time.time()
        self.write_meta(project_id, meta)
        return self.payload(project_id)

    def preflight(self, project_id):
        files = self.text_files(project_id)
        html = files.get('index.html','')
        css = '\n'.join(v for k,v in files.items() if k.endswith('.css'))
        js = '\n'.join(v for k,v in files.items() if k.endswith(('.js','.mjs','.ts','.tsx','.jsx')))
        checks = []

        def add(check_id, ok, label, weight, note=''):
            checks.append({'id':check_id,'ok':bool(ok),'label':label,'weight':weight,'note':note})

        lower = html.lower()
        add('index', bool(html.strip()), 'Page principale', 12)
        add('doctype', '<!doctype html' in lower, 'DOCTYPE HTML5', 3)
        add('viewport', 'name="viewport"' in html or "name='viewport'" in html, 'Responsive viewport', 8)
        add('language', '<html' in lower and 'lang=' in lower, 'Langue du document', 4)
        add('title', bool(re.search(r'<title>[^<]{2,}</title>', html, re.I)), 'Titre SEO', 8)
        add('description', bool(re.search(r'<meta[^>]+name=["\']description["\']',html,re.I)), 'Meta description', 8)
        add('semantic', any(tag in lower for tag in ('<main','<header','<nav','<section','<article','<footer')), 'HTML sémantique', 8)
        add('h1', len(re.findall(r'<h1\b',html,re.I)) == 1, 'Un seul H1 principal', 5)
        add('responsive_css', bool(re.search(r'@media\s*\(',css,re.I)) or 'clamp(' in css, 'CSS responsive', 10)
        add('focus', ':focus' in css or ':focus-visible' in css, 'Navigation clavier / focus', 7)
        add('reduced_motion', 'prefers-reduced-motion' in css, 'Respect reduced motion', 5)
        images = re.findall(r'<img\b[^>]*>',html,re.I)
        add('image_alt', not images or all(re.search(r'\balt\s*=',tag,re.I) for tag in images), 'Textes alternatifs images', 7)
        inputs = re.findall(r'<input\b[^>]*>',html,re.I)
        labeled = not inputs or ('<label' in lower or all('aria-label=' in tag.lower() or 'type="hidden"' in tag.lower() for tag in inputs))
        add('form_labels', labeled, 'Libellés de formulaires', 5)
        add('no_todo', not re.search(r'\b(?:TODO|FIXME|PLACEHOLDER|LOREM IPSUM)\b',html+css+js,re.I), 'Aucun placeholder technique', 6)
        add('no_inline_secret', not re.search(r'(?:api[_-]?key|secret|password)\s*[:=]\s*["\'][^"\']{8,}',html+css+js,re.I), 'Aucun secret évident dans le code', 8)

        local_refs = re.findall(r'(?:src|href)=["\']([^"\']+)["\']',html,re.I)
        broken = []
        for ref in local_refs:
            clean = ref.split('#',1)[0].split('?',1)[0].strip()
            if not clean or clean.startswith(('http://','https://','mailto:','tel:','data:','javascript:','#','/web-preview/')):
                continue
            if clean.startswith('/'):
                clean = clean.lstrip('/')
            if clean and clean not in files and not any(a.get('path') == clean for a in self.assets(project_id)):
                broken.append(clean)
        add('local_links', not broken, 'Liens et assets locaux valides', 8, ', '.join(broken[:5]))

        total = sum(x['weight'] for x in checks)
        passed = sum(x['weight'] for x in checks if x['ok'])
        score = round(100 * passed / total) if total else 0
        blockers = [x for x in checks if not x['ok'] and x['weight'] >= 8]
        return {'ok': score >= 82 and not blockers, 'score': score, 'checks': checks, 'blockers': blockers,
                'file_count': len(files), 'asset_count': len(self.assets(project_id))}


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
                rel = path.relative_to(root)
                if any(part in IGNORED_DIRS for part in rel.parts):
                    continue
                if path.name in PRIVATE_NAMES:
                    continue
                if path.is_file():
                    archive.write(path, rel.as_posix())
        return memory.getvalue()

    def save_asset(self, project_id, name, data_url):
        # Keep all imported media under the current LocalAiWeb project, never in LocalAiVision history.
        self.meta(project_id)
        name = Path(str(name or 'asset.bin').replace(chr(92), '/')).name
        name = re.sub(r'[^a-zA-Z0-9._ -]', '_', name).strip('. ')
        if not name: raise ValueError('Nom de fichier invalide.')
        suffix = Path(name).suffix.lower()
        allowed = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif', '.svg', '.glb', '.hdr'}
        if suffix not in allowed:
            raise ValueError('Asset non pris en charge : images, GLB ou éclairages HDR uniquement.')
        try: data = base64.b64decode(str(data_url).split(',',1)[-1], validate=True)
        except Exception: raise ValueError('Asset invalide.')
        limit = 40*1024*1024 if suffix == '.glb' else 20*1024*1024
        if not data or len(data) > limit:
            raise ValueError('Asset vide ou trop volumineux (GLB 40 Mo ; images 20 Mo).')
        if suffix == '.glb':
            valid_header = (len(data) >= 24 and data[:4] == b'glTF'
                            and int.from_bytes(data[4:8], 'little') == 2
                            and int.from_bytes(data[8:12], 'little') == len(data))
            if not valid_header:
                raise ValueError('Modèle GLB 2.0 invalide.')
            json_size = int.from_bytes(data[12:16], 'little')
            if (data[16:20] != b'JSON' or json_size <= 0
                    or json_size % 4 != 0 or 20 + json_size > len(data)):
                raise ValueError('Bloc JSON du GLB invalide.')
        if suffix == '.hdr':
            if not (data.startswith(b'#?RADIANCE') or data.startswith(b'#?RGBE')):
                raise ValueError('Fichier HDR Radiance invalide.')
        target = self.project_dir(project_id) / 'site' / 'assets' / name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        meta = self.meta(project_id)
        meta['updated_at'] = time.time()
        self.write_meta(project_id,meta)
        return {'ok':True, 'path':'assets/'+name, 'size':len(data)}
