# LocalAiStudio en local sur Windows : 100 % gratuit, sans API payante

Tout tourne sur votre PC : les sites (Ollama), les photos, les retouches et les pubs (ComfyUI + FLUX), et les vidéos (ComfyUI + Wan 2.2 / LTX-Video).
Configuration visée : Windows 10/11, NVIDIA RTX 3060 12 Go, 32 Go de RAM conseillés, environ 60 Go d'espace disque libre pour les modèles.

---

## 1. Installation automatique (environ 20 min, une seule fois)

1. Décompressez `LocalAiStudio-kit-windows.zip`, par exemple dans `C:\LocalAiStudio`.
2. Faites un clic droit sur `install.ps1` → **Exécuter avec PowerShell**.
   Si Windows bloque le script, ouvrez PowerShell dans le dossier et lancez :
   `powershell -ExecutionPolicy Bypass -File .\install.ps1`
3. Le script installe, via `winget` : Python 3.11, Node.js LTS, MongoDB Community, Ollama et Git.
   Il installe ensuite les dépendances (backend et interface) et télécharge le modèle de texte `qwen2.5-coder:14b`.

## 2. ComfyUI (photos et vidéos)

1. Installez **ComfyUI Desktop** : https://www.comfy.org/download (ou la version portable NVIDIA).
2. Téléchargez les modèles avec `download-models.ps1`. Indiquez le dossier `models` de ComfyUI quand le script le demande.
   Il récupère par défaut :

| Usage | Fichier | Dossier ComfyUI |
|---|---|---|
| Photos (qualité) | `flux1-dev-fp8.safetensors` (≈ 17 Go) | `models/checkpoints` |
| Photos (rapide) | `flux1-schnell-fp8.safetensors` (≈ 17 Go, optionnel) | `models/checkpoints` |
| Vidéo Wan 2.2 | `wan2.2_ti2v_5B_fp16.safetensors` (≈ 10 Go) | `models/diffusion_models` |
| Encodeur Wan | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (≈ 6,7 Go) | `models/text_encoders` |
| VAE Wan 2.2 | `wan2.2_vae.safetensors` | `models/vae` |
| Vidéo LTX (optionnel) | `ltx-video-2b-v0.9.5.safetensors` + `t5xxl_fp16.safetensors` | `models/checkpoints` + `models/text_encoders` |

3. Lancez ComfyUI. Il doit répondre sur http://127.0.0.1:8188 (ComfyUI Desktop utilise parfois le port **8000** : ajustez-le dans **Moteurs**).

## 3. Démarrage au quotidien

Double-cliquez sur le raccourci **LocalAiStudio** du Bureau (créé par install.ps1) ou sur **`start-localaistudio.bat`**. Il démarre MongoDB, Ollama, le backend (port 8001) et l'interface (port 3000), puis ouvre http://localhost:3000.
Lancez ComfyUI à côté pour les photos et les vidéos.

## 4. Réglages dans l'application

Onglet **Moteurs** :
- **Ollama** : `http://localhost:11434`, modèle `qwen2.5-coder:14b` (ou `qwen2.5:14b`, `mistral-small`…). Contexte : 16384, ou 32768 si vous avez 32 Go de RAM.
- **ComfyUI** : adresse, préréglage photo (FLUX dev / FLUX schnell / SDXL), préréglage vidéo (Wan 2.2 / LTX). Le bouton **Tester** affiche votre GPU et signale les fichiers manquants.
- **Workflow personnalisé** : dans ComfyUI, *Workflow → Export (API)*, puis collez le JSON. Placeholders disponibles :
  `{{PROMPT}}` `{{NEGATIVE}}` `{{WIDTH}}` `{{HEIGHT}}` `{{SEED}}` `{{LENGTH}}` `{{IMAGE}}`.

## 5. Ce qu'il faut savoir (qualité et temps sur RTX 3060)

| Moteur | Temps indicatif | Qualité par rapport aux API payantes |
|---|---|---|
| Site 5-7 pages (Qwen 14B) | 10 à 25 min | Bonne ; Claude reste meilleur sur les sites très complexes |
| Photo FLUX dev 1024 px | 40 à 90 s | Très proche de Nano Banana |
| Photo FLUX schnell | 8 à 15 s | Bonne |
| Vidéo Wan 2.2 5B 832×480, 3 s | 6 à 15 min | Inférieure à Veo / Kling (résolution, durée, pas de son) |

Les moteurs payants (Claude, Nano Banana, Veo, Kling) restent disponibles en secours si vous ajoutez `EMERGENT_LLM_KEY` dans `backend\.env`.

## Installateur en un clic (recommandé)

Dans l'application : **Moteurs → Installateur Windows (.exe)**. Double-cliquez sur `Installer-LocalAiStudio.exe` : il télécharge et installe Python, Node.js, MongoDB, Ollama, ComfyUI Desktop et les modèles IA (barre de progression pour chaque fichier), installe les dépendances, puis crée le raccourci **LocalAiStudio** sur le Bureau. Les éléments déjà présents sont conservés. Windows SmartScreen peut afficher « Éditeur inconnu » : cliquez sur **Informations complémentaires → Exécuter quand même** (l'installateur n'est pas signé).

Pour recompiler l'installateur vous-même : `installer\build-installer.bat` (Inno Setup, gratuit) ou `makensis installer\LocalAiStudio.nsi` (NSIS).

## Diagnostic

**Moteurs → Diagnostic** vérifie MongoDB, l'espace disque, Node.js, Ollama et son modèle, ComfyUI, la carte graphique et les fichiers de modèles, puis indique quoi corriger (avec la commande à copier).

## 6. Utiliser votre PC depuis la preview en ligne (facultatif)

La preview en ligne ne peut pas joindre « localhost » chez vous : elle affiche donc « non connecté ». Pour l'utiliser quand même avec votre carte graphique :
1. Lancez Ollama et ComfyUI sur votre PC.
2. Double-cliquez sur `tunnel-preview.bat` : il installe cloudflared si besoin et ouvre deux tunnels gratuits.
3. Dans la preview, onglet **Moteurs** : collez l'adresse `https://….trycloudflare.com` du tunnel Ollama dans « Ollama · Configurer », et celle du tunnel ComfyUI dans « ComfyUI · Configurer ».
Les adresses changent à chaque lancement du tunnel. Fermez les fenêtres pour couper l'accès.

## 7. Moteur Premium (sites web)

Par défaut, les sites sont générés avec le **Moteur Premium** : l'IA locale choisit l'ambiance, l'ordre des sections et écrit tous les textes, puis une bibliothèque de sections animées (hero cinématique, typographie géante, récit épinglé au défilement, galerie horizontale, configurateur interactif, réseau 3D, compteurs, curseur et boutons magnétiques…) assure le rendu. Palette, polices, variantes et mises en page sont tirées au sort pour chaque projet : deux sites ne se ressemblent jamais. Un modèle 7B suffit (qwen2.5:7b), le 14B donne de meilleurs textes.

## Dépannage

- « Moteur local injoignable » : Ollama n'est pas lancé (`ollama serve`) ou le modèle manque (`ollama pull qwen2.5-coder:14b`).
- « ComfyUI injoignable » : ComfyUI n'est pas lancé, ou le port n'est pas le bon (8188 ou 8000).
- « ComfyUI a refusé le workflow » : un fichier de modèle est absent ou mal nommé. Utilisez le bouton **Tester** dans Moteurs.
- Manque de VRAM pour la vidéo : choisissez 3 s, le format 16:9, ou le préréglage LTX-Video (plus léger).
