# LocalAiWeb — récupération Codex, commerces indexés et opportunités du jour

## 1. Erreur Codex « rejected: blocked by policy »

Le mécanisme d'écriture directe peut être refusé par l'environnement Windows.
Pour la **première maquette sur Windows**, LocalAiWeb demande désormais à Codex
de produire un ensemble de fichiers JSON **sans commandes shell**, dans son
sandbox en lecture seule. Le logiciel contrôle les chemins et les contenus
avant de créer les vrais fichiers du site dans le dossier du projet.

En cas d'échec d'une modification classique avec une erreur de politique
d'exécution, un essai de secours sécurisé est lancé automatiquement.
Aucune option « danger-full-access » n'est activée. La connexion Codex
(ChatGPT Plus) doit toujours être effective sur l'ordinateur.

## 2. Quitter la page sans interrompre la génération

Le traitement de Codex fonctionne dans un thread **du serveur local**,
indépendamment de l'onglet. Il continue si tu fermes **l'onglet du navigateur**
ou navigues vers un autre projet **tant que le logiciel et son serveur
continuent de fonctionner sur le PC**. En rouvrant le projet, la progression
est récupérée. Les états de traitement sont également conservés dans les
données locales, et une fermeture du logiciel pendant un traitement est
signalée comme interruption au prochain lancement.

**Ce n'est pas un service cloud : une fermeture complète du logiciel, une
mise en veille du PC, un redémarrage Windows ou une coupure d'alimentation
interrompt Codex.** Une reprise automatique de son exécution après extinction
du PC exigerait une queue durable et un exécuteur externe.

## 3. 5 000 commerces, sans inventer de résultats

L'interface n'invente aucun commerce. Elle conserve désormais les vrais
établissements rencontrés dans un index SQLite privé sur ton ordinateur,
et réaffiche les points enregistrés lors des prochaines ouvertures.
L'index supporte **plus de 5 000 fiches** : un test automatique en charge
vérifie 5 005 enregistrements et les groupes interactifs.

La couverture nationale est alimentée progressivement par de nombreuses
villes françaises et l'API officielle (plusieurs pages de résultats par
zone). **Capacité pour plus de 5 000 enregistrements ne veut pas dire
5 000 résultats déjà récupérés** : tout dépend des établissements
réellement géocodés et publiés, du débit autorisé par l'API et de la durée
du chargement. Pour une couverture vérifiée de tous les commerces français,
il faudra un import du stock géocodé Sirene officiel (volumineux) et un
enrichissement responsable des enseignes ; ce stock n'est pas inclus dans
l'archive Windows.

## 4. Suggestions quotidiennes de 5 commerces

Au-dessus de la carte, cinq fiches sélectionnées automatiquement sont
affichées à partir **des entreprises réelles déjà indexées**, sans
rechercher de données personnelles privées. L'algorithme transparent
favorise certains secteurs locaux, les informations de localisation
exploitables, la récence **seulement lorsqu'une date est explicitement
renseignée**, et l'absence de site indiqué dans la source (qui n'est
jamais une preuve d'absence de site).

Cliquer une suggestion ouvre la fiche et recentre la carte. Les cinq
propositions sont recalculées en fonction de la date locale à chaque
ouverture et lorsque l'index s'enrichit. Aucun message n'est envoyé
automatiquement aux commerces : il faut vérifier les informations et
contacter les personnes professionnellement, dans le respect du RGPD.

## 5. Photo de boutique

La fiche peut afficher une **photographie réellement renseignée dans
OpenStreetMap/Wikimedia Commons**, avec indication de provenance. Si
aucune photographie utilisable n'est connue, une mention le dit
clairement. Le logiciel **n'invente pas une photo de la devanture** et
ne copie pas automatiquement les photographies d'autres plateformes.
Avant une publication commerciale, vérifier les droits d'usage.

## 6. Popup esthétique

Les menus déroulants sont remplacés par des **cases facultatives
indépendantes**, avec des noms faciles à comprendre et une courte
description de ce que chaque réglage change : couleurs, polices, cinéma,
animations, 3D, interactions, photos, textures et performance mobile.
Une option libre peut aussi être cochée pour faire prendre en compte des
instructions supplémentaires. Aucun questionnaire dans le chat.

Ces changements sont livrés par le pipeline Windows **après** vérification
de l'ensemble des tests, sans engagement sur un temps fixe de création.
