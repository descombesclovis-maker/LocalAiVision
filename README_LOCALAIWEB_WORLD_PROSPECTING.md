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


## Évolution carte violette (28 octobre 2026)

- Ouverture centrée sur la France, carte grand format sans saisie de société,
  menu de métiers ou panneau latéral permanent.
- Petits points **violets pleins** correspondant uniquement aux établissements
  dont les champs de site Internet les plus courants sont absents d'OSM.
  L'absence d'information OSM **ne confirme pas l'absence réelle de site**.
- Un aperçu initial réparti sur de nombreuses villes françaises, y compris
  des agglomérations secondaires et la Corse, est chargé automatiquement.
  Cet aperçu reste partiel : le logiciel ne dispose d'aucun annuaire exhaustif
  de toutes les sociétés françaises ou mondiales.
- Un zoom permet de charger les établissements autour de la ville ou, dans
  les quartiers suffisamment zoomés, ceux de la zone exacte visible.
  Requêtes bornées, cache, limitation de fréquence et déchargement de marqueurs
  lointains pour conserver les performances.
- Un clic sur un prospect ouvre la fiche professionnelle, les informations
  accessibles et un lien de **recherche manuelle** pour vérifier l'existence
  éventuelle d'un site. Ce lien ne constitue pas une vérification automatique.
- Le bouton de création ouvre un projet **Pro** privé comme auparavant.
- **Claude Code CLI** devient le moteur par défaut des projets Pro et Libre.
  Il doit être installé et authentifié sur le PC qui exécute LocalAiVision.
  Le logiciel signale l'indisponibilité de Claude au lieu de produire en silence
  un site bas de gamme par un autre modèle. Les projets configurés explicitement
  pour un autre moteur conservent cette option.

**Limite importante :** afficher l'intégralité des entreprises de France sur
un seul écran et vérifier automatiquement leur absence de site exige un index
professionnel dédié, maintenu et exploitable (données, infrastructure et
licences). Ni une requête globale Overpass, ni un échantillon OSM ne peuvent
prétendre fournir ce résultat. La carte indique donc les données comme
partielles et invite à poursuivre l'exploration par zone.
