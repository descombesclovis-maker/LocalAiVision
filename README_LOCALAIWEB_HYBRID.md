# LocalAiWeb — Création hybride, photos automatiques et 3D

## Fonctionnement

L'interface reste inchangée : conversation à gauche, prévisualisation complète à droite et trois vues ordinateur/tablette/téléphone. LocalAiWeb demande au maximum deux précisions initiales concernant **l'esthétique**, et seulement si le brief est ambigu.

Le moteur privilégie les agents de programmation installés et authentifiés, dans cet ordre :
1. **Codex** (CLI `codex`) : priorité à l’abonnement déjà connecté ;
2. **Claude Code** (CLI `claude`) ;
3. modèle local existant en secours (génération HTML/CSS/JS).

L'agent cloud lit/modifie les fichiers du site. Il n'est **pas** connecté automatiquement sans installation et authentification, et un abonnement/API du fournisseur peut entraîner des frais.

## Photos et visuels produits — automatiques

Avant un premier site, LocalAiWeb tente de créer jusqu'à trois images illustratives (photo de campagne + deux photos de produits) via le workflow **ComfyUI déjà installé**. Les images sont enregistrées uniquement dans `localaiweb/projects/<id>/site/assets/`, et leur chemin exact est donné à l'agent de développement. Les médias validés existants sont réutilisés plutôt que régénérés à chaque message.

Le workflow photo actuel reste **SDXL** tant que le modèle FLUX.2 Klein n'est pas configuré. Si ComfyUI n'est pas prêt, le logiciel peut utiliser une API images OpenAI uniquement si l'utilisateur a **volontairement** configuré `OPENAI_API_KEY` et `LOCALAIWEB_ALLOW_PAID_IMAGES=1`. Le programme ne crée jamais de photos fictives et explique leur absence.

Ces images sont **illustratives** : elles ne représentent pas nécessairement les vrais SKU, stocks, couleurs ou caractéristiques commercialisés. Les prix et paiements réels doivent être connectés à un catalogue et un prestataire fiables.

## Installer FLUX.2 Klein 4B dans ComfyUI (recommandé pour une RTX 3060 12 Go)

Modèle recommandé : **FLUX.2 [klein] 4B distilled (FP8)**, sous licence Apache 2.0. Le fabricant indique un ordre de grandeur de **8,4 Go de VRAM** pour sa version 4B ; la consommation réelle dépend de ComfyUI, des textures, du modèle d'encodage et du déchargement mémoire.

1. Depuis la copie source de LocalAiVision, exécuter **INSTALLER_FLUX2_KLEIN_4B.cmd** et indiquer le dossier ComfyUI existant. Il demande confirmation et vérifie l'empreinte SHA-256 du modèle principal. Alternative : télécharger manuellement les trois fichiers ci-dessous.
2. Mettre ComfyUI à jour, puis ouvrir **Workflow Templates → Images → Flux.2 Klein 4B → Text to Image**.
3. Placer les trois fichiers de la version FP8 dans leurs dossiers :
   - `models/text_encoders/qwen_3_4b.safetensors`
   - `models/diffusion_models/flux-2-klein-4b-fp8.safetensors`
   - `models/vae/flux2-vae.safetensors`
4. Ouvrir le workflow et vérifier **une génération locale**. Les modèles source occupent plusieurs Go et peuvent prendre du temps à télécharger.
5. Exporter le workflow au format API et l'importer dans LocalAiVision sous un nom contenant **Flux2 Klein T2I**. LocalAiWeb le détecte automatiquement ; la variable optionnelle `LOCALAIWEB_IMAGE_WORKFLOW` permet de forcer un workflow précis. Si le modèle n'est pas prêt, le moteur conserve SDXL.

Référence officielle : https://docs.comfy.org/tutorials/flux/flux-2-klein

## Qualité du code et rendu

L'agent modifie de vrais fichiers, puis le programme effectue des contrôles de syntaxe, de compilation, de prévisualisation et de fidélité aux exigences (couleurs, nom, produits, navigation). En cas de défaut détecté, une seconde passe de correction est lancée.

Les projets React/Vite sont compilés avec un **base path relatif**, indispensable pour la prévisualisation embarquée sous `/web-preview/<id>/`.

