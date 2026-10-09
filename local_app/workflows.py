"""Workflow conversion and controls. No model/content policy is applied here."""
import json
import math
import uuid


def is_api(wf):
    return isinstance(wf, dict) and bool(wf) and all(
        isinstance(v, dict) and isinstance(v.get('class_type'), str)
        and isinstance(v.get('inputs'), dict) for v in wf.values())


def validate_document(wf):
    if is_api(wf):
        return
    if not isinstance(wf, dict) or not isinstance(wf.get('nodes'), list) or not wf['nodes']:
        raise ValueError('Le JSON doit contenir un workflow ComfyUI (interface ou format API).')
    ids = [str(n.get('id')) for n in wf['nodes'] if isinstance(n, dict)]
    if len(ids) != len(wf['nodes']) or len(set(ids)) != len(ids) or 'None' in ids:
        raise ValueError('Les nœuds du workflow ont des identifiants invalides ou dupliqués.')


def widget_names(node_type, info):
    spec = info.get(node_type, {})
    result = []
    for section in ('required', 'optional'):
        definitions = spec.get('input', {}).get(section, {})
        order = spec.get('input_order', {}).get(section, list(definitions))
        for name in order:
            definition = definitions.get(name)
            if not isinstance(definition, (list, tuple)) or not definition:
                continue
            typ = definition[0]
            opts = definition[1] if len(definition) > 1 and isinstance(definition[1], dict) else {}
            if opts.get('forceInput'):
                continue
            if isinstance(typ, list) or typ in ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO') or (isinstance(typ, str) and typ.startswith('COMFY_DYNAMICCOMBO')):
                result.append(name)
    return result


def to_api(wf, info):
    validate_document(wf)
    if is_api(wf):
        return json.loads(json.dumps(wf))
    if not info:
        raise ValueError('Impossible de lire les types de nœuds de ComfyUI. Vérifie que le moteur répond.')
    if wf.get('definitions', {}).get('subgraphs'):
        raise ValueError('Ce workflow contient des sous-graphes. Ouvre-le dans ComfyUI, puis utilise « Export (API) » et importe ce JSON. La conversion automatique des sous-graphes n’est pas prise en charge.')
    nodes = {str(n['id']): n for n in wf['nodes']}
    links = {int(r[0]): (str(r[1]), int(r[2])) for r in wf.get('links', []) if isinstance(r, list) and len(r) >= 6}
    ignored = {'Note', 'MarkdownNote'}

    def resolve(source, slot, visited=None):
        visited = set(visited or ())
        if source in visited:
            raise ValueError('Boucle dans les connexions du workflow.')
        visited.add(source)
        node = nodes.get(source)
        if not node:
            raise ValueError(f'Nœud source introuvable : {source}')
        typ = node.get('type')
        if node.get('mode') == 2:
            raise ValueError('Une connexion utilise un nœud désactivé. Exporte le workflow au format API depuis ComfyUI.')
        if typ == 'Reroute' or node.get('mode') == 4:
            candidates = [x for x in node.get('inputs', []) if x.get('link') is not None]
            if typ != 'Reroute':
                outputs = node.get('outputs', [])
                out_type = outputs[slot].get('type') if slot < len(outputs) else None
                candidates = [x for x in candidates if x.get('type') == out_type]
            if len(candidates) != 1:
                raise ValueError('Connexion de contournement ambiguë. Exporte le workflow au format API depuis ComfyUI.')
            return resolve(*links[int(candidates[0]['link'])], visited)
        if typ == 'PrimitiveNode':
            raise ValueError('Ce workflow utilise un PrimitiveNode connecté. Exporte-le au format API depuis ComfyUI.')
        return [source, slot]

    api = {}
    for nid, node in nodes.items():
        typ = node.get('type')
        if typ in ignored or typ in ('Reroute', 'PrimitiveNode') or node.get('mode') in (2, 4):
            continue
        if typ not in info:
            raise ValueError(f'Nœud ComfyUI manquant : {typ}. Installe son extension ou importe un workflow compatible.')
        inputs = {}
        for item in node.get('inputs', []):
            link = item.get('link')
            if link is not None:
                if int(link) not in links:
                    raise ValueError(f'Connexion introuvable : {link}')
                inputs[item['name']] = resolve(*links[int(link)])
        named = node.get('widgets_values_named')
        if isinstance(named, dict):
            inputs.update({k: v for k, v in named.items() if k not in inputs})
        else:
            vals = node.get('widgets_values') or []
            if not isinstance(vals, list):
                raise ValueError(f'Widgets non convertibles pour {typ}. Utilise Export (API).')
            index = 0
            names = widget_names(typ, info)
            # Converted-to-input widgets can retain their saved UI values.
            # Consume those placeholders when a full widget vector is present.
            full_vector = len(vals) >= len(names)
            for name in names:
                if name in inputs and not full_vector:
                    continue
                if index >= len(vals):
                    break
                if name not in inputs:
                    inputs[name] = vals[index]
                index += 1
                # Only seeds have this extra UI-only widget; literal text such as
                # "fixed" must remain untouched in prompt widgets.
                if name in ('seed', 'noise_seed') and index < len(vals) and isinstance(vals[index], str) and vals[index] in ('fixed', 'randomize', 'increment', 'decrement'):
                    index += 1
        api[nid] = {'class_type': typ, 'inputs': inputs, '_meta': {'title': node.get('title') or typ}}
    return api


