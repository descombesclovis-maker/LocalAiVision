"""Sector-aware public business brief for LocalAiWeb Pro.

No personal profiling. Not a factual claim about clients, revenue, ownership,
special categories or private customer characteristics. Structured guidance
comes from industry/city and public facts supplied by the chosen business.
"""
from __future__ import annotations

from copy import deepcopy

SECTORS=(
 ("coiffure",("hairdresser","coiffeur","barber","9602","96.02"),{
   "audiences":["Habitants du quartier recherchant une prestation et des tarifs clairs",
                "Clients souhaitant réserver rapidement depuis un téléphone"],
   "pages":["Accueil","Prestations & tarifs","Réservation","Réalisations","Accès & contact"],
   "conversion":"Prise de rendez-vous vérifiable, avec disponibilités uniquement si un calendrier réel existe.",
   "seo":"Prestations locales + commune, adresse vérifiée, horaires confirmés, données structurées LocalBusiness."
 }),
 ("restauration",("restaurant","cafe","bar","brasserie","5610","56.10"),{
   "audiences":["Habitants proches comparant les menus et les horaires",
                "Visiteurs de passage recherchant l'accès et le téléphone"],
   "pages":["Accueil","Carte & menus","Réservation","Accès & horaires","Contact"],
   "conversion":"Réserver une table ou appeler ; ne pas afficher des créneaux inventés.",
   "seo":"Cuisine et quartier, horaires documentés, coordonnées, données structurées Restaurant."
 }),
 ("artisanat",("plumber","electrician","craft","artisan","plomb","électric","432","43.2"),{
   "audiences":["Particuliers recherchant un devis détaillé et des réalisations",
                "Professionnels locaux avec un projet d'intervention"],
   "pages":["Accueil","Prestations","Réalisations","Zone d'intervention","Demander un devis"],
   "conversion":"Formulaire de demande de devis réellement relié à un destinataire avec consentement.",
   "seo":"Prestations + zone d'intervention réelle, certifications seulement si prouvées."
 }),
 ("commerce",("shop","bakery","florist","books","butcher","boulanger","commerc","471","47."),{
   "audiences":["Consommateurs locaux vérifiant produits, horaires et itinéraire",
                "Clients qui souhaitent contacter la boutique avant de se déplacer"],
   "pages":["Accueil","Produits","Notre boutique","Accès & horaires","Contact"],
   "conversion":"Contact direct et visite en magasin ; vente en ligne uniquement avec stock/paiement réels.",
   "seo":"Activité et ville, informations de magasin, catalogue sans inventer prix ou stocks."
 }),
 ("services",(),{
   "audiences":["Clients locaux cherchant à comparer les services et les garanties",
                "Personnes souhaitant prendre contact depuis un mobile"],
   "pages":["Accueil","Services","À propos","Réalisations ou références vérifiées","Contact"],
   "conversion":"Une demande de contact opérationnelle et des preuves publiques vérifiées.",
   "seo":"Nom de l'activité et commune, structure de pages claire, métadonnées originales."
 }),
)

def _clean(value,limit=190):
    return " ".join(str(value or "").split())[:limit]

def plan(business):
    if not isinstance(business,dict):
        raise ValueError("Fiche d'entreprise invalide.")
    activity=" ".join(_clean(business.get(key),120)
                      for key in ("category","osm_category","name")).casefold()
    label,guide=next(((label,guide) for label,words,guide in SECTORS if
                       any(token in activity for token in words)),("services",SECTORS[-1][2]))
    verified_public={}
    for field in ("name","address","postcode","city","phone","email","opening_hours","website","category"):
        if business.get(field):
            verified_public[field]=_clean(business[field])
    return {
        "sector":label,
        "public_facts":verified_public,
        "audiences_to_validate":deepcopy(guide["audiences"]),
        "suggested_pages":deepcopy(guide["pages"]),
        "conversion_strategy":guide["conversion"],
        "local_search_strategy":guide["seo"],
        "research_checklist":[
            "Vérifier l'identité de l'établissement à l'adresse choisie et son site officiel.",
            "Confirmer les prestations, tarifs et horaires avant publication.",
            "Vérifier les droits d'usage des photos, témoignages et logos.",
            "Évaluer la concurrence locale uniquement sur des sources publiques fiables.",
            "Identifier les attentes liées au secteur par hypothèses, sans inférer l'âge, "
            "la santé, la religion, l'origine ou la vie privée des clients.",
            "Ne pas attribuer de revenus, performances, faiblesses ou informations personnelles "
            "à une entreprise sans preuve fiable.",
        ],
        "uncertainties":[
            "Absence de site NON confirmée si aucune URL professionnelle n'est renseignée.",
            "Persona et intention de recherche sont des hypothèses métier, "
            "pas des mesures de la clientèle réelle.",
            "Aucun horaire, tarif, avis ou rendez-vous inventé.",
        ],
    }

def direction(business):
    brief=plan(business)
    lines=[
        "ANALYSE COMMERCIALE — hypothèses et faits professionnels publics uniquement.",
        "Secteur probable : "+brief["sector"]+".",
        "Audiences pertinentes à valider : "+" ; ".join(brief["audiences_to_validate"])+".",
        "Structure conseillée : "+" ; ".join(brief["suggested_pages"])+".",
        "Conversion : "+brief["conversion_strategy"],
        "SEO local : "+brief["local_search_strategy"],
        "RECHERCHE CIBLÉE : vérifier le site officiel, les services, les prix, les horaires, "
        "la zone de chalandise et les sources ouvertes si tes outils de recherche sont autorisés. "
        "Ne jamais présenter une hypothèse comme un fait, ne pas créer de fausses informations.",
        "Ne pas collecter de données sensibles ou privées sur le propriétaire, les employés ou les clients.",
    ]
    return "\n".join(lines)
