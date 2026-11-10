# LocalAiStudio en local sur Windows : 100 % gratuit, sans API payante

Tout tourne sur votre PC : les sites (Ollama), les photos, les retouches et les pubs (ComfyUI + FLUX), et les vidéos (ComfyUI + Wan 2.2 / LTX-Video).
Configuration visée : Windows 10/11, NVIDIA RTX 3060 12 Go, 32 Go de RAM conseillés, environ 60 Go d'espace disque libre pour les modèles.

---

## 1. Installation isolée V2-F

Prérequis : Windows x64, Python 3.11 x64 avec le lanceur `py`, Node.js 20.19+ ou 22.12+ avec npm, et MongoDB accessible sur `127.0.0.1:27017`. Ollama et ComfyUI sont des services séparés. Une connexion est nécessaire pour les dépendances Python/npm ; **aucun modèle IA n'est téléchargé par cet installateur**.

1. Décompressez `LocalAiStudio-kit-windows.zip` dans un nouveau dossier.
2. Double-cliquez sur `install-v2f.bat`, ou lancez `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-parallel-edition.ps1`.
3. L'application est créée dans `%LOCALAPPDATA%\LocalAiStudio-Editions\NextGen-V2F` avec ses propres environnements Python et frontend. Une cible existante est refusée, jamais écrasée. Ports par défaut : 8012 et 3012.
4. Une **nouvelle base vide** reçoit un nom aléatoire ; au premier lancement, l'application refuse ce nom s'il existe déjà. Aucun projet ni média n'est migré. Pour récupérer une base existante, décidez d'abord d'une sauvegarde vérifiée et d'une procédure explicitement autorisée.

Le script utilise les versions et empreintes verrouillées pour Python 3.11 x64, Yarn 1.22.22 et `frontend/yarn.lock`. Il ne copie pas les environnements, les modèles ou les secrets d'une autre édition. Pour une cible ou des ports différents, passez `-Target`, `-BackendPort` et `-FrontendPort` au script PowerShell.

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

Dans le dossier de la nouvelle édition, double-cliquez sur **`start-localaistudio-v2f.bat`**. Il ouvre le backend sur `127.0.0.1:8012` et l'interface sur `127.0.0.1:3012`, après vérification de MongoDB. Lancez Ollama et ComfyUI séparément : le lanceur ne modifie pas leurs services ni leurs modèles. Si les ports sont occupés, il s'arrête sans lancer de seconde instance.

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

## Installateur Windows historique (.exe)

Les anciens scripts Inno Setup et NSIS restent des sources historiques : **ils n'ont pas été compilés ni validés pour V2-F** et peuvent proposer des téléchargements de modèles. Ne distribuez pas leur `.exe` comme une version V2-F. Utilisez l'installation isolée décrite en section 1 ; un `.exe` signé et testé sur Windows vierge reste à préparer.

## Diagnostic

**Moteurs → Diagnostic** vérifie MongoDB, l'espace disque, Node.js, Ollama et son modèle, ComfyUI, la carte graphique et les fichiers de modèles, puis indique quoi corriger (avec la commande à copier).

## 6. Accès distant (facultatif, non recommandé)

La preview en ligne ne peut pas joindre « localhost » chez vous : elle affiche donc « non connecté ».
Pour des raisons de sécurité, les tunnels publics non authentifiés ont été désactivés (V1-B) :
Ollama et ComfyUI n'ont pas d'authentification intégrée — les exposer sur Internet donnait un accès
complet à vos modèles IA, votre GPU et potentiellement vos fichiers.

Si vous avez **réellement** besoin d'un accès distant, utilisez un reverse proxy avec authentification
(Caddy, nginx) ou Cloudflare Access (Zero Trust) devant chaque moteur. Ne rouvrez jamais un tunnel
public sans cette couche de protection.

L'application reste concue pour un usage 100 % local. L'accès distant n'est ni testé ni supporté.

## 7. Moteur Premium (sites web)

Par défaut, les sites sont générés avec le **Moteur Premium** : l'IA locale choisit l'ambiance, l'ordre des sections et écrit tous les textes, puis une bibliothèque de sections animées (hero cinématique, typographie géante, récit épinglé au défilement, galerie horizontale, configurateur interactif, réseau 3D, compteurs, curseur et boutons magnétiques…) assure le rendu. Palette, polices, variantes et mises en page sont tirées au sort pour chaque projet : deux sites ne se ressemblent jamais. Un modèle 7B suffit (qwen2.5:7b), le 14B donne de meilleurs textes.

## Dépannage

- « Moteur local injoignable » : Ollama n'est pas lancé (`ollama serve`) ou le modèle manque (`ollama pull qwen2.5-coder:14b`).
- « ComfyUI injoignable » : ComfyUI n'est pas lancé, ou le port n'est pas le bon (8188 ou 8000).
- « ComfyUI a refusé le workflow » : un fichier de modèle est absent ou mal nommé. Utilisez le bouton **Tester** dans Moteurs.
- Manque de VRAM pour la vidéo : choisissez 3 s, le format 16:9, ou le préréglage LTX-Video (plus léger).
