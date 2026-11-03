"""A seller's script tied to the actual private preview, never to estimated ROI."""
from html.parser import HTMLParser
from datetime import date, datetime
from urllib.parse import urlsplit, unquote, urljoin
from io import BytesIO
import re
from xml.sax.saxutils import escape


class PageFacts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.field=None
        self.text={"h1":[],"title":[]}
        self.tel=False
        self.form=False
        self.anchor=None
        self.links=[]

    def handle_starttag(self,tag,attrs):
        if tag in self.text:
            self.field=tag
        if tag=="a":
            href=str(dict(attrs).get("href") or "")
            self.anchor=[href,[]]
            if re.fullmatch(r"tel:\+?[0-9() .-]{6,24}",href,re.I):
                self.tel=True
        if tag=="form":
            self.form=True

    def handle_endtag(self,tag):
        if tag=="a" and self.anchor:
            href,parts=self.anchor
            self.links.append((href," ".join(" ".join(parts).split())[:100]))
            self.anchor=None
        if tag==self.field:self.field=None

    def handle_data(self,data):
        if self.field:self.text[self.field].append(data)
        if self.anchor:self.anchor[1].append(data)


def script(desk,preview):
    if not desk["ready"] or desk["opposed"]:
        return []
    facts=[]
    names=sorted(desk["pages"],key=lambda p:(p!="index.html",p))
    order=list(dict.fromkeys([n for n in desk["page_order"] if n in names]+names))
    for name in order[:12]:
        file=preview/name
        if not file.resolve().is_relative_to(preview.resolve()) or file.stat().st_size>2_000_000:
            continue
        page=PageFacts()
        page.feed(file.read_text(encoding="utf-8",errors="replace"))
        label=" ".join(" ".join(page.text["h1"] or page.text["title"]).split())[:100] or name
        facts.append((name,label,page))
    if not facts:return []
    activity=desk["activity"].lower()
    sectors=[
        (r"fleur|florist|bouquet","Pour quelle occasion vos clients hésitent-ils le plus entre deux compositions ?","choisir un bouquet avant de se déplacer"),
        (r"coiff|hair|barber|beauté","Quelles questions reviennent avant une prise de rendez-vous ?","préparer une demande de rendez-vous"),
        (r"restaur|café|traiteur","Vos clients cherchent-ils d’abord la carte, les horaires ou un moyen de réserver ?","choisir avant de venir sur place"),
        (r"artisan|plomb|menuis|peint|maçon","Quelle information vous manque le plus souvent quand on vous demande un devis ?","préparer une demande de devis plus précise"),
        (r"boutique|commerce|shop|vende|librair","Que demande-t-on le plus souvent au téléphone avant de passer en boutique ?","repérer une offre avant la visite"),
    ]
    question,goal=next(((q,g) for pattern,q,g in sectors if re.search(pattern,activity)),
        ("Quelle question vous pose-t-on régulièrement avant de faire appel à vous ?","trouver l’information utile avant de vous contacter"))
    company=desk["business"]
    place=" à "+desk["city"] if desk["city"] else ""
    imported=datetime.fromtimestamp(desk["source_date"]).date().isoformat() if desk["source_date"] else "date inconnue"
    refs=[f"Fiche enregistrée le {imported} depuis {desk['source']}. Cette date est celle du dossier.",
          f"Nom relevé sur la fiche : {company}.",
          f"Activité indiquée : {activity}." if activity!="votre activité" else "Activité à confirmer auprès de l’établissement."]
    if desk["address"]:refs.append("Adresse indiquée sur cette fiche : "+desk["address"]+".")
    if desk["website"]:
        refs.append("Site renseigné dans cette source : "+desk["website"]+". Demander si cette adresse est toujours utilisée.")
    elif desk["website_recorded"]:
        refs.append("Un site est signalé dans la source, sans adresse exploitable.")
    else:
        refs.append("Site non renseigné dans la fiche. Demander quel site ou canal l’entreprise utilise actuellement.")
    reg=desk["registry"]
    if reg.get("matched") is True and re.fullmatch(r"\d{9}",str(reg.get("siren",""))):
        checked=datetime.fromtimestamp(reg["checked_at"]).date().isoformat() if reg.get("checked_at") else "date de consultation non conservée"
        refs.append(f"Registre rapproché · {checked} : {reg.get('legal_name','')} · SIREN {reg['siren']} · {reg.get('source','')}.")
    else:
        refs.append("Identité juridique non rapprochée : confirmer la raison sociale avant le devis.")
    confirmed=[]
    revisit=[]
    for f in desk["facts"]:
        line=f"{f['category'].capitalize()} : {f['value']} ({f['source']}, {f['day']})"
        if (date.today()-date.fromisoformat(f["day"])).days>90:
            revisit.append("Revalider ce point avant de l’utiliser : "+line)
        else:
            refs.append(line);confirmed.append(f)
    client_points=[f for f in confirmed if f["source"] in ("Client au téléphone","Document du client")]
    sections=[("Repères du dossier — pour le vendeur",refs),
      ("1 · Ouverture — 20 à 40 secondes",[
        f"Bonjour, je m’appelle [votre nom], de [votre entreprise]. Est-ce vous qui vous occupez de la présentation en ligne chez {company}{place} ?",
        f"J’ai préparé une maquette privée pour vous montrer comment un visiteur pourrait {goal}. Avez-vous deux minutes pour regarder un exemple et me dire si cela répond à une demande que vous recevez ?"]),
      ("2 · Découvrir le besoin", [question,"Comment cela se passe-t-il aujourd’hui ? Parmi les informations que vous donnez à chaque client, laquelle voudriez-vous rendre plus facile à trouver ?"]),
    ]
    if client_points:
        f=next((x for x in client_points if x["category"]=="priorité"),client_points[0])
        sections[1][1].append(f"Vous aviez indiqué le {f['day']} : « {f['value']} ». Est-ce toujours le point à traiter en premier ?")
    sections[2][1].extend(revisit)
    proof=[]
    for name,label,page in facts[:3]:
        linked=None
        for href,anchor in page.links:
            try:
                target=urlsplit(href)
                if target.scheme or target.netloc:
                    continue
                url=urlsplit(urljoin("https://preview.invalid/"+name,href))
            except ValueError:
                continue
            dest=unquote(url.path.lstrip("/")) or "index.html"
            if href and anchor and url.hostname=="preview.invalid" and dest!=name and dest in desk["pages"]:
                linked=(anchor,dest);break
        if linked:
            argument=f"Dans la maquette, « {linked[0]} » ouvre {linked[1]}. Suivons ensemble ce lien. Est-ce le bon chemin pour votre clientèle ?"
        elif page.tel:
            argument="Cette page contient un lien d’appel. Montrons-le dans l’aperçu. Est-ce le bon moyen pour vos clients de vous joindre ?"
        elif page.form:
            argument="Voici les champs proposés pour une demande. Quelles informations vous seraient utiles ? Nous testerons ensemble la réception avant la livraison."
        else:
            argument=f"Cette page présente « {label} ». Est-ce ce que votre client devrait voir en premier, ou mettriez-vous autre chose en avant ?"
        proof.append(f"Montrer {name} — {argument}")
    sections.extend([
      ("3 · Démonstration — arguments à montrer",proof),
      ("4 · Répondre aux objections",[
        "« J’ai déjà un site. » — Très bien. Prenons la question que vous venez de citer. La réponse est-elle déjà facile à trouver sur votre site ? Si oui, qu’aimeriez-vous améliorer en priorité ?",
        "« Combien ça coûte ? » — Je peux vous chiffrer précisément les pages et les fonctions que vous retenez. Je sépare la création des frais récurrents de domaine, d’hébergement et de maintenance.",
        "« Je dois réfléchir. » — Bien sûr. Quel point voulez-vous éclaircir : le contenu, le fonctionnement ou le budget ? Souhaitez-vous convenir d’un autre moment ?",
        "« Ne me rappelez pas. » — Compris, je note votre opposition. Merci de me l’avoir indiqué. Terminer l’appel et enregistrer l’opposition."]),
      ("5 · Conclure — passer au devis avec son accord",[
        "Si je résume, votre priorité est [besoin exprimé] et vous souhaitez [périmètre retenu]. Est-ce exact ?",
        "Voulez-vous que je prépare un devis écrit pour ce périmètre ? À quelle adresse professionnelle et à quelle échéance souhaitez-vous le recevoir ?",
        "Noter le besoin et la réponse du client. Programmer une relance uniquement si elle est convenue."])
    ])
    if client_points:
        priority=next((x["value"] for x in client_points if x["category"]=="priorité"),client_points[0]["value"])
        words={w for w in re.findall(r"[^\W\d_]{4,}",priority.casefold()) if w not in
               {"avec","pour","dans","avant","montrer","avoir","faire","nous","vous","plus","page","site"}}
        matches=[(len(words.intersection(re.findall(r"[^\W\d_]{4,}",label.casefold()))),name,label)
                 for name,label,_ in facts]
        count,name,label=max(matches)
        if count:
            proof.insert(0,f"Priorité confirmée : « {priority} ». Ouvrir {name} (« {label} ») et demander : est-ce que cette présentation répond à ce point, ou faut-il l’adapter ?")
        else:
            proof.append(f"Priorité confirmée : « {priority} ». Aucune correspondance explicite dans les titres des pages analysées. Demander ce qu’il faudrait ajouter avant de le chiffrer.")
        sections[-1][1][0]=f"Pour le devis, je retiens « {priority} ». Que faut-il inclure en priorité, et que souhaitez-vous remettre à plus tard ?"

    return sections