**Limite honnête** : ces contrôles ne notent pas encore automatiquement la beauté de la page à partir de captures d'écran. La qualité « Claude/Blink/Emergent » dépendra du modèle cloud connecté, du brief, des assets et de la validation visuelle sur des projets réels.

## Éviter les coûts inutiles

- La génération d'images cloud n'est pas activée sans consentement/configuration explicites.
- Les visuels existants ne sont pas regénérés à chaque itération.
- Les modèles payants de programmation sont utilisés seulement lorsqu'ils sont déjà installés et authentifiés.
- Le projet et les fichiers de modèles/photos restent séparés des sauvegardes de LocalAiVision.


## Installer/activer l'agent développeur cloud

Claude Code : installer la CLI officielle puis lancer `claude auth login` dans un terminal Windows. Codex : installer la CLI officielle puis lancer `codex login`. Au lancement suivant, LocalAiWeb vérifie les authentifications existantes ; aucun compte n'est créé à votre place.

Un agent peut exécuter npm install/build dans le dossier du projet. Examiner les dépendances et accès accordés avant d'exécuter un code de provenance inconnue ; ne jamais renseigner de clés dans le code côté navigateur.



## Nouveau gestionnaire de projets — ouverture façon ComfyUI

Cliquer sur **Accéder à LocalAiWeb** ouvre désormais la bibliothèque `/localaiweb`.
Elle contient tous les projets LocalAiWeb, avec leurs noms, dernière modification,
recherche et aperçu miniature lorsque des captures existent. **Nouveau projet**
demande seulement un nom. Choisir une carte ouvre
`/localaiweb/editor?id=web-...` avec **le bon historique et les bons fichiers**.
Rafraîchir l'éditeur ne crée pas de nouveau projet. La flèche à gauche du titre
revient à la bibliothèque. Rien n'est mélangé avec les créations LocalAiVision.

## Nouvelle méthode de génération agentique

Dans la version précédente, en l'absence d'un agent cloud connecté, LocalAiWeb
pouvait passer silencieusement au générateur HTML local et produire des maquettes
peu professionnelles. **Ce repli silencieux est désormais désactivé.**

Le fonctionnement normal repose sur un **Claude Code ou un Codex authentifié**.
L'agent réalise le site sur le disque dans le projet courant, puis :

1. Planifie la mise en page, les contenus et les interactions.
2. Crée les fichiers et utilise les visuels automatiquement générés.
3. Installe les dépendances nécessaires et construit le site réel (Vite/React ou HTML).
4. Vérifie les exigences, les erreurs de syntaxe et la compilation.
5. Ouvre le site dans un navigateur local : **Playwright** si présent, sinon le
   **Microsoft Edge/Google Chrome headless** déjà installé sous Windows.
6. Prend des captures ordinateur/tablette/téléphone, les confie à l'agent
   pour une vraie **revue visuelle**, puis relance les vérifications.
7. Conserve le site, son historique et une miniature du rendu dans son projet.
   Les captures de contrôle sont exclues du ZIP exporté et des commits Git.

Si aucun moteur professionnel n'est connecté, le chat indique clairement
les étapes de connexion au lieu de prétendre qu'une page HTML générique est
une création premium. Il reste possible d'autoriser volontairement l'ancien
moteur local avec `LOCALAIWEB_ALLOW_LOCAL_FALLBACK=1` ou en sélectionnant
`ai_provider=local` dans les paramètres projet.

L'inspection **Playwright** fournit des vérifications d'erreurs JavaScript et
de débordement mobile. Le mode Edge/Chrome sans Playwright capture seulement
des images que l'agent IA peut analyser : il ne prétend pas avoir exécuté
tous les tests fonctionnels. Si aucun navigateur n'est disponible, cette
limitation est explicitement affichée.

La vérification automatique ne remplace pas un test avec **un vrai compte
Cloud Claude/Codex**, les ressources médias et une validation du site par
son propriétaire. Notre architecture s'inspire de la méthode d'agents de
développement, sans copier le code propriétaire ni garantir les résultats
visuels d'un éditeur tiers.

**Le logiciel ne publie jamais automatiquement** les sites : la mise en ligne
reste une commande explicite dans le chat, vérifiée avant déploiement.
