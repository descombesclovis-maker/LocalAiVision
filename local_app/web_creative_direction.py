"""Project-specific design strategy for LocalAiWeb coding agents.

Used as a creative/UX brief, not as a fixed template or a claim that code can
automatically score aesthetic quality.
"""
import re
import unicodedata


def normalized(value):
    text=unicodedata.normalize("NFKD",str(value or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


SECTORS=(
    ("toilettage|groom|animal|animaux|chiens?|chats?|paw",
     "soin animalier","rassurer sur le bien-être, valoriser l'expertise humaine",
     "portrait animalier authentique, lumière douce, détails du pelage, atmosphère propre et chaleureuse",
     "découvrir la prestation → voir les résultats → demander un rendez-vous"),
    ("parfum|cosmet|beaute|coiff|spa|barbier|maquillage",
     "beauté et soin","installer un univers sensoriel crédible",
     "macro-photographies et textures de produits, typographie raffinée et lumière étudiée",
     "explorer les soins → comprendre la différence → réserver ou acheter"),
    ("restaurant|cafe|patisserie|boulanger|gastronom|traiteur",
     "restauration","donner envie sans distraire du menu et des horaires",
     "photographies de plats, matières culinaires, rythme éditorial et couleur des ingrédients",
     "découvrir la carte → trouver les informations → réserver ou commander"),
    ("artisan|bijou|ceram|mobilier|atelier|couture|sur.mesure",
     "artisanat","rendre visible le geste, les matières et la qualité",
     "macro-photographie des pièces, récit de fabrication, compositions d'atelier",
     "comprendre le savoir-faire → examiner une réalisation → demander un devis"),
    ("peche|poisson|randonnee|camping|sport|plein air",
     "équipement et plein air","répondre au besoin d'usage sans noyer le visiteur",
     "scènes terrain, détails fonctionnels, typographie précise, filtres utiles",
     "trouver sa pratique → comparer les produits → choisir une fiche"),
    ("saas|application|logiciel|robot|technolog|electronique",
     "technologie","démontrer la valeur du produit rapidement",
     "démonstrations interactives, états réalistes d'interface et schémas utiles",
     "comprendre → tester → s'engager"),
    ("conseil|cabinet|architect|expert|avocat|immobilier",
     "services professionnels","créer une confiance vérifiable, sans corporate interchangeable",
     "réalisations photographiées, typographie éditoriale, cas concrets",
     "comprendre → vérifier l'expertise → prendre contact"),
)


def concept(request, brand=""):
    text=normalized(brand+" "+str(request or ""))
    for pattern,sector,goal,visual,journey in SECTORS:
        if re.search(pattern,text):
            return dict(sector=sector,goal=goal,visual=visual,journey=journey)
    return dict(
        sector="activité propre à l'entreprise",
        goal="communiquer la différence de la marque et faciliter l'action centrale",
        visual="métaphores et détails fidèles aux produits ou services réellement proposés",
        journey="découvrir la promesse → examiner les preuves → agir sans friction",
    )


def instructions(request, brand=""):
    theme=concept(request,brand)
    return (
        "DIRECTION ARTISTIQUE SUR MESURE — PRIORITÉ À LA SINGULARITÉ ET À L'USAGE :\n"
        "Refuse les thèmes de dropshipping/Shopify interchangeables, les mêmes trois cartes "
        "répétées partout, les faux témoignages, les dégradés sans lien avec la marque, "
        "et les boutons décoratifs qui ne font rien. Même une demande simple exige "
        "un travail de direction artistique précis, PAS davantage de complexité.\n"
        f"MARQUE : {brand or 'nom exact dans le cahier des charges'}. "
        f"DOMAINE : {theme['sector']}. "
        f"OBJECTIF CLIENT : {theme['goal']}. "
        f"MATIÈRE VISUELLE PERTINENTE : {theme['visual']}. "
        f"PARCOURS PRINCIPAL : {theme['journey']}.\n"
        "AVANT D'ÉCRIRE LES COMPOSANTS : définis une intention visuelle UNIQUE pour CETTE "
        "entreprise. Rédige DESIGN_INTENT.md dans le projet contenant : cible et besoin, "
        "parti pris graphique distinctif expliqué, hiérarchie et répartition des pages, "
        "système typographique et couleurs, provenance des visuels, micro-interactions "
        "utiles, parcours principal sans impasse, responsive, accessibilité et budget "
        "performance. Ce document est interne au projet et n'apparaît pas sur le site.\n"
        "CONSTRUIS CETTE INTENTION : composition éditoriale originale plutôt qu'un empilement "
        "de sections à cartes; vrais détails métier; contraste et rythme; visuels "
        "soigneusement cadrés; texte français naturel; composants fonctionnels. "
        "Chaque clic mène à une destination cohérente ou fournit un retour compréhensible; "
        "les formulaires valident et indiquent clairement leur comportement réel; "
        "les CTA et les pages n'inventent jamais d'action accomplie. Navigation clavier "
        "et focus visibles, chargements et états vides soignés. Animations discrètes "
        "par transform/opacity et transitions cohérentes, avec prefers-reduced-motion. "
        "Réserve les effets 3D/PBR complexes aux concepts où ils renforcent l'identité et "
        "l'usage, pas à tous les projets.\n"
        "EXAMEN AVANT LIVRAISON : compare le rendu du site à son intention de marque. "
        "Peut-on remplacer le nom par celui d'un concurrent sans voir de différence ? "
        "Si oui, reconstruis le design. Vérifie chaque lien, chaque bouton, la "
        "réservation, la navigation multi-pages, le mobile et le contraste. "
        "Ne te contente pas de dire que l'interface est belle : corrige les fichiers."
    )
