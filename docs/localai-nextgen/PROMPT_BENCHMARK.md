# V2-B — Protocole de comparaison reproductible

Outil : `backend/lib/prompt_bench/` (corpus, approches A/B/C, contrôles, rendu optionnel).
Sorties : `backend/bench_runs/<horodatage>/` (manifest.json, index.html, renders/) — **git-ignorées, jamais poussées**.

## Approches comparées

| Id | Prompt envoyé | Rôle |
|---|---|---|
| A_legacy | Texte actuel de l'application (images : suffixe qualité ajouté ; vidéo : brut) | Référence |
| B_v2a_balanced | `prepare_prompt(mode=BALANCED, enabled=True)` ; sans LLM joignable : texte original | Candidat V2-A |
| C_constraint_first | Mêmes phrases que A, clauses contraintes (couleurs, positions, négations, caméra, texte) placées en tête | Hypothèse fenêtre CLIP |

Le moteur actif (`comfy.py`, `pipeline.py`) n'est pas modifié. Aucun workflow, checkpoint, sampler, CFG, steps ou résolution n'est changé.

## Commandes (Windows, depuis `backend/`)

```powershell
.venv\Scripts\python.exe -m lib.prompt_bench                                   # texte seul, sans GPU ni LLM
.venv\Scripts\python.exe -m lib.prompt_bench --llm-model qwen2.5-coder:14b     # LLM Ollama déjà installé
.venv\Scripts\python.exe -m lib.prompt_bench --llm-model qwen2.5-coder:14b --render-photo --seed 1234 --seed 5678   # ComfyUI lancé requis
.venv\Scripts\python.exe -m lib.prompt_bench --only photo_dense_long --render-photo --seed 1234                  # un seul cas
.venv\Scripts\python.exe -m lib.prompt_bench --render-video --only t2v_camera_fixed                             # T2V, coûteux
```

Le rendu photo utilise les builders `comfy._image_workflow` avec leurs paramètres par défaut, sans modification.
Les I2V sont ignorées tant qu'aucune image de référence n'est fournie (rien n'est inventé).
Mesures enregistrées : durée, pic VRAM (delta `nvidia-smi` au-dessus de la base), paramètres de sampler, prompt réellement envoyé, erreur explicite.

## Contrôles automatiques (proxies, pas une mesure visuelle)

- `must_missing` : exigence explicite absente du prompt préparé.
- `must_beyond_clip_window` : exigence située au-delà de ~75 tokens CLIP (estimation 1,3 token/mot ; **le tokenizer CLIP réel n'est pas utilisé**).
- `forbidden_added` : terme interdit ajouté par la préparation (ex. « rouge » pour une voiture noire).

## Jugement visuel (obligatoire, à faire à l'œil)

Ouvrir `index.html`, comparer A/B/C avec **la même seed**, noter : fidélité aux contraintes, réalisme, cohérence, détails, défauts anatomiques, éclairage, mouvement (vidéo), stabilité des sujets, artefacts.

## Limites connues

- Aucun test GPU n'a été exécuté dans cette session : ComfyUI est arrêté et aucun checkpoint image/vidéo n'est présent sur la machine de travail.
- A et B diffèrent sur deux points à la fois : le suffixe qualité (retiré par B) et le gabarit anglais ajouté par les adaptateurs. Un test contrôlé doit les séparer (variantes B sans gabarit, A sans suffixe).
- Le LLM ne modifie pas le fond du prompt : V2-A conserve le texte source et place l'analyse en diagnostic.
- La rétouche localisée est « unsupported » (aucun masque dans l'application) ; l'I2V est traitée comme référence fournie.

## V2-C — Lancer les premiers rendus sur votre PC (PowerShell)

Prérequis : ComfyUI lancé (Desktop, ou `python main.py --listen` dans son dossier) sur `http://127.0.0.1:8188`, et le checkpoint choisi présent dans son dossier `models\checkpoints`.

```powershell
cd C:\Users\desco\Documents\LocalAiVision\backend
# 1) Vérifier le checkpoint réellement installé (ne télécharge rien)
Invoke-RestMethod http://127.0.0.1:8188/object_info/CheckpointLoaderSimple | ConvertTo-Json -Depth 6 | Select-String "flux1|sdxl|sd_xl"
# 2) Photo produit, seed unique, 4 approches (A0 brut, A legacy, B V2-A, C ordre)
.venv\Scripts\python.exe -m lib.prompt_bench --only photo_product --render-photo --seed 1234 `
  --approach A0_raw --approach A_legacy --approach B_v2a_balanced --approach C_constraint_first `
  --llm-model qwen2.5-coder:14b --unload-ollama
# 3) Ouvrir la galerie
start .\bench_runs\(dossier le plus récent)\index.html
```

Modèle explicite : `--image-preset flux-dev|flux-schnell|sdxl` ou `--image-checkpoint NOM.safetensors`. Un checkpoint absent fait échouer le contrôle préalable ; aucun autre modèle n'est utilisé à la place.
`--unload-ollama` décharge uniquement `--llm-model` avant le rendu.
Les paramètres (résolution 1:1 = 1024², steps, sampler, CFG, négatif) restent ceux de `comfy.py`.