def pdf(desk,sections):
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,HRFlowable
    if not sections:
        raise ValueError("Feuille indisponible : maquette absente ou opposition enregistrée.")
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,title="Feuille d’appel — "+desk["business"],
        leftMargin=17*mm,rightMargin=17*mm,topMargin=16*mm,bottomMargin=16*mm)
    styles=getSampleStyleSheet()
    heading=ParagraphStyle("Call heading",parent=styles["Heading2"],textColor=colors.HexColor("#55347a"),
                           fontSize=13,leading=16,spaceBefore=10,spaceAfter=4)
    speech=ParagraphStyle("Spoken",parent=styles["BodyText"],fontSize=11,leading=15,spaceAfter=3)
    evidence=ParagraphStyle("Facts",parent=speech,fontSize=10,leading=13,textColor=colors.HexColor("#454050"))
    def footer(canvas,doc):
        canvas.setFillColor(colors.HexColor("#57446f"));canvas.setFont("Helvetica",9)
        canvas.drawString(17*mm,10*mm,"LocalAiWeb  /  Support vendeur")
        canvas.drawRightString(193*mm,10*mm,"Page "+str(doc.page))
    body=[Paragraph("Feuille d’appel",styles["Title"]),Paragraph(escape(desk["business"]),styles["Heading2"])]
    for title,lines in sections:
        if title.startswith("4 ·"):
            body.extend([PageBreak(),Paragraph(escape(desk["business"])+" · Suite de l’appel",styles["Heading2"])])
        body.append(Paragraph(escape(title),heading))
        for line in lines:
            body.append(Paragraph(escape(line),evidence if title.startswith("Repères") else speech))
    body.extend([Spacer(1,6*mm),Paragraph("À noter avant de raccrocher",heading)])
    for label in ("Besoin exprimé et périmètre retenu","Accord pour recevoir le devis","Prochaine action et date convenue"):
        body.extend([Paragraph(label,evidence),Spacer(1,6*mm),HRFlowable(width="100%",color=colors.HexColor("#c8c0d2")),Spacer(1,3*mm)])
    doc.build(body,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()
