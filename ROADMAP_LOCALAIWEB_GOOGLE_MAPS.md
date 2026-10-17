# Phase finale — Création de sites à partir d'une entreprise sur Google Maps

**État : spécification de la phase future. NON implémenté dans cette version.**
L'interface actuelle de création et de sélection de projets reste inchangée.

## Expérience visée

Dans le gestionnaire de projets LocalAiWeb, proposer plus tard un parcours
« Créer depuis Google Maps ». L'utilisateur tape un nom d'établissement ou
une ville, parcourt des résultats sur une carte, puis **sélectionne une fiche
précise**. LocalAiWeb présente les informations fournies par l'API Google
Places (sous réserve des champs autorisés et disponibles) et les données à
confirmer : nom, secteur d'activité, adresse, horaires, site déjà existant,
moyens de contact.

L'IA analyse l'activité **sans prétendre connaître des informations privées**
et propose :
- un plan de pages proportionnel aux besoins de l'établissement ;
- une direction artistique originale, dédiée à sa clientèle et à son domaine ;
- les services présentés comme confirmés seulement après vérification ;
- les images appropriées : fichiers sous licence fournis par l'entreprise,
  ou illustrations générées par l'IA identifiées comme telles ;
- les parcours pratiques : réservation, contact, itinéraire, catalogue
  ou commande, uniquement avec des intégrations réellement disponibles.

### Questions de préparation

**Indispensables :** identifier avec certitude la fiche choisie ; définir
l'objectif principal (ex. présenter/recevoir des réservations/vendre) ;
valider les informations d'entreprise reprises ; confirmer la qualité
du lien avec l'entreprise et l'autorisation avant toute publication en
son nom. Une simple démonstration privée peut être créée sans prétendre
être le site officiel d'un tiers.

**Recommandées, non bloquantes :** palette et ton souhaités, inspiration
artistique, public prioritaire, photographies et logo officiels,
prestations détaillées, intégration de prise de rendez-vous.

Lorsqu'un détail manque, l'IA propose des hypothèses **marquées à confirmer**
ou pose une question courte. Elle ne fabrique ni disponibilités réelles,
ni tarifs, ni réalisations client, ni faux avis Google.

### Intégration API et limites

Utiliser la Google Maps Platform officielle (Places API / recherche de lieux,
Place Details, éventuellement carte JavaScript). Une clé API, des quotas et
éventuellement une facturation configurés explicitement sont nécessaires.
Limiter les champs demandés et les appels pour maîtriser le coût.
Respecter les conditions de Google Maps Platform : attribution, affichage,
mise en cache et réutilisation des photos/contenus. Ne pas contourner l'API
par extraction automatisée du site Google Maps.

Ne pas contacter les entreprises, leur envoyer des sollicitations en série,
revendiquer leur identité, ni publier leur site sans commande explicite et
autorisation appropriée.

**Ordre de livraison :** terminer l'éditeur, la sélection d'éléments, les
pages multiples et la direction artistique sur mesure ; vérifier ensuite
ces fonctions sur des projets réels ; seulement après, intégrer ce parcours
Google Maps.
