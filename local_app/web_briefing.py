"""LocalAiWeb specification-first guide and measurable output checks.

A missing decision is discussed with the user *before* spending tokens generating a site.
Questions are saved with the project and survive application restarts.  This module
does not copy another builder's proprietary prompts, site code or templates.
"""
import colorsys
import re
import unicodedata

WAITING_MESSAGE = "La prévisualisation devrait apparaitre ici."

def plain(value):
    raw = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(c for c in raw if not unicodedata.combining(c))

def has(pattern, value):
    return bool(re.search(pattern, plain(value), flags=re.I))

def infer(request):
    text = plain(request)
    shop = has(r'\b(boutique|commerce|e-?commerce|produits?|catalogue|panier|achete|vente|store|shop)\b', text)
    spectacular = has(r'\b(exceptionnel|epoustoufl|spectacul|premium|lux|artistique|cinemati|immersi|wow|impressionn|revolutionn)\w*', text)
    visual3d = has(r'\b(3d|three\.?js|webgl|modele 3d|objet 3d)\b', text)
    chosen_images = has(r'\b(photo|photograph|illustration|image|video|glb|hdr|visuel)\w*', text) or visual3d
    colors = []
    for label,pat in (('bleu',r'\bbleu\w*\b'),('vert',r'\bvert\w*\b'),('rouge',r'\brouge\w*\b'),
                       ('violet',r'\bviolet\w*\b'),('orange',r'\borange\b'),('noir',r'\bnoir\b'),
                       ('blanc',r'\bblanc\b'),('rose',r'\brose\b'),('jaune',r'\bjaune\b')):
        if re.search(pat,text): colors.append(label)
    return {
        'shop':shop,'spectacular':spectacular,'visual3d':visual3d,'chosen_images':chosen_images,
        'colors':colors,'light_green':has(r'\bvert(?:e)?\s+clair(?:e)?\b', text),
        'has_brand':has(r"(?:s['’]appelle|nomm[eé]|marque|appelle|brand|enseigne)\s*[: ]\s*[\"']?[a-z0-9]",text),
        'has_goal':has(r'\b(site|application|app|boutique|portfolio|landing|vitrine|blog|commerce)\b',text),
        'has_payment':has(r'\b(paiement|stripe|checkout|commander|achat|panier|reglement)\b',text),
        'has_products':has(r'\b(nom\w* des produits|liste de produits|prix|catalogue fourni|fichier csv|references?)\b',text),
        'has_style':bool(colors) or has(r'\b(minimal|sobre|moderne|artistique|luxe|professionnel|3d|cinematique|epoustoufl|premium)\w*\b',text)
    }

def questions_for(request):
    info = infer(request)
    questions = []
    def ask(key, question, choices):
        questions.append({'key':key,'question':question,'choices':choices})
    if not info['has_goal']:
        ask('goal','Quel type de site veux-tu et à quoi doit-il servir ?',
            ['Site vitrine', 'Boutique en ligne', 'Portfolio', 'Application web', 'Landing page'])
    if not info['has_brand']:
        ask('brand','Quel est le nom exact de la marque ou du site ?',
            ['Choisis un nom pour moi', 'Je donnerai le nom et le slogan'])
    if not info['has_style']:
        ask('identity','Quelle ambiance et quelles couleurs veux-tu ?',
            ['Sobre et élégant', 'Professionnel contemporain', 'Luxe', 'Audacieux et créatif', 'Couleurs à préciser'])
    if info['spectacular'] and not info['chosen_images']:
        ask('visual','Pour obtenir un rendu exceptionnel, quel type de visuels préfères-tu ?',
            ['Photos réalistes (fichiers à fournir)', '3D interactive (GLB ou sculpture originale)', 'Illustrations SVG originales', 'Typographie spectaculaire sans images'])
    if info['shop']:
        if not info['has_products']:
            ask('inventory','Quels produits, catégories et prix dois-je afficher ?',
                ['Utilise des exemples clairement indiqués', 'Je vais donner mes produits et prix', 'Je fournirai un catalogue plus tard'])
        if not info['has_payment']:
            ask('checkout','Pour les commandes, quel fonctionnement faut-il prévoir ?',
                ['Catalogue uniquement, sans paiement', 'Panier fonctionnel, paiement à connecter', 'Vente réelle avec paiement (Stripe à connecter)'])
    if info['visual3d'] and not has(r'\b(glb|procedural|sculpture|modele fourni|import)\b',request):
        ask('model3d','As-tu un modèle 3D GLB du produit ou veux-tu une sculpture 3D originale pour commencer ?',
            ['Sculpture 3D de démonstration', 'Je fournirai un fichier GLB', 'Présente surtout le produit en 2D pour commencer'])
    return questions[:6]

def new_plan(request):
    request=str(request or '').strip()
    questions=questions_for(request)
    return {'original':request,'answers':{},'questions':questions,'index':0,'ready':not questions,'revision':1}

def pending_question(plan):
    index=int(plan.get('index',0))
    questions=plan.get('questions') or []
    if index>=len(questions):return None
    return questions[index]

def answer_plan(plan, response):
    item=pending_question(plan)
    if not item:return plan
    answer=str(response or '').strip()
    if not answer:raise ValueError('Ta réponse est vide.')
    plan['answers'][item['key']]=answer[:3000]
    plan['index']+=1
    plan['ready']=pending_question(plan) is None
    return plan

