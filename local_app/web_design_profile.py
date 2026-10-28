"""Explicit visual direction choices for a prospect site, never a questionnaire.

The modal is a user-selected design specification. It is persisted per project
and supplied to Codex on the first and subsequent generations.
"""
from __future__ import annotations
import re

FIELDS={
 "style":{"auto":"Direction artistique libre","minimal":"Minimalisme architectural",
          "luxury":"Luxe éditorial","boutique":"Commerce chaleureux",
          "editorial":"Éditorial expérimental","futurist":"Futurisme raffiné",
          "artisanal":"Artisanat authentique","cinematic":"Cinématique immersive"},
 "colors":{"auto":"Palette proposée par l'IA","mono":"Monochrome contrasté",
           "ink":"Noir / ivoire","cream":"Crème / sable","copper":"Noir / cuivre",
           "forest":"Vert profond","marine":"Bleu nuit","pastel":"Pastels",
           "bold":"Couleurs vives contrastées"},
 "typography":{"auto":"Typographie selon l'univers","serif":"Serif expressive",
               "sans":"Sans-serif premium","display":"Typographie graphique",
               "humanist":"Humaniste organique"},
 "layout":{"auto":"Composition libre","editorial":"Grille éditoriale",
           "gallery":"Galerie immersive","asymmetric":"Asymétrie soignée",
           "fullbleed":"Pleine largeur cinématique","ecommerce":"Boutique détaillée"},
 "motion":{"none":"Sans mouvement superflu","subtle":"Micro-animations légères",
           "smooth":"Animations très fluides","expressive":"Transitions expressives"},
 "cinema":{"none":"Aucune cinématique","scroll":"Récit au défilement",
           "camera":"Mouvements de caméra scénarisés",
           "reveal":"Révélations de scènes et de contenus"},
 "dimension":{"none":"2D exclusivement","depth":"Profondeur 2.5D",
              "interactive":"Objets 3D interactifs","immersive":"Environnement WebGL immersif"},
 "interaction":{"standard":"Navigation et boutons classiques","parallax":"Parallaxe tactile",
                "magnetic":"Interactions magnétiques","gesture":"Gestes et micro-interactions"},
 "visuals":{"verified":"Ressources professionnelles disponibles",
            "illustrative":"Illustrations originales","generated":"Visuels IA illustratifs",
            "licensed":"Photographies sous licence compatible"},
 "surfaces":{"plain":"Surfaces nettes","glass":"Verre et transparence",
             "paper":"Papier et grain organique","material":"Matières et textures réalistes"},
 "mobile":{"balanced":"Équilibre mobile/ordinateur","mobilefirst":"Mobile d'abord",
           "performance":"Performances et accessibilité d'abord"},
}

def validate(profile):
    if not isinstance(profile,dict):
        raise ValueError("Options graphiques invalides.")
    if set(profile)-set(FIELDS)-{"notes"}:
        raise ValueError("Option de personnalisation inconnue.")
    result={}
    for field,choices in FIELDS.items():
        value=profile.get(field,next(iter(choices)))
        if not isinstance(value,str) or value not in choices:
            raise ValueError("Choix de direction artistique invalide : "+field)
        result[field]=value
    notes=profile.get("notes","")
    if not isinstance(notes,str) or len(notes)>1200:
        raise ValueError("La consigne créative doit contenir 1 200 caractères maximum.")
    result["notes"]=re.sub(r"[\x00-\x08\x0b-\x1f]"," ",notes).strip()
    return result

def prompt(profile):
    if not profile:return ""
    chosen=validate(profile)
    rows=["DIRECTION VISUELLE CONFIRMÉE PAR L'UTILISATEUR :"]
    for key,choices in FIELDS.items():
        rows.append("- "+key+" : "+choices[chosen[key]])
    if chosen["notes"]:rows.append("- Consigne créative libre : "+chosen["notes"])
    rows += [
      "Traduis ces options en vrai design, animation et comportement des pages.",
      "Toutes les animations demandées nécessitent une implémentation réelle, avec "
      "rendu responsive et préférence de réduction des mouvements respectée.",
      "Ne pas inventer de logo officiel ni de détails commerciaux non vérifiés.",
      "Les nouvelles demandes de l'utilisateur dans le chat prévalent sur ces choix."
    ]
    return "\n".join(rows)
