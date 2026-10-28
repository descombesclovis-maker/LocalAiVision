# LocalAiWeb — Fond Google Maps officiel, petits commerces et création libre

## Carte Google Maps : ce qu'elle fait réellement

Lorsque tu fournis une clé officielle Google Maps JavaScript, la **carte de fond**
devient la vraie carte Google Maps, avec ses routes, villages, zooms et attributions.
Les **points verts commerciaux** superposés proviennent d'une source indépendante,
réutilisable pour la prospection : l'annuaire professionnel officiel français
(Sirene / API Recherche d'entreprises) et, si nécessaire, OpenStreetMap.

Ce choix protège les projets commerciaux : Google Maps Platform interdit
d'extraire et de stocker ses fiches professionnelles pour bâtir un annuaire de
prospects ou produire du contenu dérivé. Le **catalogue d'entreprises n'est
pas une copie de Google Places**.

La carte géographique française charge progressivement des zones réelles ;
en se rapprochant d'une ville, elle charge jusqu'à **trois pages de 25
résultats** de l'annuaire pour les commerces, artisans, restaurants et services
locaux. Le nombre effectivement affiché peut être inférieur en fonction des
données disponibles, du géocodage et de la source. Aucun point inventé.

## Activation du fond Google Maps officiel

Google Maps Platform est **distinct de ChatGPT Plus**. L'intégration reste
désactivée tant que tu n'as pas choisi volontairement d'activer la facturation
Google Cloud. Le programme n'active aucune facturation à ta place.

1. Créer un projet Google Cloud, activer facturation et budgets/alertes.
2. Activer **Maps JavaScript API** (Places API n'est PAS nécessaire pour la
   carte des prospects professionnels, qui utilise les données publiques).
3. Créer une clé **navigateur**, restreinte à Maps JavaScript API et à tes
   référents autorisés (par défaut `http://127.0.0.1:3000/*` et
   `http://localhost:3000/*`).
4. Dans PowerShell, définir ta propre clé :
   ```powershell
   [Environment]::SetEnvironmentVariable('LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY','TA_CLE_NAVIGATEUR','User')
   ```
   Ne place jamais ta vraie clé dans un commit GitHub ou dans un chat.
5. Fermer totalement LocalAiVision, rouvrir la nouvelle build et lancer
   LocalAiWeb → Carte. Si la clé Google n'est pas valide, le logiciel revient
   automatiquement au fond de carte public existant.

**Important :** Google Maps peut être facturé en fonction des chargements,
même si les **données d'entreprises** proviennent de l'annuaire public.
Consulte la tarification officielle et les conditions applicables à un compte EEE.

Documentation :
- https://developers.google.com/maps/documentation/javascript/load-maps-js-api
- https://cloud.google.com/terms/maps-platform/eea
- https://recherche-entreprises.api.gouv.fr/docs/

## Création d'une maquette Pro

La fiche carte reste simple : nom, activité, adresse, SIRET, téléphone, e-mail,
horaires et état de présence du site web quand ces informations existent.
**« Site non renseigné » ne signifie jamais « aucun site ».**

Le bouton en bas « Créer un site pour cette entreprise » ouvre l'éditeur et
une **fenêtre facultative de direction créative**. Elle permet de choisir
esthétique, couleurs, typographie, composition, animations, mouvements
cinématiques, profondeur 3D, interactions, textures, visuels, contraintes
mobiles et instructions libres. Ces choix sont sauvegardés et transmis à Codex.

Dans tous les autres cas, **le chat commence totalement vide**. Il n'y a
pas de questionnaire initial obligatoire, pas de boutons de prompts
suggérés, pas de « Signature 3D » ni de bulles de l'agent. Tu communiques
avec Codex par tes propres messages. Les informations de statut et les
erreurs restent visibles hors du chat.

Les anciens projets et médias ne sont pas écrasés. Les coordonnées
professionnelles, droits d'auteur, autorisations de publication et données
commerciales doivent toujours être vérifiés.