def full_prompt(plan):
    text=plan.get('original','')
    answers=plan.get('answers') or {}
    if not answers:return text
    original_lines=['DEMANDE ORIGINALE INTANGIBLE :',text,'','PRÉCISIONS VALIDÉES PAR LE CLIENT :']
    for q in plan.get('questions') or []:
        if q['key'] in answers:
            original_lines.extend(['- '+q['question'],answers[q['key']]])
    original_lines.extend(['','CONTRAINTE ABSOLUE : respecter chaque couleur, page, catégorie,',
                           'fonction et nom explicitement demandés. Ne pas remplacer un choix client par',
                           'une identité générique violette. Ne jamais prétendre disposer d’images',
                           'produit ou d’un paiement réellement branché sans ces ressources.'])
    return '\n'.join(original_lines)

def _rgb_hex(hexcode):
    x=hexcode.lstrip('#')
    if len(x)==3:x=''.join(c+c for c in x)
    if len(x)!=6:return None
    try:return tuple(int(x[i:i+2],16)/255 for i in (0,2,4))
    except ValueError:return None

def _hues(source):
    out=[]
    for value in re.findall(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b',source):
        rgb=_rgb_hex(value)
        if rgb:
            h,l,s=colorsys.rgb_to_hls(*rgb)
            out.append((h*360,l,s))
    for red,green,blue in re.findall(r'rgba?\(\s*(\d{1,3})\s*[, ]+\s*(\d{1,3})\s*[, ]+\s*(\d{1,3})',source):
        h,l,s=colorsys.rgb_to_hls(min(int(red),255)/255,min(int(green),255)/255,min(int(blue),255)/255)
        out.append((h*360,l,s))
    return out

def audit(files, request):
    """Deterministic contract audit, complementary to web-builder's structural preflight.

    Failures become precise second-pass repair instructions; not a fake aesthetic score.
    """
    html=str(files.get('index.html') or '')
    css='\n'.join(str(v) for k,v in files.items() if k.endswith('.css'))
    js='\n'.join(str(v) for k,v in files.items() if k.endswith(('.js','.mjs')))
    body=plain(html)
    req=plain(request)
    info=infer(request)
    findings=[]
    def issue(code,fix):findings.append({'id':code,'fix':fix})
    if WAITING_MESSAGE in html or 'Ton prochain site commence ici.' in html:
        issue('placeholder','Replace the starter placeholder with the COMPLETE requested working site.')
    if len(html.strip())<1700:
        issue('depth','The generated HTML is too skeletal; deliver substantive sections, actual content, clear navigation and functional UX.')
    if len(css.strip())<2100:
        issue('visual_polish','The stylesheet needs a complete premium responsive visual system: typography, spacing, interactive states and mobile layouts.')
    if not re.search(r'<(main|section|article)\b',html,re.I):
        issue('semantics','Structure the site with semantic sections, headings and meaningful page content.')
    if info['shop']:
        if not has(r'\b(produit|catalogue|product)\w*',body):
            issue('catalogue','An online store must show a browsable catalogue and actual product detail states.')
        if has(r'\b(recherche|search|rechercher|champ de recherche)\b',req):
            if not re.search(r'<input\b[^>]*(type=["\']search|(?:placeholder|aria-label|id)=["\'][^"\']*(?:recher|search))',html,re.I):
                issue('search_ui','Implement a visible accessible product search input.')
            if not re.search(r'addEventListener|oninput|onkeyup',js,re.I):
                issue('search_logic','Make product search actually filter items in JS (not just a decorative input).')
        if has(r'\b(categori|categorie|categories|classe)\w*',req):
            if not has(r'\b(categori|categorie|category|categories)\w*',body+' '+js):
                issue('category','Create meaningful category browsing and navigation.')
    # Brand names explicitly requested must be rendered.
    m=re.search(r"(?:s['’]appelle|site s['’]appelle|nomm[eé]|marque\s*:|appelle)\s*[\"']?([A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ-]{2,})",request,re.I)
    if m and plain(m.group(1)) not in body:
        issue('brand_name','The requested brand name '+m.group(1)+' must appear prominently in the site.')
    hues=_hues(css+html)
    blue=any(190<=h<=260 and s>.25 and .15<l<.90 for h,l,s in hues)
    green=any(75<=h<=175 and s>.24 and .20<l<.90 for h,l,s in hues)
    if 'bleu' in info['colors'] and not blue and not re.search(r'\b(blue|cyan|skyblue)\b',css,re.I):
        issue('blue_palette','User explicitly requests BLUE: use visible blue tones in CSS, nav and dominant surfaces.')
    if 'vert' in info['colors'] and not green and not re.search(r'\b(lime|green|lightgreen)\b',css,re.I):
        issue('green_palette','User explicitly requests GREEN: use green accents or surfaces instead of purple.')
    if info['light_green'] and not any(75<=h<=175 and s>.23 and l>.45 for h,l,s in hues) and not re.search(r'\b(lightgreen|lime)\b',css,re.I):
        issue('light_green','User explicitly requests LIGHT GREEN: provide light green CTAs and highlights.')
    if info['visual3d'] and not re.search(r'three|webgl|babylon|<model-viewer',html+js,re.I):
        issue('missing_3d','The user requested ACTUAL interactive 3D; implement real WebGL/Three.js, not a 2D mockup.')
    if 'viewport' not in html:issue('responsive','Include the viewport meta tag and responsive layout.')
    if not re.search(r'@media\s*\(',css,re.I):issue('mobile','Provide responsive CSS breakpoints for tablet and mobile.')
    return findings
