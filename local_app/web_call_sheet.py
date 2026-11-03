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


def _internal_link(page,name,pages):
    for href,anchor in page.links:
        try:
            target=urlsplit(href)
            if target.scheme or target.netloc:
                continue
            url=urlsplit(urljoin("https://preview.invalid/"+name,href))
        except ValueError:
            continue
        dest=unquote(url.path.lstrip("/")) or "index.html"
        if href and anchor and dest!=name and dest in pages:
            return anchor,dest
    return None


def _first_call(desk,facts,goal,refs):
    company=desk["business"]
    angle=desk.get("angle")
    introduction="Bonjour. Je crée des sites pour les professionnels."
    if angle:
        fresh=(date.today()-date.fromisoformat(angle["day"])).days<=90
        refs.append(f"Intitulé public retenu par le vendeur le {angle['day']} : « {angle['heading']} » — {angle['url']}.")
        if fresh:
            topic=angle["heading"]
            # Each angle is a question about the literal public heading. It does
            # not imply a conversion problem, missing feature or proven demand.
            if re.search(r"mariage|réception|événement",topic,re.I):
                lead=f"J’ai vu « {topic} » sur votre site. Pour une personne qui prépare cet événement, qu’aimeriez-vous lui montrer en premier ?"
            elif re.search(r"abonnement|récurrent|chaque mois",topic,re.I):
                lead=f"Je suis tombé sur « {topic} » en regardant votre site. Avant de s’engager dans la durée, qu’est-ce qu’un client devrait pouvoir comprendre tout de suite ?"
            elif re.search(r"entreprises|professionnels|collectivités",topic,re.I):
                lead=f"« {topic} » a retenu mon attention sur votre site. Si une entreprise découvre {company} aujourd’hui, quel exemple aimeriez-vous qu’elle voie avant de vous appeler ?"
            elif re.search(r"réserv|rendez.vous|booking",topic,re.I):
                lead=f"Sur votre site, j’ai vu « {topic} ». Quand quelqu’un veut réserver, quel premier geste voulez-vous lui rendre évident ?"
            elif re.search(r"devis|sur.mesure",topic,re.I):
                lead=f"J’ai une question à propos de « {topic} », que j’ai lu sur votre site : qu’aimeriez-vous savoir d’un client avant de lui chiffrer une demande ?"
            else:
                lead=f"En regardant votre site, je me suis arrêté sur « {topic} ». Est-ce l’offre que vous aimeriez mettre en avant, ou y en a-t-il une plus importante aujourd’hui ?"
            return [f"Bonjour. J’ai lu « {topic} » sur votre site. Je crée des sites pour les professionnels et j’ai préparé une maquette pour {company}. Vous avez vingt secondes pour que je vous présente l’idée ?",
                    "Si la personne accepte : "+lead]
        refs.append("Observation de plus de 90 jours : relire la page avant de réutiliser cet intitulé en ouverture.")
    if desk["website"]:
        try: host=urlsplit(desk["website"]).hostname
        except ValueError: host=None
        if host:
            return [introduction+f" Votre fiche pour {company} indique {host}. Est-ce toujours votre site ?",
                    f"Si oui : j’ai préparé un autre parcours où un visiteur pourrait {goal}. Est-ce que je peux vous le montrer pour que vous jugiez vous-même de l’intérêt ?"]
    labels={name:label for name,label,_ in facts}
    for name,_,page in facts:
        link=_internal_link(page,name,desk["pages"])
        if link and link[1] in labels:
            anchor,target=link
            return [introduction+f" Pour {company}, j’ai préparé une maquette : on choisit « {anchor} » et on arrive sur « {labels[target]} ».",
                    "Ce petit parcours vous semble-t-il utile pour vos clients ? Si vous avez vingt secondes, je peux vous le montrer."]
    city=" à "+desk["city"] if desk["city"] else ""
    if desk["activity"]!="votre activité":
        return [introduction+f" Je vous appelle au sujet de {company}{city}. Quand une personne souhaite {goal}, qu’est-ce qu’elle vous demande en premier ?",
                "J’ai une proposition de site à vous montrer. Votre réponse me dira tout de suite si elle est pertinente."]
    return [introduction+f" Pour {company}{city}, j’ai préparé un aperçu privé. Est-ce vous qui choisissez comment présenter l’entreprise en ligne ?",
            "Si oui : qu’aimeriez-vous qu’un visiteur comprenne tout de suite ? Je peux vous montrer en vingt secondes comment la maquette aborde ce point."]


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
      ("1 · Première accroche — obtenir vingt secondes",_first_call(desk,facts,goal,refs)),
      ("2 · Découvrir le besoin", [question,"Comment cela se passe-t-il aujourd’hui ? Parmi les informations que vous donnez à chaque client, laquelle voudriez-vous rendre plus facile à trouver ?"]),
    ]
    if client_points:
        f=next((x for x in client_points if x["category"]=="priorité"),client_points[0])
        sections[1][1].append(f"En reprise seulement, si vous avez déjà échangé : vous aviez indiqué le {f['day']} : « {f['value']} ». Est-ce toujours le point à traiter en premier ?")
    sections[2][1].extend(revisit)
    proof=[]
    for name,label,page in facts[:3]:
        linked=_internal_link(page,name,desk["pages"])
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

    if desk.get("manual_script"):
        sections.insert(2,("Version corrigée par le vendeur",[desk["manual_script"]]))
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