def preflight(api, info):
    if not info:
        raise ValueError('Les informations du moteur ComfyUI sont indisponibles.')
    errors = []
    for nid, node in api.items():
        typ = node['class_type']
        if typ not in info:
            errors.append(f'nœud manquant : {typ}')
            continue
        if typ == 'SaveVideo':
            codec_spec = info[typ].get('input', {}).get('optional', {}).get('codec', [])
            if codec_spec and str(codec_spec[0]).startswith('COMFY_DYNAMICCOMBO'):
                # New ComfyUI handles the optional codec as a nested value.
                # Omitting the legacy scalar selects its native default.
                if isinstance(node['inputs'].get('codec'), str):
                    node['inputs'].pop('codec')
        for section in ('required', 'optional'):
            for name, definition in info[typ].get('input', {}).get(section, {}).items():
                if name not in node['inputs']:
                    if section == 'required':
                        errors.append(f'{typ}.{name} absent')
                    continue
                value = node['inputs'][name]
                if isinstance(value, list):
                    if len(value) == 2 and str(value[0]) not in api:
                        errors.append(f'{typ}.{name} : connexion vers un nœud absent')
                    continue
                if (typ in ('LoadImage', 'LoadImageMask') and name == 'image') or (typ == 'LoadVideo' and name in ('file', 'video')):
                    # User inputs are uploaded/copied just before generation; /object_info may cache its filename list.
                    continue
                if definition and isinstance(definition[0], list) and value not in definition[0]:
                    errors.append(f'{typ}.{name} : valeur ou fichier indisponible « {value} »')
    if errors:
        raise ValueError('Workflow non prêt :\n' + '\n'.join(errors))


def profile(api):
    values = ' '.join(str(v).lower() for n in api.values() for k, v in n.get('inputs', {}).items() if isinstance(v, str) and k in ('ckpt_name','unet_name','model_name','vae_name','clip_name'))
    types = ' '.join(n['class_type'].lower() for n in api.values())
    if 'hunyuanimage2.1' in values or 'emptyhunyuanimagelatent' in types:
        return 'hunyuanimage21'
    if 'hyomniweaving' in types or 'hy_omniweaving' in values:
        tasks = {str(n.get('inputs', {}).get('task', '')).lower() for n in api.values()}
        return 'omniweaving-i2v' if 'i2v' in tasks else 'omniweaving-t2v'
    if 'hunyuanvideo1.5_480p_i2v_step_distilled' in values:
        return 'hunyuan15-i2v-step'
    if 'hunyuanvideo1.5' in values or 'hunyuanvideo15' in types or 'hunyuan_video_15' in values:
        return 'hunyuan15'
    if 'wanvace' in types or 'vace' in values:
        return 'vace'
    if 'animate' in values or 'wananimate' in types:
        return 'wan-animate'
    if 'wan' in types or 'wan2.' in values:
        return 'wan'
    if 'ltx' in types or 'ltx-' in values:
        return 'ltx'
    if 'flux' in values and 'schnell' in values:
        return 'schnell'
    if 'flux' in values:
        return 'flux'
    if 'animagine' in values:
        return 'animagine'
    if 'sd_xl' in values or 'sdxl' in values or 'realvisxl' in values:
        return 'sdxl'
    return 'unknown'


