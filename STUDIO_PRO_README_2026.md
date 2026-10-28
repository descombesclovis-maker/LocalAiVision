# LocalAiVision + LocalAiWeb — Studio intégré (octobre 2026)

## Ce qui fonctionne dans cette version

**Accueil LocalAiVision**
- Identité générale de l'utilisateur sur une surface blanche, transition vers un
  environnement sombre lorsque le champ est activé.
- Entrée LocalAiWeb au centre de l'accueil.
- Menu visible limité à quatre usages : Mes créations, Photo, Vidéo, NSFW.
- Moteurs, réglages, historique et fichiers restent utilisables sans encombrer
  la navigation. Le bouton d'installation PWA a été retiré ; l'installation
  éventuelle reste gérée par le navigateur.
- Galerie des créations avec aperçu, filtrage, suppression confirmée et
  importation **explicite** vers un projet LocalAiWeb existant. L'import est
  une copie locale (ComfyUI/output vers le dossier site/assets/ai), jamais un
  transfert réseau vers Claude ou un lancement de publication.

**LocalAiWeb**
- Bibliothèque des projets Libre et Pro, prévisualisation ordinateur/tablette/mobile,
  modification au chat, sélection de sections, ZIP, carte et outils de publication
  existants conservés.
- Visuels importés dans assets/ai/ retrouvables depuis les fichiers du projet et
  journalisés dans la conversation du site.
- L'application utilise Claude Code par défaut, lorsque installé et authentifié.
  Un site opérationnel doit être testé avec les intégrations réelles nécessaires.

**LocalAiWeb Pro — /localaiweb/clients**
- Portefeuille privé local. Les nouveaux projets Pro sélectionnés sur la carte
  peuvent créer une fiche prospect avec les seules informations professionnelles
  fournies ; les anciennes fiches/projets restent intacts.
- Étapes manuelles : prospect, contacté, devis envoyé, accepté, en production,
  livré, client actif, sans suite.
- Fiches client, contact, adresse de facturation, notes, SIRET, sites reliés.
- Devis PDF numérotés et conservés, avec identité réelle du prestataire et du
  destinataire, postes détectés depuis le site, TVA confirmée et validité.
  Le devis n'est pas accepté automatiquement.
- Factures définitives créées uniquement après validation explicite dans la page
  vente. Elles sont associées au client et projet ; les archives précédentes sont
  listées en lecture seule. Aucune facture n'est créée lors de l'ouverture du hub.
- Les identités de facturation codées en dur ont été retirées. Les vrais éléments
  d'entreprise doivent être fournis par la personne qui émet les documents.

## Invariants de fiabilité

- Le serveur HTTP reste lié à localhost. Aucun appel extérieur ne peut consulter
  le registre sans être sur le poste ou la connexion privée déjà configurée.
- Pas de formulaire factice : un bouton qui affiche une fonctionnalité déclenche
  une action réelle, ou expose explicitement son indisponibilité.
- Importations limitées aux sorties ComfyUI et aux formats multimédias vérifiés,
  avec contrôle du chemin, de l'extension et de la taille. Fichier source intact.
- Aucun devis n'envoie un email, encaisse un paiement ou publie un site.
- Les répertoires des projets et modèles IA ne sont pas détruits par le déploiement.
- Tests Python de fonctionnement, tests de contrat frontend, syntaxe JS,
  puis compilation Windows et test natif après intégration.

## Chantiers ultérieurs (non simulés dans cette version)

1. Capture d'écran réelle de chaque site généré et évaluation visuelle automatique
   par Claude Code sur desktop/tablette/mobile, avec corrections et budget de rendu.
2. Espace client sécurisé pour avis et validation de prévisualisation privée.
3. Suivi de maintenance, hébergement et renouvellements avec rappels fiables.
4. Connexion à une plateforme agréée pour la facturation électronique, selon
   l'applicabilité légale. Un PDF seul ne constitue pas cette connexion.
5. Signature Authenticode de l'exécutable avec certificat d'éditeur légitime.
   Sans certificat, Windows SmartScreen peut avertir : ne pas désactiver Defender.
6. Une carte de prospection réellement exhaustive nécessite des jeux de données
   professionnels licenciés et indexés ; OpenStreetMap est une base partielle.

## Vérification utilisateur

Lancer la nouvelle version, contrôler le premier écran, ouvrir Photo / Vidéo /
NSFW, consulter Mes créations et importer un élément vers un projet existant.
Ouvrir ensuite LocalAiWeb > Clients & devis, enregistrer une fiche, associer un
site, préparer un devis, vérifier le PDF et ne créer une facture qu'après
livraison et vérification. Tester la mise à jour avec une version future.

## Fiabilisation du suivi et audit de livraison
- L'accueil revient toujours en mode neutre : aucune conversation ou
  génération NSFW n'est réutilisée par inadvertance dans le chat principal.
  Le menu Historique montre les conversations standards ; celles de l'espace
  NSFW restent consultables uniquement depuis cet espace.
- Chaque dossier client peut définir une **date de relance**. Le tableau de
  bord signale les relances en retard, celles à effectuer aujourd'hui et
  les prochaines échéances. Aucun email ou SMS n'est envoyé automatiquement.
- Les projets web sont associés à une seule fiche client à la fois, afin de
  prévenir les erreurs d'attribution de livrables et de documents commerciaux.
- Depuis une fiche client associée à un site : **Audit du site** déclenche
  le véritable contrôle technique LocalAiWeb (structure HTML, responsive,
  accessibilité de base, référencement élémentaire, assets locaux et syntaxe
  JavaScript), affiche le score et liste ce qui doit être corrigé. Ce n'est
  pas une certification visuelle, légale ou fonctionnelle des intégrations.
- **Exporter CSV** produit un fichier client local sur action explicite, sans
  envoi à un service externe, avec neutralisation des formules dangereuses
  pouvant se trouver dans des champs importés.
- Un devis généré localement est nommé **Devis préparé**, jamais
  « devis envoyé » : l'émission du PDF ne constitue pas un envoi au client.
