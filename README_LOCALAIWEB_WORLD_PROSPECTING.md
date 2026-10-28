# LocalAiWeb — Carte mondiale de prospection professionnelle

## Accès
Depuis l'éditeur LocalAiWeb, une nouvelle **icône planète** est placée à droite
des outils de l'aperçu (curseur, œil, ZIP). Elle ouvre le sélecteur d'établissements
déjà présent au lancement des projets Pro, avec maintenant un cadrage initial
à l'échelle mondiale et **plus de 80 métiers regroupés par familles**.

Le champ « Rechercher un métier dans la liste » filtre les options. Après
avoir choisi un métier, zoomer sur une région et cliquer explicitement sur
« Afficher les établissements dans cette zone ». Les résultats sont affichés
dans une liste et par marqueurs sur la carte. Une recherche par nom de ville
ou établissement reste disponible. **La carte n'affiche pas instantanément
toutes les entreprises de la planète** : les lieux dépendent de la couverture
OpenStreetMap et des limitations des API communautaires.

## Fiche professionnelle

La sélection affiche les **renseignements professionnels publiés** dans
OpenStreetMap : raison commerciale, type d'activité, localisation, horaires,
site web, téléphone professionnel ou courriel de l'établissement, lorsqu'ils
existent. Leur exactitude doit être vérifiée.

Pour des fiches localisées en France, une action **facultative et explicite**
permet de rechercher dans l'API Recherche d'entreprises de l'État. La liaison
n'est admise qu'en cas de correspondance forte sur le nom commercial et la
localisation de l'établissement. La fiche peut alors présenter le SIREN,
l'activité NAF, la raison sociale et les noms/fonctions des **dirigeants**
professionnellement déclarés. Un dirigeant n'est pas nécessairement le
propriétaire. Pas de recherche de profils privés, pas d'adresses
personnelles, de coordonnées privées ni de dates de naissance.

Aucune recherche officielle ne part en arrière-plan sans sélection.
Les informations impossibles à confirmer ne sont pas utilisées comme des faits.

## Création de la maquette

Après avoir choisi un établissement, cliquer sur « Créer la première maquette ».
LocalAiWeb crée une sauvegarde **Pro** au nom de l'entreprise et ouvre l'éditeur,
où Claude Code/Codex (s'il est installé et connecté) se charge de la génération.
Le brief inclut les informations de la carte et les renseignements légaux
confirmés dans la mesure où ils sont pertinents et disponibles.

Le résultat est une **maquette privée et non officielle**. Le logiciel ne
démarche aucun client automatiquement et n'envoie aucun message commercial.
La publication en tant que site officiel exige une confirmation d'autorisation,
et les informations, photos et fonctionnalités doivent être validées.

## Intégrations et limites

- Leaflet + OpenStreetMap, Photon et Overpass pour les données de commerces
  disponibles. Utilisation uniquement sur demande, rayon limité, temporisation
  et cache. Les APIs publiques n'ont pas d'engagement de disponibilité ni
  de couverture mondiale exhaustive.
- Option Google Maps/Places disponible uniquement avec la configuration de
  clés officielles ; des frais et restrictions d'usage peuvent s'appliquer.
- Enrichissement des entreprises françaises :
  https://recherche-entreprises.api.gouv.fr/docs/
- Licence OSM, cartes et attribution : https://www.openstreetmap.org/copyright
- Politique des serveurs de tuiles : https://operations.osmfoundation.org/policies/tiles/

**Mise à jour logicielle :** le bouton existant « ↻ Mettre à jour » conserve
sa procédure sécurisée (vérification de l'archive, démarrage contrôlé et
tentative de restauration en cas d'échec). La compilation Windows comprend
le contrôle de démarrage du binaire PyInstaller. Le fonctionnement sur le
poste utilisateur nécessite un test réel après installation.

Pour un usage intensif de prospection à grande échelle, remplacer
les instances communautaires OSM par des fournisseurs adaptés et vérifier
les règles de protection des données et de prospection applicables.