def text_roles(api):
    roles = {}
    def visit(ref, role, seen):
        if not isinstance(ref, list) or len(ref) != 2:
            return
        nid = str(ref[0])
        if nid in seen or nid not in api:
            return
        seen.add(nid)
        node = api[nid]
        if node['class_type'].startswith('CLIPTextEncode') or node['class_type'] == 'HYOmniWeavingTextEncode':
            roles.setdefault(nid, set()).add(role)
            return
        for value in node['inputs'].values():
            if isinstance(value, list):
                visit(value, role, seen)
    for node in api.values():
        for key in ('positive', 'negative'):
            visit(node['inputs'].get(key), key, set())
    return roles


def apply_inputs(api, prompt='', negative=None, image_ref=None, settings=None, mask_ref=None, video_ref=None):
    settings = settings or {}
    kind = profile(api)
    roles = text_roles(api)
    for nid, node in api.items():
        inp = node['inputs']
        title = node.get('_meta', {}).get('title', '').lower()
        if node['class_type'].startswith('CLIPTextEncode') or node['class_type'] == 'HYOmniWeavingTextEncode':
            role = roles.get(nid, {'negative' if 'negative' in title or 'négatif' in title else 'positive'})
            # Conditioning helper nodes (notably Wan VACE) can make a graph walk
            # reach both encoders from both sampler branches. An explicit node
            # title is a stronger signal than that ambiguous traversal.
            if 'negative' in title or 'négatif' in title:
                role = {'negative'}
            elif 'positive' in title or 'positif' in title:
                role = {'positive'}
            if role == {'positive', 'negative'} and negative is not None and prompt != negative:
                raise ValueError('Le même encodeur texte alimente les prompts positif et négatif. Sépare ces deux encodeurs dans ComfyUI.')
            value = negative if role == {'negative'} else prompt
            if value is not None and (value or role == {'negative'}):
                for key in ('text', 'text_g', 'text_l', 'prompt'):
                    if key in inp and not isinstance(inp[key], list):
                        inp[key] = value
        else:
            for key in ('prompt', 'positive_prompt', 'prompt_text'):
                if prompt and isinstance(inp.get(key), str):
                    inp[key] = prompt
            if negative is not None:
                for key in ('negative_prompt', 'negative'):
                    if isinstance(inp.get(key), str):
                        inp[key] = negative
        if image_ref and node['class_type'] == 'LoadImage':
            inp['image'] = image_ref['name']
        if mask_ref and node['class_type'] == 'LoadImageMask':
            inp['image'] = mask_ref['name']
            inp['channel'] = 'red'
        if video_ref and node['class_type'] == 'LoadVideo':
            # Recent ComfyUI exposes this widget as `file`; some versions use
            # `video`. Keep whichever key the workflow already contains.
            if 'file' in inp and not isinstance(inp.get('file'), list):
                inp['file'] = video_ref['name']
            elif 'video' in inp and not isinstance(inp.get('video'), list):
                inp['video'] = video_ref['name']
            else:
                inp['file'] = video_ref['name']
    seed = settings.get('seed')
    seed = uuid.uuid4().int % 2147483647 if seed is None else int(seed)
    if seed < 0 or seed > 2**53 - 1:
        raise ValueError('Le seed doit être compris entre 0 et 9007199254740991.')
    for node in api.values():
        for key in ('seed', 'noise_seed'):
            if key in node['inputs'] and not isinstance(node['inputs'][key], list):
                node['inputs'][key] = seed
    # Defaults preserve each workflow. Known model profiles are used only when
    # the user explicitly requests a preset; advanced settings take precedence.
    presets = {
        'sdxl': (16, 25, 35),
        'wan': (12, 20, 30),
        'hunyuan15': (12, 20, 28),
        'hunyuan15-i2v-step': (4, 8, 12),
        'omniweaving-t2v': (24, 36, 50),
        'omniweaving-i2v': (24, 36, 50),
        'hunyuanimage21': (8, 8, 8),
    }
    quality = settings.get('quality', 'workflow')
    steps = settings.get('steps')
    if steps is None and quality in ('draft', 'balanced', 'quality') and kind in presets:
        steps = presets[kind][('draft', 'balanced', 'quality').index(quality)]
    if steps is not None and (int(steps) < 1 or int(steps) > 10000):
        raise ValueError('Le nombre d’étapes doit être compris entre 1 et 10000.')
    video = kind in ('wan', 'hunyuan15', 'hunyuan15-i2v-step', 'omniweaving-t2v', 'omniweaving-i2v')
    if video:
        dims = {'1:1': (512,512), '16:9': (832,480), '9:16': (480,832), '4:3': (640,480), '3:4': (480,640)}
    elif kind == 'hunyuanimage21':
        dims = {'1:1': (2048,2048), '16:9': (2560,1536), '9:16': (1536,2560), '4:3': (2304,1792), '3:4': (1792,2304)}
    else:
        dims = {'1:1': (1024,1024), '16:9': (1344,768), '9:16': (768,1344), '4:3': (1152,864), '3:4': (864,1152)}
    width, height = dims.get(settings.get('aspect'), (None, None))
    width, height = settings.get('width') or width, settings.get('height') or height
    if kind == 'hunyuanimage21' and settings.get('aspect') in (None, '', 'auto') and not settings.get('width') and not settings.get('height'):
        square = {'draft': 1024, 'balanced': 1536, 'quality': 2048}.get(quality)
        if square:
            width = height = square
    for label, value in (('Largeur', width), ('Hauteur', height)):
        if value is not None and (int(value) < 8 or int(value) % 8):
            raise ValueError(f'{label} : utilise un multiple de 8, supérieur ou égal à 8.')
    fps = settings.get('fps')
    if fps is not None and (not math.isfinite(float(fps)) or float(fps) <= 0):
        raise ValueError('Les FPS doivent être positifs.')
    duration = settings.get('duration')
    frames = None
    if duration is not None:
        if not math.isfinite(float(duration)) or float(duration) <= 0:
            raise ValueError('La durée doit être positive.')
        effective_fps = fps
        if effective_fps is None:
            for node in api.values():
                effective_fps = next((node['inputs'][k] for k in ('fps','frame_rate','framerate') if isinstance(node['inputs'].get(k), (int,float))), None)
                if effective_fps:
                    break
        if not effective_fps:
            raise ValueError('Renseigne les FPS pour calculer le nombre d’images de la vidéo.')
        frames = max(1, round(float(duration) * float(effective_fps)))
        stride = 4 if kind in ('wan', 'hunyuan15', 'hunyuan15-i2v-step', 'omniweaving-t2v', 'omniweaving-i2v') else 1
        frames = max(1, round((frames - 1) / stride) * stride + 1)
    for node in api.values():
        inp = node['inputs']
        for key, val in [('steps', steps), ('width', width), ('height', height)]:
            if val is not None and key in inp and not isinstance(inp[key], list):
                inp[key] = int(val)
        for key in ('fps', 'frame_rate', 'framerate'):
            if fps is not None and key in inp and not isinstance(inp[key], list):
                inp[key] = float(fps)
        for key in ('frames', 'num_frames', 'frame_count', 'length'):
            if frames is not None and key in inp and not isinstance(inp[key], list):
                inp[key] = frames
        if settings.get('denoise') is not None and 'denoise' in inp and not isinstance(inp['denoise'], list):
            value = float(settings['denoise'])
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('La force de retouche doit être comprise entre 0 et 1.')
            inp['denoise'] = value
    return api
