# LocalAiWeb — Création hybride, photos automatiques et 3D

## Fonctionnement

L'interface reste inchangée : conversation à gauche, prévisualisation complète à droite et trois vues ordinateur/tablette/téléphone. LocalAiWeb demande au maximum deux précisions initiales concernant **l'esthétique**, et seulement si le brief est ambigu.

Le moteur privilégie les agents de programmation installés et authentifiés, dans cet ordre :
1. **Claude Code** (CLI `claude`) ;
2. **Codex** (CLI `codex`) ;
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
