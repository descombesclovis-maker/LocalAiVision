# LocalAiWeb : Google Maps officiel, petits commerces, conception libre

## Carte officielle Google Maps : configuration indispensable

L'interface de la carte, sa fiche entreprise et son bouton « Créer un site pour cette entreprise » ne changent pas. Lorsque Google Maps est **configuré officiellement**, l'application utilise les vraies tuiles Google Maps et Google Places (New) pour charger de **petits commerces, salons, boulangeries, artisans et services** au lieu de se limiter aux grosses entreprises. Sans compte Google Maps Platform, une carte publique de secours reste disponible : **ce n'est pas Google Maps**.

Google Maps Platform est **distinct de ChatGPT Plus** : Google requiert un projet Google Cloud avec une facturation activée et ses propres clés API. Le logiciel ne crée pas le compte, ne renseigne pas une carte bancaire, ne souscrit pas d'abonnement et n'active aucune API à ta place.

1. Ouvrir Google Cloud Console, créer un projet de cartographie professionnel, et activer la facturation et les budgets/alertes.
2. Activer **Maps JavaScript API** et **Places API (New)** sur le projet.
3. Créer une clé **navigateur**, limitée à *Maps JavaScript API*, et aux référents HTTP du serveur LocalAiWeb (par défaut `http://127.0.0.1:3000/*` et `http://localhost:3000/*`). Pour une application native, vérifier les restrictions et risques de la clé avant déploiement distant.
4. Créer une autre clé **serveur**, limitée à *Places API (New)*. La clé serveur reste **sur le PC**, jamais dans le frontend, jamais commitée sur GitHub.
5. Sur ton compte Windows (PowerShell), définir les variables d'environnement pour les prochains lancements de l'application :

   ```powershell
   [Environment]::SetEnvironmentVariable('LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY', 'COLLER_CLE_NAVIGATEUR', 'User')
   [Environment]::SetEnvironmentVariable('LOCALAIWEB_GOOGLE_PLACES_API_KEY', 'COLLER_CLE_SERVEUR', 'User')
   ```
   Ces commandes affichées sont des **exemples** à exécuter toi-même en remplaçant les valeurs. Ne transmets jamais les vraies clés dans le chat.
6. Fermer complètement LocalAiVision, puis relancer la dernière build Windows et ouvrir LocalAiWeb → Carte. Le fond Google remplace alors automatiquement la cartographie publique. Les petites entreprises autour de la ville ciblée sont découvertes avec l'API Google Places officielle.

### Limites et coûts réels

- Une recherche Google Places Nearby New renvoie **au maximum 20 entreprises**. Notre carte lance au maximum trois segments spécifiques (coiffure/beauté, petits commerces, artisans/services) lorsqu'on se rapproche d'une ville, et elle ne prétend PAS récupérer l'ensemble des entreprises Google Maps.
- Ces appels sont **payants à l'utilisation** selon Google et les champs demandés. Le logiciel ne lance pas un balayage payant de toutes les villes de France. Il laisse l'utilisateur se déplacer dans la carte et plafonne les recherches à quelques segments par zone.
- Aucun filtrage ne peut garantir qu'une entreprise n'a pas de site web : la fiche distingue « site renseigné » et « non renseigné ». La source doit être vérifiée.
- Les données Google Places peuvent être soumises à des règles de mise en cache, de stockage et d'utilisation. Ne pas constituer de copie permanente du répertoire Google ni distribuer des données sans respecter les conditions de licence. Un Place ID peut servir à retrouver une fiche officielle.
- Si aucune clé Google n'est configurée, la carte publique de secours continue de fonctionner sans facturation Google, avec une **couverture partielle** de l'annuaire officiel et d'OSM.
- Même avec les vraies cartes Google, une couverture nationale *exhaustive* en repères Google n'est pas disponible instantanément via Nearby Search. Elle nécessiterait une source légalement réutilisable distincte, une indexation géographique et une infrastructure autorisée.

Documentation officielle : https://developers.google.com/maps/documentation/javascript/load-maps-js-api et https://developers.google.com/maps/documentation/places/web-service/nearby-search et https://developers.google.com/maps/billing-and-pricing

## Création du premier site professionnel

1. Sélectionne un petit commerce sur la carte et clique **Créer un site pour cette entreprise**.
2. Un projet Pro privé s'ouvre dans l'éditeur. Une unique fenêtre de **direction artistique** s'affiche au-dessus de l'éditeur : univers, palette, typographie, composition, effets et cinématiques, profondeur/3D, interactions, textures, visuels, priorité mobile et instructions libres.
3. Les réglages sont facultatifs. **Créer la première maquette** conserve réellement ces choix dans ce projet et les transmet à Codex. **Choisir plus tard** ferme la fenêtre sans lancer une génération.
4. En dehors de cette fenêtre facultative, **le chat est vide**. Écris ce que tu veux : aucune question obligatoire, aucun QCM, aucune réponse préfabriquée, aucune suggestion « Améliorer le rendu », aucun bouton « Signature 3D » dans le chat.
5. Les tests, contraintes de sécurité, protections des données client et obligations légales restent actifs ; ne pas confondre liberté créative et absence de contrôle du code produit.

L'agent Codex ne dispose pas automatiquement des données sensibles des clients ou d'une licence de réutilisation des photographies : le site généré doit vérifier ses sources, clairement identifier une maquette non officielle et ne pas simuler de vrais services commerciaux non connectés.
