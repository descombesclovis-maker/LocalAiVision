# LocalAI Studio — Web + Vision

**LocalAI Studio** est une application Windows unique qui ouvre deux espaces de travail distincts, reliés par une bibliothèque de marques et un parcours commercial commun.

L'exécutable reste nommé `LocalVisionAI.exe` pour préserver les mises à jour et les raccourcis existants. La fenêtre Windows est désormais nommée **LocalAI Studio**.

## Les deux univers

À l'ouverture, `http://127.0.0.1:3000/` ou `/studio` affiche le choix des deux univers :

- **LocalAiWeb** (`/localaiweb`) : bibliothèque de projets **libres** et **clients**, création de sites par Codex, aperçu, édition visuelle, sauvegardes, export ZIP, carte de prospection, CRM, devis, factures et publication explicite.
- **LocalAiVision** (`/localaivision`) : ComfyUI + modèles locaux, chat et bibliothèques photo/vidéo, styles, workflows, retouches et espace isolé inchangés. Un atelier **Publicité** permet de préparer une campagne à partir d'une marque et d'exporter une version avec son véritable logo.

La navigation **Univers** et **LocalAI Studio** permet de revenir à l'accueil sans supprimer les projets.

## Marques et projets clients

- Ouvrir **Identités de marque** dans LocalAiWeb ou `/studio/brands`.
- Enregistrer le nom réel de l'entreprise, son activité, son slogan, ses couleurs, son public, son message d'action et un logo **PNG/JPEG/WebP fourni avec autorisation**.
- Dans un projet LocalAiWeb, sélectionner la marque dans l'en-tête : une copie privée du logo est rangée dans les ressources du projet et l'agent reçoit les informations de marque lors de la prochaine génération.
- Dans LocalAiVision, cliquer **Publicité**, choisir cette même marque, le format **9:16, 1:1 ou 16:9**, l'objectif et le média. La génération utilise les workflows existants et les couleurs de marque comme direction artistique.
- Le **logo officiel et les textes sont composés après génération**. Le média original est conservé. Les images publicitaires utilisent Pillow ; les vidéos nécessitent **FFmpeg** sur le PC. Une erreur d'export ne marque jamais la génération comme réussie.
- Les versions publicitaires peuvent être copiées dans les ressources d'un projet LocalAiWeb avec **Ajouter à un site**.

La création de sites reste non publiée par défaut. Vérifier les informations des entreprises, les droits sur les logos, les photos et les allégations publicitaires avant livraison.

## Génération persistante et bibliothèque

L'éditeur Web lance sa génération dans un worker côté **PC** : quitter l'éditeur ne l'arrête pas, tant que LocalAI Studio et Windows continuent de fonctionner. La pastille animée en haut à droite affiche les travaux Web actifs et la file d'attente photo/vidéo de ComfyUI. Cliquer dessus retourne au projet ou à l'univers en cours.

La bibliothèque de sites fournit deux collections, miniatures disponibles, recherche, actualisation, réessai en cas d'échec et accès direct au projet conservant son propre historique. Elle n'affiche ni pourcentage inventé ni message de réussite en l'absence de fichiers.

## Installation et limites

Installer la dernière archive de [GitHub Releases](https://github.com/descombesclovis-maker/LocalAiVision/releases/latest), extraire puis lancer `LocalVisionAI.exe`. Le PC doit disposer des modèles et outils nécessaires. Codex requiert une connexion/authentification réelle. Les rendus photoréalistes et la vitesse sur GPU RTX 3060 dépendent des modèles, résolutions et étapes ; les tests logiciels ne garantissent pas un rendu visuel supérieur sans essai réel.

Les outils de publication et les connecteurs restent configurables et doivent être autorisés avant tout déploiement. Aucune activité ni marque n'est automatiquement publiée à l'extérieur.

Pour un accès privé depuis l'iPhone, lire [MOBILE_SETUP.md](MOBILE_SETUP.md). Le PC doit rester allumé.

## Tests

```bash
python -m unittest discover -s tests -v
node --check local_app/web/localaiweb.js
node --check local_app/web/localaiweb-brand.js
node --check local_app/web/studio-activity.js
node --check local_app/web/studio-brands.js
node --check local_app/web/studio-ads.js
```

La CI exécute les tests et compile un exécutable Windows, puis réalise les tests de démarrage et de mise à jour. Les tests fonctionnels sur les véritables modèles locaux et les aperçus réels restent nécessaires pour valider la qualité finale.

Documentation complémentaire : [README_LOCALAIWEB_HYBRID.md](README_LOCALAIWEB_HYBRID.md), [README_LOCALAIWEB_PRO_MAP.md](README_LOCALAIWEB_PRO_MAP.md), [AGENTS.md](AGENTS.md).
