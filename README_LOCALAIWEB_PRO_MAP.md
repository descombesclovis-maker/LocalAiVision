# LocalAiWeb Pro — Création depuis une entreprise sur une carte

## Nouveau parcours

À l'accueil LocalAiWeb, le bouton **Créer depuis une carte** ouvre une nouvelle
interface comprenant une carte interactive OpenStreetMap et une recherche.
Tu peux rechercher une ville ou un commerce en saisissant son nom et en validant
avec Entrée, déplacer/zoomer la carte, puis cliquer sur **Afficher les
établissements dans cette zone**. Les résultats sont visibles dans une liste
et sous forme de marqueurs sur la carte.

Choisis une **entreprise** (et non une ville), vérifie son nom et son adresse,
puis clique **Créer la première maquette**. LocalAiWeb enregistre un projet
**Pro** au nom de l'établissement, ouvre automatiquement l'éditeur habituel
et lance une première version du site avec l'agent de programmation connecté.
Tu peux ensuite continuer à modifier la maquette grâce au chat, à la sélection
d'éléments dans l'aperçu, aux versions du projet et à ses exports.

Le projet garde les informations cartographiques disponibles ainsi qu'un
brief initial indépendant des projets créés librement.

## Bibliothèque de projets

Les **Projets Libre** apparaissent **au-dessus** des **Projets Pro**.
Les anciens projets restent Libre sans migration ni suppression de données.
Les projets Pro conservent leur propre sauvegarde et ne sont jamais mélangés
aux créations LocalAiVision.

## Premier rendu

Il doit être adapté à l'activité réelle avec une direction artistique originale,
une navigation logique et des fonctionnalités réellement applicables. L'IA
utilise uniquement les informations disponibles : dénomination, secteur,
adresse, téléphone, horaires ou site existant lorsqu'ils sont fournis par la
source. Les champs manquants restent **à confirmer** ; aucun tarif, avis,
prestation ou travail client ne doit être inventé. Les images générées sont
des illustrations, et non des photographies officielles de cette entreprise.

La première maquette est **privée et non officielle**. La mise en ligne au nom
de l'établissement exige une confirmation explicite de ton autorisation et
une vérification des informations utilisées. Les corrections ultérieures
s'effectuent dans l'éditeur existant.

## Fournisseurs cartographiques, confidentialité et limites

- **Carte** : Leaflet 1.9.4, tuiles OpenStreetMap, crédits ODbL affichés.
- **Recherche de ville / nom** : Photon (API communautaire Komoot).
- **Commerces affichés à proximité** : Overpass API, autour de la position
  choisie avec un rayon limité, uniquement après clic.
- Les appels ne sont **jamais déclenchés à chaque touche** ou déplacement
  de carte. Cache de courte durée, limites de zone et temporisation.
- Les services communautaires sont gratuits mais **sans garantie de
  disponibilité**, et ne sont pas adaptés à un volume commercial important.
  Une version à grande échelle devra utiliser des prestataires sous contrat
  ou une infrastructure OSM propre.
- La carte et les recherches nécessitent Internet. L'application ne contourne
  pas l'API officielle de Google et ne gratte aucune fiche Google Maps.
- Aucune clé Google Maps et aucun achat de service payant ne sont nécessaires
  pour le parcours OpenStreetMap de cette version.

Sources et conditions :
- https://www.openstreetmap.org/copyright
- https://operations.osmfoundation.org/policies/tiles/
- https://github.com/komoot/photon
- https://wiki.openstreetmap.org/wiki/Overpass_API

**Rappel :** la réussite d'une compilation et des tests simulés ne garantit pas
qu'un fournisseur cartographique fonctionne partout ni qu'un agent de codage
autonome réussisse toutes les mises en page. Tester la version sur des fiches
réelles, avec le navigateur disponible sur ton PC.
