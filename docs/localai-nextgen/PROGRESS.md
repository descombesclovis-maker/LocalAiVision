# Suivi de progression — LocalAiStudio NextGen

## État de la branche
- Branche : `nextgen/claude-code`, source canonique pour Manyfold.
- Code React/FastAPI initial **importé** depuis `nextgen/claude-original`, comparé aux empreintes d'un snapshot NextGen avant fusion.
- Quatre icônes binaires de `frontend/public/` manquent encore par rapport au ZIP de référence : consulter `PROVENANCE.md`. Les `__init__.py` Python vides manquants ont été restaurés.
- Aucun modèle IA ni donnée personnelle n'a été inclus dans GitHub.
- Aucun test GPU Windows exécuté durant ce transfert.
- Correctifs Claude Code 1.1-a / 1.2 / 1.3 : **non attestés** sur cette source.
- Audit Manyfold V0 fait sur l'ancienne branche `main` : **non applicable sans nouvelle vérification NextGen**.

## Prochaine action, sans nouvelles fonctionnalités
1. Manyfold vérifie `git branch --show-current`, `git status` et `backend/server.py`, `frontend/package.json`, `install.ps1`.
2. Inventorie les 4 icônes manquantes et les dépendances matérielles, sans inventer de remplacements.
3. Vérifie les mécanismes de nettoyage/téléchargement **dans cette version** ; ne pas recopier des conclusions de `main`.
4. Vérifie l'intégration exacte des protections de sécurité avant d'autoriser la génération hors `localhost`.
5. Met à jour la documentation de comparaison, puis arrête-toi **avant toute optimisation du moteur**.

## V1-A — Fiabilisation des modèles IA (réalisé)

Objectif : distinguer et fiabiliser la détection, le lancement et les erreurs des moteurs IA, **sans changer les
modèles par défaut, les paramètres (CFG, samplers, résolutions, étapes), les prompts, les LoRA ni les workflows**.

Constat vérifié dans le code NextGen (pas de recopie depuis `main`) :
- Aucune suppression automatique de fichier modèle n'existe (les `delete_one`/`delete_many` ne portent que sur les
  enregistrements DB : médias, marques, projets). Les modèles partagés ne sont donc jamais effacés sans action.
- Aucun téléchargement automatique de modèle n'existe côté backend ; `download-models.ps1` est manuel (interactif ou
  paramétré), reprend les téléchargements interrompus (`curl -C -`) et n'efface rien. Pydantic valide déjà les clés
  de modèles (`Literal[...]`), donc aucun HTTP 500 générique sur clé de modèle invalide.

Corrections fonctionnelles apportées :
- **Pré-vérification avant génération (ComfyUI)** : nouvelle fonction `comfy.verify_ready(s, video)` contrôle la
  joignabilité de ComfyUI **et** la présence des fichiers modèles requis par le preset actif, **avant** l'entrée
  dans la file GPU (`media.py`). Un modèle manquant échoue immédiatement avec une erreur claire au lieu d'attendre
  un slot GPU puis de produire une erreur générique. Réutilise les modèles déjà installés (n'échange aucun fichier).
- **Erreurs catégorisées (ComfyUI)** : hiérarchie `ComfyError` → `ComfyUnreachable`, `MissingModel`,
  `WorkflowError`, `GenerationError`. `comfy.run()` distingue désormais : serveur injoignable, modèle manquant,
  workflow incompatible, VRAM insuffisante (OOM/CUDA), délai dépassé, aucun fichier produit. Les `except comfy.ComfyError`
  existants (ex. `engines.put_comfy` → 422) continuent de fonctionner (sous-classes).
- **Erreurs catégorisées (Ollama / moteur local)** : `local_engine.LocalEngineError` → `EngineUnreachable`,
  `ModelMissing`. `complete_local` signale clairement « Ollama/LM Studio indisponible » vs « modèle de texte absent »
  (404 / « model not found ») avec la commande `ollama pull` appropriée.
- **Messages clairs côté UI** : `llm.friendly_error` restitue directement les messages actionnables des erreurs
  moteur ; le fallback « solde insuffisant » est conservé.

Fichiers modifiés : `backend/lib/comfy.py`, `backend/lib/local_engine.py`, `backend/lib/llm.py`,
`backend/routers/media.py`. Ajouté : `backend/tests/conftest.py`, `backend/tests/test_model_reliability.py`.

Tests : 22 tests ciblés passent (`pytest backend/tests/test_model_reliability.py`), sans GPU/ComfyUI/Ollama/MongoDB
(httpx mocké). Import-smoke des modules `lib.*` et `routers.media`/`routers.engines` OK.

Limitations restantes :
- Aucun test GPU/VRAM réel (RTX 3060 non présente dans l'environnement d'exécution) ; la détection OOM repose sur le
  message renvoyé par ComfyUI à l'exécution.
- La qualité des générations n'est pas modifiée ; les presets, CFG, samplers, résolutions, étapes et workflows sont
  intacts. La pré-vérification n'ajoute que des lectures locales (`system_stats` + `object_info`), n'envoie ni ne
  supprime de modèle.
- Les 4 icônes manquantes (cf. `PROVENANCE.md`) restent à compléter pour la distribution Windows.

## V1-B — Sécurisation des communications réseau (réalisé)

Objectif : sécuriser les accès réseau de LocalAiStudio NextGen **sans modifier la qualité ni le fonctionnement
des moteurs de génération**. Travaille exclusivement sur la sécurité des accès.

### 1. Protection des moteurs

**tunnel-preview.bat neutralisé** : l'ancien script ouvrait deux tunnels Cloudflare publics non authentifiés
exposant directement Ollama (`:11434`) et ComfyUI (`:8188`) à Internet. Le script a été réécrit : il
n'exécute plus `cloudflared tunnel --url`. Il affiche un avertissement de sécurité et rappelle que les
moteurs n'ont pas d'authentification intégrée. Les références dans `diagnostic.py`, `INSTALLATION.md`
et `SPEC.md` ont été mises à jour.

Les moteurs locaux utilisent les interfaces loopback par défaut (`http://127.0.0.1:11434`,
`http://127.0.0.1:8188`). `start-localaistudio.bat` démarre le backend sur `--host 127.0.0.1`.

### 2. Protection du backend

**Middleware d'authentification** (`backend/lib/auth.py`, nouveau) : un middleware ASGI pur (sans
`BaseHTTPMiddleware` — compatible avec `StreamingResponse`) protège toutes les routes `/api/*`.

- **Clé API** générée aléatoirement au premier démarrage, stockée dans `backend/.api_key` (gitignoré,
  exclu des téléchargements de kit via `SKIP_FILES`).
- **Authentification** par en-tête `X-API-Key` **ou** cookie httpOnly `las_session`.
- **Auto-bootstrap loopback** : la première requête depuis une connexion loopback vérifiée (TCP source
  `127.0.0.1`/`::1` **et** en-tête `Host` = `localhost`/`127.0.0.1`) reçoit un cookie httpOnly
  `SameSite=Strict; Path=/api`. Les requêtes suivantes sont authentifiées par ce cookie — aucune
  modification du frontend n'est nécessaire (le navigateur inclut le cookie automatiquement).
- **Rejet 401** pour toute requête non authentifiée provenant d'une source non-loopback. Une requête
  n'est **jamais** autorisée « parce qu'elle vient de localhost » : localhost est une condition
  d'émission du jeton, pas une autorisation.
- **Contournement de tunnel bloqué** : la vérification conjointe TCP + Host empêche un tunnel de
  contourner l'authentification (le Host serait l'URL du tunnel, pas `localhost`).
- **Chemins exemptés** (sans auth) : `/api/preview/*` (aperçus de sites générés), `/api/media/*/file`
  (servitude des fichiers média pour les aperçus), `/api/` (health check), `OPTIONS` (CORS preflight).

**CORS restrictif** (`backend/server.py`) : les origines par défaut sont limitées à loopback
(`localhost:3000`, `127.0.0.1:3000`, `localhost:5173`, `127.0.0.1:5173`, `localhost:8001`,
`127.0.0.1:8001`). Le wildcard `*` est systématiquement filtré (incompatible avec
`allow_credentials=True`). L'opérateur peut définir `CORS_ORIGINS` dans `.env` ; `*` est ignoré.
Les méthodes et en-têtes sont restreints (`GET, POST, PUT, PATCH, DELETE, OPTIONS` ;
`Content-Type, X-API-Key`). L'exemple `.env` dans `engines.py` utilise des origines loopback.

**Protection des clés API externes** : `EMERGENT_LLM_KEY` reste dans `.env` (gitignoré, exclu des kits).
`backend/.api_key` est ajouté à `SKIP_FILES` et `.gitignore`.

**Protection des opérations** : `DELETE /api/projects/{pid}`, `DELETE /api/media/{mid}`,
`DELETE /api/brands/{bid}`, `PUT /api/settings/comfyui`, `PUT /api/settings/local-engine`,
`POST /api/media/images`, `POST /api/media/videos`, `POST /api/projects` et toutes les routes
sensibles requièrent désormais un jeton valide. Le listing (`GET /api/media`) et les actions de file
(`POST /api/queue/*/cancel`) sont également protégés.

### 3. Protection des générations

**CSP sur les aperçus** (`backend/routers/projects.py`) : l'endpoint `/api/preview/{pid}/{path}`
retourne désormais l'en-tête `Content-Security-Policy: connect-src 'none'`. Le JS d'un site généré
ne peut pas appeler les API privilégiées de LocalAiStudio via `fetch`/`XMLHttpRequest`. Les balises
`<img>`/`<video>` (gouvernées par `img-src`/`media-src`, non par `connect-src`) continuent de charger
les médias depuis `/api/media/{id}/file` — les aperçus affichent correctement les images et vidéos.

Aucun mécanisme dangereux des anciennes versions n'a été réintroduit. Les fonctions `session.ts`
du frontend (`beginSession`/`endSession`) existaient déjà dans le code importé mais n'étaient pas
branchées ; elles ne le sont toujours pas (l'auth est gérée côté backend par cookie automatique).

### 4. Vérification de V1-A — risques confirmés et documentés

**Risque 1 — Faux diagnostic de modèle manquant** (confirmé) :
`comfy._choices()` attrape toutes les exceptions et retourne `[]`. Si l'endpoint `object_info` de
ComfyUI échoue (nœud absent, erreur réseau, format inattendu), la liste est vide. `_missing_files()`
signale alors le fichier du preset comme manquant — un faux positif. Le modèle peut être installé ;
c'est la liste qui est indisponible.

*Correctif recommandé (distinct, hors mission sécurité)* : `_choices` devrait retourner `None` en
cas d'erreur (liste indisponible) plutôt que `[]` (liste vide = aucun modèle). `_missing_files`
sauterait la vérification quand la liste est `None` au lieu de signaler le fichier comme manquant.

**Risque 2 — Double vérification** (confirmé) :
`verify_ready()` est appelée deux fois par génération ComfyUI : une fois dans `media.py`
(`_comfy_image`/`_run_comfy_video`, avant le slot GPU) et une fois dans `comfy.py`
(`generate_image`/`generate_video`, après `get_settings`). Chaque appel effectue 5 requêtes HTTP
localhost (`system_stats` + 4 × `object_info`). Le surcoût est négligeable (~0,1 s) mais le double
appel est confirmé.

*Correctif recommandé (distinct, hors mission sécurité)* : retirer l'appel `verify_ready` de
`generate_image`/`generate_video` dans `comfy.py` puisque tous les appelants passent déjà par
`media.py` qui pré-vérifie. Alternative : ajouter un paramètre `skip_verify=True`.

### 5. Préservation

Aucun changement : modèles IA, workflows, paramètres CFG, samplers, étapes d'inférence, résolutions,
prompts, LoRA, paramètres de qualité, interface graphique. Aucun modèle téléchargé. Aucun fichier
utilisateur supprimé. Le frontend n'a pas été modifié (l'auth par cookie httpOnly est transparente).

### 6. Tests

**45 tests de sécurité** (`backend/tests/test_security.py`) couvrent :
- Refus des accès non authentifiés (401 sans jeton, mauvais jeton, mauvais cookie)
- Fonctionnement des sessions autorisées (en-tête `X-API-Key` et cookie `las_session`)
- Absence d'exposition publique (tunnel neutralisé, CORS restrictif, filtrage `*`)
- Protection des moteurs locaux (loopback par défaut, Host header vérifié)
- Maintien du fonctionnement normal (chemins exemptés : preview, media file, health check, OPTIONS)
- Compatibilité des routes de génération (routes sensibles protégées, exemptes préservées)
- CSP `connect-src 'none'` sur les aperçus
- Vérification V1-A (faux modèle manquant + double `verify_ready`)
- Protection de la clé API (gitignoré, exclu des kits, exemple `.env` loopback)

**22 tests V1-A** (`backend/tests/test_model_reliability.py`) : toujours passants, non affectés.

Total : **67 tests passent** (`pytest tests/`), sans GPU/ComfyUI/Ollama/MongoDB (httpx mocké, TestClient
in-process). Aucun test GPU réel n'est présenté comme test de génération.

### Fichiers modifiés

- `backend/lib/auth.py` (nouveau) — middleware d'authentification ASGI, gestion de clé API
- `backend/server.py` — CORS restrictif + ajout du middleware d'auth
- `backend/routers/projects.py` — en-tête CSP `connect-src 'none'` sur les aperçus
- `backend/routers/engines.py` — `.api_key` dans `SKIP_FILES`, `ENV_EXAMPLE` loopback
- `backend/lib/diagnostic.py` — référence tunnel-preview.bat retirée
- `tunnel-preview.bat` — neutralisé (avertissement de sécurité, aucun tunnel public)
- `INSTALLATION.md` — section 6 réécrite (accès distant sécurisé)
- `SPEC.md` — référence tunnel mise à jour
- `.gitignore` — `.api_key` ajouté
- `backend/tests/conftest.py` — `CORS_ORIGINS` loopback
- `backend/tests/test_security.py` (nouveau) — 45 tests de sécurité

### Limitations restantes

- Le cookie de session utilise `secure=False` (HTTP sur localhost, pas de TLS). En production avec
  HTTPS, passer `secure=True`.
- L'auto-bootstrap émet un cookie à la première requête loopback. Si un tunnel est configuré
  manuellement (hors script), le Host header serait l'URL du tunnel et le bootstrap serait refusé —
  mais l'opérateur reste responsable de la sécurité des tunnels qu'il crée.
- Les 4 icônes manquantes (cf. `PROVENANCE.md`) restent à compléter.
- Les deux risques V1-A (faux modèle manquant, double vérification) sont documentés mais non corrigés
  — un correctif ciblé distinct est recommandé.

## V1-B.2 — Authentification sécurisée et isolation des aperçus (réalisé)

Commit : `3c5177a` sur `nextgen/claude-code`.

### Objectif

Corriger deux failles identifiées après V1-B :
1. **Auto-bootstrap localhost supprimé** : aucune requête sensible n'est autorisée uniquement parce
   qu'elle provient de loopback.
2. **Isolation sandbox des aperçus** : les scripts des sites générés ne peuvent plus accéder aux
   cookies, au stockage local ni appeler les API protégées.

### A. Authentification — jeton d'initialisation à usage unique

**Problème corrigé** : V1-B autorisait les requêtes loopback sans jeton via un mécanisme
d'auto-bootstrap (la première requête localhost recevait un cookie). Un processus local malveillant
pouvait ainsi accéder à l'API sans authentification.

**Correction** :
- `_is_localhost()` et l'auto-bootstrap supprimés de `lib/auth.py`.
- Nouvelle classe `_BootToken` : jeton aléatoire unique généré par le lanceur Windows
  (`start-localaistudio.bat`, via PowerShell `NewGuid()`), passé via la variable d'environnement
  `LAS_BOOT_TOKEN` aux deux processus (backend + proxy Vite).
- Nouvel endpoint `POST /api/auth/init` (dans `server.py`) : valide le jeton `X-Boot-Token`,
  émet un cookie httpOnly `SameSite=Strict`, invalide le jeton (usage unique).
- Le proxy Vite (`vite.config.ts`) injecte `X-Boot-Token` uniquement sur `/api/auth/init` —
  le secret n'est jamais dans le bundle frontend.
- `frontend/src/main.tsx` appelle `/api/auth/init` au démarrage avant de monter React.
- `.boot_token` gitignorer et exclu des kits (`SKIP_FILES`).

### B. Isolation des aperçus (iframe sandbox)

**Problème corrigé** : l'iframe de prévisualisation dans `Editor.tsx` accédait à `contentDocument`
sans sandbox — les scripts du site généré partageaient l'origine du backend et pouvaient appeler
les API protégées ou lire les cookies.

**Correction** :
- Attribut `sandbox="allow-scripts allow-forms"` ajouté à l'iframe (sans `allow-same-origin`).
  Les scripts générés ne peuvent plus accéder aux cookies, au `localStorage` ni à l'API backend.
- Pont `postMessage` injecté dans le HTML des aperçus (`_SELECT_BRIDGE` dans `routers/projects.py`) :
  - Parent → iframe : `"las-select-start"` / `"las-select-stop"`.
  - Iframe → parent : `{type:"las-select", selector, html}` sur clic d'élément.
  - Iframe → parent : `{type:"las-navigate", path}` au chargement.
- `Editor.tsx` remplace l'accès direct à `contentDocument` par `window.addEventListener("message")`.
- CSP améliorée : `connect-src 'none'; form-action 'none'` (bloque fetch/XHR ET soumissions de formulaires).

### Tests

59 tests dans `test_security.py` couvrant :
- Bootstrap token : usage unique, rejeu refusé, token vide rejeté.
- `POST /api/auth/init` : token valide → cookie émis, token invalide → 401, usage unique.
- Absence d'auto-bootstrap loopback (aucun `_is_localhost` exporté).
- Attribut `sandbox` de l'iframe sans `allow-same-origin`.
- Pont postMessage présent dans le code de prévisualisation.
- CSP `form-action 'none'` ajoutée.
- `.boot_token` gitignorée et exclue des kits.
- Lanceur génère `LAS_BOOT_TOKEN`.

### Fichiers modifiés

- `backend/lib/auth.py` — `_is_localhost` et auto-bootstrap supprimés, `_BootToken` ajouté.
- `backend/server.py` — endpoint `POST /api/auth/init`.
- `backend/routers/projects.py` — `_SELECT_BRIDGE` postMessage, CSP `form-action 'none'`.
- `backend/routers/engines.py` — `.boot_token` dans `SKIP_FILES`.
- `frontend/src/main.tsx` — appel bootstrap au démarrage.
- `frontend/src/pages/Editor.tsx` — iframe sandbox + postMessage.
- `frontend/vite.config.ts` — proxy injecte `X-Boot-Token`.
- `start-localaistudio.bat` — génère `LAS_BOOT_TOKEN`.
- `.gitignore` — `.boot_token` ajouté.
- `backend/tests/conftest.py` — `LAS_BOOT_TOKEN=test-boot-token`.
- `backend/tests/test_security.py` — réécriture complète (59 tests).

---

## V1-C — Fiabilisation des générations ComfyUI (réalisé)

Commit : `4124cef` sur `nextgen/claude-code`.

### Objectif

Corriger les deux problèmes de fiabilité identifiés pendant V1-A et V1-B :
1. **Faux modèles manquants** : `_choices()` retournait `[]` sur erreur réseau, causant de faux
   diagnostics « modèle absent ».
2. **Double vérification** : `verify_ready()` était appelé deux fois par génération (media.py +
   comfy.py), ajoutant 5 requêtes HTTP inutiles.

### A. Correction `_choices()` — None vs []

**Problème** : `_choices()` attrapait toutes les exceptions et retournait `[]`. `_missing_files()`
interprétait `[]` comme « ComfyUI ne connaît aucun modèle » et signalait le modèle présent comme
absent — faux positif.

**Correction** :
- `_choices()` retourne maintenant `None` en cas d'erreur (liste indisponible) vs `[]`
  (liste disponible mais vide).
- `_missing_files()` ignore les listes `None` — ne peut pas confirmer l'absence sans liste valide.
- Nouveau type d'erreur `ModelListUnavailable(ComfyError)` : distinct de `MissingModel`.
- `verify_ready()` lève `ModelListUnavailable` quand une liste est `None`, avec un message clair
  identifiant l'endpoint `object_info` défaillant.
- `test()` gère aussi les listes `None` avec un message informatif.
- Diagnostics complets : `ComfyUnreachable` / `ModelListUnavailable` / `MissingModel` /
  `WorkflowError` / `GenerationError` (OOM, timeout, aucun fichier).

### B. Suppression de la double vérification

**Problème** : `generate_image()` et `generate_video()` appelaient `verify_ready()` après que
`media.py` l'avait déjà fait — 5 requêtes HTTP redondantes par génération.

**Correction** :
- `verify_ready()` supprimé de `generate_image()` et `generate_video()` dans `comfy.py`.
- `media.py` conserve l'appel unique dans `_comfy_image()` et `_run_comfy_video()` (avant le slot GPU).
- Diagnostics améliorés dans `media.py` : `ComfyUnreachable` / `ModelListUnavailable` /
  `MissingModel` distingués avec des `progress_label` spécifiques.

### C. Préservation des moteurs

Aucune modification des workflows, modèles, presets, CFG, samplers, résolutions, seeds, prompts,
LoRA ou paramètres de qualité. `DEFAULTS`, `IMAGE_PRESETS`, `VIDEO_PRESETS`, `IMAGE_SIZES`,
`VIDEO_SIZES`, `VIDEO_LENGTHS` et `NEGATIVE` sont intacts.

### Tests

**108 tests nouveaux** dans `test_comfy_reliability.py` couvrant :
- `_choices()` retourne `None` sur erreur réseau.
- `_choices()` retourne `[]` quand ComfyUI a 0 modèles.
- `_missing_files()` ignore les listes `None`.
- `verify_ready()` lève `ModelListUnavailable` (pas `MissingModel`) pour les listes `None`.
- `verify_ready()` lève `MissingModel` uniquement quand la liste est disponible et le modèle absent.
- `generate_image()` et `generate_video()` n'appellent PAS `verify_ready()`.
- `media.py` appelle `verify_ready()` exactement 2 fois (1 par type de génération).
- Paramètres de génération préservés (CFG, steps, sampler, résolutions).
- Workflow personnalisé respecté.
- Simulations T2I, T2V, I2V (mocked, pas de GPU réel).
- Absence de suppression de modèles, absence de téléchargement automatique.

**Total : 130 tests passent** (`pytest tests/`).

### Fichiers modifiés

- `backend/lib/comfy.py` — `_choices()` None, `ModelListUnavailable`, `_missing_files()` None-safe,
  `verify_ready()` distingué, `generate_image()`/`generate_video()` sans double-vérification.
- `backend/routers/media.py` — diagnostics détaillés, `verify_ready()` appel unique.
- `backend/tests/test_comfy_reliability.py` (nouveau) — 108 tests V1-C.
- `backend/tests/test_model_reliability.py` — mis à jour pour `ModelListUnavailable` et None.
- `backend/tests/test_security.py` — mis à jour (V1-C fixes reflétés).
- `backend/tests/conftest.py` — event loop précrée pour éviter conflit motor/xdist.

### Limitations

- Aucun test GPU réel (RTX 3060 non présente dans l'environnement d'exécution). Tous les tests de
  génération sont des simulations (httpx mocké). Cela est clairement indiqué dans les docstrings.
- `ModelListUnavailable` est catchable comme `ComfyError` — compatibilité ascendante garantie.
- Si `object_info` devient indisponible en cours de génération après `verify_ready()`, l'erreur se
  produira dans `run()` (via `WorkflowError`) et non via `ModelListUnavailable`.

---

## V1-D — Dernières corrections de fiabilité ComfyUI (réalisé)

Base : `4124cef` (V1-C). Commit V1-D : `294002d`, poussé et confirmé sur `nextgen/claude-code`.

### Corrections

- Les pré-vérifications sont limitées aux listes effectivement utilisées : checkpoint photo pour
  SDXL/FLUX, diffusion + encodeur + VAE pour Wan, checkpoint vidéo + encodeur pour LTX.
  Un ancien réglage VAE externe ne bloque plus LTX (VAE fourni par son checkpoint).
- Les workflows API personnalisés remplacent les exigences des presets : leurs fichiers littéraux
  sont vérifiés avec le schéma de leur propre loader, y compris multi-CLIP et LoRA.
  Les entrées liées/dynamiques/opaques restent à valider par ComfyUI, sans faux diagnostic d'absence.
- `None` / schéma non énumérable reste « présence invérifiable » ; `[]` reste une liste valide vide.
  Une absence confirmée garde son erreur explicite même si une autre liste est indisponible.
- Seulement 2 requêtes pour une photo, 4 pour Wan, 3 pour LTX (`system_stats` inclus).
  Chaque type de loader personnalisé est interrogé une seule fois par vérification, même sur erreur.
- `_hero_video()` réalise sa propre vérification unique (appel direct hors `media.py`), sans ajouter
  de contrôle dans `generate_video()` ni de slot GPU imbriqué. Une découverte indisponible produit
  un avertissement et autorise la tentative existante ; un modèle confirmé absent est diagnostiqué.
  Les erreurs serveur/workflow/rendu sont visibles dans le média et l'étape du projet, sans arrêter le site.

### Périmètre préservé

Aucun changement des checkpoints configurés, workflows de génération, prompts existants, modèles,
CFG, samplers, steps, résolutions ou durées. Aucun téléchargement, aucune suppression de création.
LocalAiWeb n'est modifié que dans le correctif vidéo d'en-tête demandé.

### Validation

- Référence avant correction : **71 tests** ComfyUI/modèles réussis.
- **29 nouveaux tests V1-D** : modèles actifs/inactifs, Wan/LTX, workflows personnalisés,
  schémas non vérifiables, déduplication des requêtes, erreurs et vidéo d'en-tête.
- Commande ciblée : `.venv/Scripts/python.exe -m pytest tests/test_comfy_v1d.py tests/test_comfy_reliability.py tests/test_model_reliability.py -q`
  depuis `backend` : **100 réussis, 0 échec**.
- Non-régression : `.venv/Scripts/python.exe -m pytest tests/ -q` : **159 réussis, 0 échec**.
- Premier passage : 6 erreurs de fixture (import Motor sans boucle asyncio) corrigées en exécutant
  la fixture vidéo dans sa boucle asynchrone ; aucun contournement dans le code applicatif.
- Avertissements préexistants pytest-asyncio/Starlette ; configuration pytest inchangée.
- Tests HTTP/DB/rendus simulés, pas de test GPU ni d'affirmation de qualité visuelle.

Fichiers : `backend/lib/comfy.py`, `backend/lib/pipeline.py`,
`backend/tests/test_comfy_v1d.py`, adaptations de signatures des mocks dans
`test_comfy_reliability.py` / `test_model_reliability.py`, ce journal.

## V2-A — Compréhension et préparation indépendante des prompts (réalisé)

Démarré **après validation et push de V1-D `294002d`**, confirmé sur GitHub.
Commit dédié V2-A sur `nextgen/claude-code`. Documentation : [PROMPT_PREPARATION.md](PROMPT_PREPARATION.md).

### Module et garanties

- Package central `backend/lib/prompt_preparation/`, indépendant des générateurs et sans I/O
  à l'import. Aucune intégration active dans les routes existantes ; `enabled=False` par défaut.
- Analyse JSON par le LLM **entièrement local déjà configuré** (Ollama / OpenAI-compatible local),
  une requête au maximum, pas de listage préalable/retry/téléchargement/fallback payant.
  Endpoints loopback seulement, proxies et redirections désactivés, validation des URLs/ports.
- Sujet, attributs, environnement, actions, cadrage, lumière, obligations, interdictions, détails
  à conserver et style ; également relations spatiales, mouvements et identité.
  Chaque élément cite le texte exact, sa phrase source et ses offsets Unicode.
- Original intégral conservé. Analyse inventée/non conforme, LLM absent ou timeout : repli sur
  l'original exact, sans troncature. Annulation de l'appelant propagée.
- Trois modes STRICT/ÉQUILIBRÉ/CRÉATIF. ÉQUILIBRÉ recommandé mais **pas activé automatiquement**.
  Les politiques n'autorisent jamais de remplacer une exigence explicite.
- Adaptateurs photo, T2V, I2V, retouche et publicité : priorités d'analyse et instructions fixes
  adaptées à la tâche. Aucune réécriture visuelle libre du LLM n'entre dans le candidat.
- Les citations restent dans les diagnostics et ne sont **pas réinjectées comme consignes positives** :
  même un extrait exact peut perdre la portée d'une négation/titre de liste/exception distant.
  Le texte préparé garde tout l'original une seule fois, puis des politiques d'exécution non visuelles.
- Contradictions sourcées : `needs_clarification`, candidat original, aucune résolution automatique.
  Retouche sans masque, identité, positions/mouvements non contrôlés : avertissements honnêtes.
  Tâche ou masque non pris en charge : `unsupported`, sans tentative d'inventer un workflow.
- `compare_preparations()` conserve toujours l'ancien prompt sélectionné ; API/CLI JSON pour
  afficher original/candidat/analyse/diagnostics. Aucun rendu déclenché, aucune création modifiée.

### Tests

Depuis `backend` (configuration pytest/xdist inchangée) :

- `.venv/Scripts/python.exe -m pytest tests/test_prompt_preparation.py tests/test_prompt_local_provider.py -q`
  : **175 réussis, 0 échec** (72 moteur/corpus/non-régression, 103 fournisseur local).
- `.venv/Scripts/python.exe -m pytest tests/ -q` : **334 réussis, 0 échec**.
- Corpus de 9 demandes, chacune dans les 3 modes : photo détaillée, couleurs multi-objets,
  positions, caméra fixe/mouvements complexes, chorégraphie caméra demandée, identité I2V,
  retouche localisée, publicité/texte exact, contradictions. Cas adversariaux de négation,
  citations inventées, paramètres non autorisés, URL distante, erreurs réseau et désactivation.
- Non-régression du vrai constructeur de prompt photo existant et comparaison conservant l'ancien
  choix ; CLI UTF-8/CRLF sans DB ; compilation Python réussie.
- Erreurs intermédiaires de collecte/syntaxe pendant les éditions corrigées ; aucun échec final.
  Avertissements préexistants pytest-asyncio/Starlette. Black non installé dans le venv : pas
  d'installation ajoutée ; cette disponibilité n'affecte pas les tests applicatifs.

### Fichiers

- `backend/lib/prompt_preparation/{__init__,__main__,types,engine,adapters,local_llm}.py`.
- `backend/tests/test_prompt_preparation.py`, `backend/tests/test_prompt_local_provider.py`.
- `backend/tests/fixtures/prompts_v2a.json`.
- `docs/localai-nextgen/PROMPT_PREPARATION.md` et ce journal.

### Limites et périmètre

Aucun modèle téléchargé, aucune création supprimée, aucun checkpoint/workflow/sampler/résolution/
CFG/step de génération modifié. LocalAiWeb n'a aucune modification V2-A.
Le préparateur est conservateur : compréhension structurée + garde-fous + politiques par tâche,
pas de traduction ni de réécriture créative libre. La qualité d'extraction d'un vrai LLM et sa
capacité à détecter toutes les contradictions restent à évaluer ; les tests utilisent des
annotations/HTTP simulés. Ils **ne prouvent pas une meilleure fidélité visuelle**.
Les capacités manquantes (masques, identité verrouillée, spatial/caméra dédiés) ne sont pas ajoutées.
Les négatifs fixes existants, dont les conflits éventuels avec la demande, restent inchangés.
Aucun test GPU ou qualité visuelle effectué pendant cette mission.

## Prochaine étape recommandée — V2-B (non commencée)

Validation comparative locale de l'analyse réelle, puis original/ancien/candidats sur la
**RTX 3060 12 Go** : respect des obligations, couleurs/positions, mouvements, identité,
conservation hors retouche, latence et VRAM. Garder les paramètres de génération contrôlés ;
ne pas activer automatiquement le moteur avant cette validation et une décision utilisateur.

**Arrêt après V2-A.** Pas de nouvelle fonctionnalité secondaire ni de modification des moteurs.

## V2-B — Évaluation reproductible (terminée côté outil ; GPU non exécuté)

- Outil : `backend/lib/prompt_bench/` (corpus de 11 cas, approches A legacy / B V2-A équilibré / C ordre contraintes d'abord, contrôles textuels, manifest JSON, galerie HTML, rendu ComfyUI optionnel avec durée et pic VRAM). Protocole : `docs/localai-nextgen/PROMPT_BENCHMARK.md`.
- Moteur actif, workflows, paramètres de génération et LocalAiWeb : **inchangés**. Sorties `backend/bench_runs/` git-ignorées.
- Environnement constaté : RTX 3060 12 Go libre, Ollama actif (qwen2.5-coder:14b utilisé), ComfyUI **arrêté**, aucun checkpoint image/vidéo trouvé sur la machine. Rendus visuels **non réalisés**.
- Résultats texte (`--llm-model qwen2.5-coder:14b`) : A 10/11, B 10/11, C 10/11. Le cas dense (≈140 tokens approx.) dépasse la fenêtre CLIP pour A, B et C (4/4/3 exigences tardives).
- LLM réel : 7 prompts « prepared », 3 replis sur l'original, 1 « unsupported » (rétouche sans masque). Constat : B ajoute un gabarit anglais générique et retire le suffixe qualité du photo ; le fond du prompt n'est pas réécrit.
- Tests : `tests/test_prompt_bench.py` ; 195 réussis (benchmark + préparation + fournisseur LLM).
- Prochaine étape : rendus photo A/B/C sur la RTX 3060 avec ComfyUI lancé, en séparant suffixe et gabarit (variantes contrôlées), avant toute décision sur le moteur par défaut.

## V2-C — Premières générations réelles (bloquées : ComfyUI non joignable)

- Inventaire : ComfyUI absent (`127.0.0.1:8188` fermé, aucune installation trouvée sur C:, D:, E:). Aucun checkpoint FLUX, SDXL, Wan ou LTX et aucun encodeur T5/UMT5 sur les disques. Ollama 0.40.15 actif avec 8 modèles texte/vision uniquement.
- Benchmark : sélection explicite du modèle (`--image-preset` / `--image-checkpoint`), contrôle préalable ComfyUI (refus sans repli silencieux), approches `A0_raw` (sans suffixe) pour isoler le suffixe, `--unload-ollama` ciblé, compteur d'images et d'échecs dans le manifeste. Défauts de génération inchangés.
- Tests : `tests/test_prompt_bench.py`, 27 réussis, 0 échec.
- Essai réel : photo produit, approches A0/A/B/C, seed 1234 → contrôle ComfyUI en échec (`ComfyUnreachable`), 0 image, aucune comparaison visuelle. Ollama déchargé (qwen2.5-coder:14b).
- Action requise : lancer ComfyUI et exécuter les commandes de `docs/localai-nextgen/PROMPT_BENCHMARK.md` (section V2-C).

## V2-C.1 — Première génération photographique réelle (SDXL, photo produit)

- **Correction** : le constat V2-C « ComfyUI absent » était faux. ComfyUI Desktop est installé (`AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI`, venv PyTorch 2.12.1+cu130 avec CUDA, RTX 3060 détectée). Ses modèles partagés sont dans `AppData\Local\Comfy-Desktop\ComfyUI-Shared\models`, chargés par `extra_model_paths` de l'instance Desktop.
- Modèles constatés : `checkpoints\sd_xl_base_1.0.safetensors` (6 938 078 334 o, taille officielle : aucune téléchargement nécessaire), `flux1-schnell-fp8`, LTX présents ; `flux1-dev-fp8` **absent** (preset par défaut de l'application).
- ComfyUI lancé sur `127.0.0.1:8188` depuis le venv Desktop (version 0.37.2), sans téléchargement ni modification des modèles. Contrôle préalable du checkpoint SDXL : OK.
- Rendu : photo produit, seed 1234, SDXL (1024², 30 steps, CFG 6,5, dpmpp_2m karras, paramètres de `comfy.py` inchangés), approches A0/A/B/C. Ollama déchargé (qwen2.5-coder:14b) avant le rendu.
- Résultats : 4 images produites, 0 erreur. Durées : A0 26,6 s (inclut le chargement du checkpoint), A 22,4 s, B 22,5 s, C 22,4 s. Pic VRAM au-dessus de la base : A0 +7 828 MiB (chargement), A/B/C ≈ +2 750 MiB. VRAM totale après rendu : 7 813 / 12 288 MiB.
- Observations visuelles (3 images distinctes examinées) : verre bleu cobalt, collerette dorée et marbre respectés ; aucune étiquette visible ; **« bouchon doré posé à droite » non respecté** (flacon centré) ; rendu propre mais léger aspect de synthèse sur le cristal. Un même seed produit des compositions différentes selon le texte : une comparaison à seed unique est donc bruitée.
- **C = A** (empreintes identiques) : le prompt tient en une phrase, le réordonnancement ne change rien. Le suffixe qualité se colle après un point (« visible., highly detailed ») : défaut mineur du chemin legacy, non corrigé (changerait le moteur actif).
- Correction de code : le manifeste marque `may_include_model_load` sur le premier rendu, pour ne pas comparer ses durées. Test de rendu avec faux ComfyUI ajouté.
- Galerie : `backend\bench_runs\20261109-200129\index.html` (4 approches, prompts, statuts). Vérifiée dans le navigateur ; les « PASS » ne sont que des contrôles textuels.
- Application : aucune configuration `comfyui` enregistrée en base ; valeurs par défaut utilisées (URL 8188 correcte, preset `flux-dev` non installé). Pour générer dans LocalAiStudio, choisir le preset **SDXL** dans les réglages. Aucune écriture en base.
- Tests : `tests/test_prompt_bench.py` + préparation + fournisseur LLM : 203 réussis, 0 échec.
- Limites : une seule seed, une seule image par approche ; aucune vidéo ; aucune mesure de qualité objective ; pas de test via l'API authentifiée de l'application.


## V2-D — Étape A : sécurité (objectif 10/10)

Constats vérifiés dans le dépôt puis corrigés :

- **Tunnels publics proposés dans l'interface** : `frontend/src/pages/Engines.tsx` affichait encore `cloudflared tunnel --url` pour Ollama (11434) et ComfyUI (8188), avec bouton de copie. Commandes et boutons retirés ; remplacés par un avertissement sans commande. `tunnel-preview.bat` était déjà neutralisé (V1-B), inchangé.
- **Secrets dans l'installeur** : Inno Setup (`installer/LocalAiStudio.iss`) et NSIS (`installer/LocalAiStudio.nsi`) incluaient tout `backend/`. Sur ce poste, `backend/.api_key` existe et `backend/bench_runs/` contient les rendus de benchmark : ils auraient été embarqués. Exclusions ajoutées : `.api_key`, `.boot_token`, `bench_runs`, `*.key`, `*.pem`, `.env.*` (backend) et `.env.*` (frontend).
- **Exposition du serveur Vite** : `frontend/vite.config.ts` utilisait `host: true` et `allowedHosts: true`, donc un `yarn dev` seul écoutait sur toutes les interfaces et acceptait tout nom d'hôte. Désormais loopback par défaut (`127.0.0.1`, hôtes `localhost`/`127.0.0.1`). L'exposition exige `LAS_VITE_EXPOSE=1` explicitement. Le lanceur `start-localaistudio.bat` (déjà `--host 127.0.0.1`) est inchangé. La prévisualisation hébergée doit définir `LAS_VITE_EXPOSE=1` ; ce cas n'a pas été testé.
- **Jeton d'amorçage périmé** : Vite lisait `backend/.boot_token` une seule fois au démarrage. Après un redémarrage du backend, le proxy envoyait l'ancien jeton. Lecture désormais à chaque requête (`readBootToken()`).
- **401 à chaque rafraîchissement** : `/api/auth/init` renvoyait 401 au second chargement (jeton déjà consommé) alors que le cookie de session était valide, ce qui journalisait une erreur dans le navigateur. Désormais 200 si le cookie `las_session` correspond à la clé persistante. Sans cookie, le jeton reste à usage unique.

Tests : `backend/tests/test_security_v2d.py` (nouveau) couvre la page Engines, les exclusions Inno et NSIS, la configuration Vite, et le cycle de session sur la vraie route `/api/auth/init` (premier démarrage, mauvais jeton, rafraîchissement avec et sans cookie, redémarrage avec clé persistante, régénération du jeton). Suite backend complète : **392 réussis, 0 échec**.

Non vérifié, à faire : compilation Inno Setup et NSIS (aucun compilateur installé sur ce poste) ; compilation TypeScript et interface navigateur (`frontend/node_modules` absent, donc Vite n'a pas été lancé) ; authentification dans un navigateur réel.


## V2-D — Étapes B et C : génération photo depuis l'application, comparaison contrôlée

### Corrections techniques (commits poussés)

- `d005a34` — **Erreurs 500 sur réglages, médias, projets** : le client Motor était créé à l'import, donc lié à une autre boucle asyncio qu'uvicorn. `lib/db.py` crée désormais un client par boucle (proxys paresseux, `db.motor()`) ; `lib/store.py` idem pour GridFS. Test : `tests/test_db_loop.py`. Vérifié : routes 200 sur uvicorn.
- `44471b8` — **Editor.tsx restauré** : le commit V1-B.2 (`3c5177a`) avait écrasé les retours à la ligne ; les `//` avalaient le code et le frontend ne compilait plus. Restauration depuis `3170eb8`, puis réapplication des seuls changements de sécurité : iframe `sandbox="allow-scripts allow-forms"` (sans `allow-same-origin`), sélection et navigation par `postMessage`. `tsc --noEmit` passe. `vite.config.ts` : cible du proxy configurable via `LAS_API_TARGET` (défaut inchangé).
- `3497980` — **Suffixe photo** : l'application produisait « … marbre blanc., highly detailed ». Helper partagé `lib/photo_prompt.py` (application et benchmark). Cas benchmark `photo_spatial_product` ajouté (phrase de contrôle spatial).
- Suite backend : **402 tests réussis, 0 échec**. Les anciens tests qui encodaient « prompt + suffixe » ont été mis à jour, la différence voulue étant documentée.

### Génération depuis l'application — état réel

Démontré :
- Backend authentifié (cookie de session) : `POST /api/media/images` avec le corps envoyé par le bouton (`model=comfy`, `aspect_ratio=1:1`).
- Preset par défaut `flux-dev` : erreur explicite en français, qui liste `flux1-dev-fp8` manquant et les modèles présents. Le média passe en `error` avec ce message.
- Réglage `image_preset` passé à `sdxl` (checkpoint `sd_xl_base_1.0.safetensors`) via `PUT /api/settings/comfyui`, base `localaistudio_nextgen_original`. Réversible ; aucune autre valeur modifiée.
- Génération SDXL réussie : **27,3 s** (chargement inclus), PNG de 1,05 Mo, média `done` visible dans `GET /api/media`. Image : `backend/bench_runs/app_flow/349182bf-8fa3-4598-ae62-27865428ea89.png`.

Non démontré :
- **Parcours de clic dans l'interface non validé.** Le navigateur intégré n'offre qu'une fenêtre d'environ 83 px de haut ; le clic par référence et l'activation clavier n'ont pas déclenché de `POST` (aucune trace côté backend ni proxy). Cause non identifiée : à vérifier sur votre poste.
- Affichage de la bibliothèque et du lecteur dans l'interface : non vérifié visuellement.

Points relevés, non corrigés :
- Au démarrage, le backend a fait passer un média `pending` de `localaistudio_nextgen_original` en `error` (« Interrompue par un redémarrage ») : comportement normal de `_recover_interrupted`, mais c'est une écriture sur des données existantes.
- Si le jeton d'amorçage a déjà été consommé, l'interface reste vide (401 silencieux) sans invite de reconnexion.
- Une installation neuve garde le preset `flux-dev` par défaut (absent) : l'erreur est claire, mais le repli automatique vers un modèle présent n'est pas implémenté (décision à prendre, car il change un défaut).
- `POST /api/settings/comfyui/test` exige un corps (422 sans corps).
- L'édition installée (`AppData\Local\LocalAiStudio-Editions\NextGen-Avant-Fusion`) n'a pas ces corrections et son backend n'a pas d'authentification : elle doit être mise à jour. Je n'y ai pas touché sans accord.

### Comparaison photo — cas spatial

Cas : « Un flacon de parfum bleu au centre avec son bouchon doré posé séparément à droite, sur une surface en marbre blanc. » Seeds 1001 à 1004, identiques entre approches. Paramètres par preset : SDXL 1024², 30 steps, CFG 6,5, dpmpp_2m karras ; FLUX Schnell 1024², 4 steps, CFG 1,0, euler.

Runs : `backend/bench_runs/20261109-210428` (SDXL) et `backend/bench_runs/20261109-211459` (FLUX Schnell), 32 rendus, 0 échec. Galerie : `backend/bench_runs/photo_spatial_compare/` (`grid_sdxl.png`, `grid_flux_schnell.png`, `summary.md`, `index.html`), générée par `backend/scripts/photo_compare_grid.py`.

Mesures brutes (`summary.md`) :

| Modèle | Approche | Durée moy. (s) | Min–max (s) | Prompt (car.) |
|---|---|---|---|---|
| SDXL | A0 brut | 22,4 | 22,4–22,5 | 115 |
| SDXL | A historique | 22,5 | 22,4–22,5 | 187 |
| SDXL | B V2-A | 45,7 | 22,7–62,7 | 310 |
| SDXL | C contraintes | 58,3 | 52,7–62,8 | 187 |
| FLUX Schnell | A0 brut | 40,2 | 34,6–46,7 | 115 |
| FLUX Schnell | A historique | 44,7 | 40,6–46,7 | 187 |
| FLUX Schnell | B V2-A | 50,8 | 42,9–68,8 | 115 |
| FLUX Schnell | C contraintes | 60,2 | 36,6–117,0 | 187 |

Évaluation visuelle (examen des grilles, 4 seeds × 4 approches, sans note chiffrée) :

- **Fidélité spatiale** : SDXL n'a jamais posé le bouchon doré séparément à droite (bouchon sur le flacon dans 3 seeds sur 4 ; au seed 1002, une petite sphère dorée apparaît à droite). FLUX Schnell place un **objet séparé à droite dans 4 seeds sur 4**, pour les quatre approches. Mais cet objet **n'est pas doré** (bleu, noir ou crème) : la couleur n'est pas respectée.
- **Réalisme** : FLUX Schnell donne un éclairage plus photographique et moins de rendu « CGI » que SDXL (appréciation visuelle seule, sans métrique objective).
- **Défauts** : SDXL produit des textes illisibles sur le flacon (B, seed 1003). FLUX Schnell ajoute des étiquettes avec des noms de marque inventés, non demandées.
- **Régularité** : la composition varie fortement selon le seed dans les deux modèles (SDXL seed 1004 : branches dorées et pétales ; FLUX seed 1002 : flacon centré à gauche).
- **Approches** : A_legacy et C sont identiques sur ce prompt à une phrase (attendu). A0 et A se ressemblent fortement en FLUX : le suffixe qualité a peu d'effet. B ajoute un préambule anglais générique sans amélioration nette.

Hypothèses techniques (non démontrées) :
- Les durées élevées de B et C (SDXL et FLUX) apparaissent après la préparation LLM de B : Ollama (qwen2.5-coder:14b, environ 8 Go de VRAM) semble occuper la VRAM ou être rechargé, ce qui ralentit ComfyUI. Vérification possible : préparer tous les prompts avant tout rendu, décharger Ollama, puis rendre. Tant que ce n'est pas fait, les durées de B et C ne sont pas comparables.

### Limites

- Un seul sujet, quatre seeds, un seul cas spatial. Aucune métrique objective de fidélité ou de qualité. Évaluation visuelle par un seul examinateur.
- Aucun test de portrait ni de vidéo.
- Aucun test de relance dans l'interface (voir plus haut).

### Alternatives techniques (non testées)

- Contrôle spatial par régions (`ConditioningSetArea` + `ConditioningCombine` dans ComfyUI) : sans téléchargement, à tester sur le cas spatial.
- Composition en deux passes : génération du flacon, puis du bouchon séparément, puis assemblage.
- FLUX Dev (`flux1-dev-fp8`) : fidélité meilleure attendue, mais fichier absent ; téléchargement à autoriser.
- Couleur spécifique : inpainting ciblé ou prompt de couleur renforcé, à tester.

### Recommandation pour la prochaine étape

1. Vérifier le parcours de clic dans l'interface sur votre poste (génération, progression, bibliothèque).
2. Corriger la mesure de durée (préparation LLM avant rendu, déchargement d'Ollama), puis relancer B et C.
3. Tester la composition régionale (sans téléchargement) sur le cas spatial, avec au moins 8 seeds.
4. Décider du modèle par défaut après ces résultats ; FLUX Schnell est un candidat crédible pour la mise en page, pas encore un choix.

## V2-E — Étape 1 : interface Photo entièrement utilisable (validée)

Parcours testé dans **Chrome, fenêtre normale** (pilotage Playwright via protocole de débogage, pas la prévisualisation 83 px), backend de test `127.0.0.1:8002`, Vite `127.0.0.1:3001`, base `localaistudio_nextgen_original`, ComfyUI `127.0.0.1:8188`.

Validé :
- **Session** : première fenêtre OK (cookie `HttpOnly`) ; sans cookie → 401 ; fenêtre neuve après consommation du jeton → message « Session non ouverte » (avant : page vide sans explication).
- **Sélection du modèle** : sélecteur dans Studio (FLUX.1 dev grisé « non installé », FLUX.1 schnell et SDXL « installé »). Le choix est transmis au rendu (`comfy_preset`) ; l'historique ComfyUI confirme le checkpoint réellement utilisé (`flux1-schnell-fp8` 4 étapes ; `sd_xl_base_1.0` 30 étapes `dpmpp_2m`).
- **Génération** : clic sur « Générer la photo » → `POST /api/media/images` 200 → rendu terminé (FLUX Schnell 23,0 s, SDXL 29,0 s, incluant le chargement).
- **Progression réelle** : « étape 4/30 … 29/30 » en direct depuis le WebSocket ComfyUI (avant : seulement le temps écoulé).
- **Résultat et bibliothèque** : carte de résultat, bibliothèque avec les 5 photos, téléchargement d'un PNG valide (1,4 à 1,7 Mo).

Cause du blocage précédent : l'outil de navigation limitait la fenêtre à 83 px, ce qui faisait tomber les clics hors du bouton. En fenêtre normale, le clic déclenche bien la requête : **ce n'était pas un défaut de l'application**.

Corrections apportées (commit de l'étape) :
- `comfy.py` : `image_settings()` (preset par requête, validé), `image_model_status()`, progression WebSocket (`progress_from_ws`, `_ws_progress`) avec repli sur le temps écoulé ; `client_id` unique par rendu ; avertissement journalisé si `websockets` est absent.
- `routers/media.py`, `models/schemas.py` : champ `comfy_preset` (Literal, valeurs inconnues rejetées).
- `routers/engines.py` : `GET /api/settings/comfyui/image-models` (installé / non installé / inconnu).
- Frontend : sélecteur `photo-preset-picker`, bouton bloqué seulement si aucun modèle n'est installé, `main.tsx` affiche « Session non ouverte » seulement sur un refus explicite (401/403).
- `requirements.txt` : `websockets==17.4`.

Tests : 421 passés (backend), dont 16 ciblés incluant un vrai test WebSocket contre un serveur local ; `tsc` sans erreur.

Limites et non-validé :
- La progression par étapes a été observée sur SDXL ; FLUX Schnell n'a pas été relancé après la correction (même mécanisme).
- La tuile de bibliothèque n'indique pas le modèle utilisé (seul l'historique ComfyUI le prouve).
- Le venv du dépôt `backend/.venv` ne contient pas `uvicorn` (présent dans `requirements.txt`) : l'installation Windows n'est pas complète sur cette machine (voir Mission 2).
- Le lanceur officiel utilise les ports 8001/3000, occupés par l'édition installée : non testé tel quel.
- Trois photos de test ont été ajoutées à la base `localaistudio_nextgen_original` (aucune photo existante modifiée ou supprimée).
- Les erreurs 403 de polices dans la console sont dues à la jonction `node_modules` de l'environnement de test, pas au produit.

## V2-E — Étape 2 : édition distincte corrigée (validée), édition installée non modifiée

Build : `scripts/build-parallel-edition.ps1` → `%LOCALAPPDATA%\LocalAiStudio-Editions\NextGen-V2E` (commit `82fccde`, 142 fichiers suivis). Ports 8011 (backend) / 3011 (interface), écoute `127.0.0.1`, lanceur `start-localaistudio-v2e.bat`, cookie de session `las_session_v2e`, base `localaistudio_nextgen_original` (choix à confirmer : c'est la base où se trouve le travail NextGen ; l'édition installée lit `localaistudio`, vide).

Préservé : bases (sauvegarde logique préalable, voir ci-dessous), modèles (ComfyUI partagé, aucune copie), configuration (`backend/.env` créé une fois, jamais écrasé par un rebuild). Non copiés : `.env`, `.api_key`, `.boot_token`, `bench_runs/`, venv, node_modules (le venv est copié en lecture seule puis synchronisé ; `node_modules` est une jonction vers celui de l'édition installée, à remplacer par une vraie installation avant diffusion).

Validé dans Chrome (fenêtre normale) :
- Démarrage par son propre lanceur, écoute uniquement sur `127.0.0.1:8011` et `127.0.0.1:3011`.
- Sans cookie : `401` sur `/api/media`.
- CORS : seule l'origine locale `http://127.0.0.1:3011` est renvoyée ; une origine étrangère ne reçoit aucun `Access-Control-Allow-Origin`.
- Première ouverture : initialisation par jeton d'amorçage, cookie `las_session_v2e` distinct de `las_session` (l'édition du dépôt sur 3001 garde sa session).
- Génération SDXL de bout en bout : POST 200, rendu terminé en 28,7 s, `ckpt=sd_xl_base_1.0`, 30 étapes ; téléchargement PNG valide (1,33 Mo).

Bug trouvé et corrigé (lanceurs officiel et V2-E, commit `82fccde`) : la génération du jeton via `powershell` dans `for /f` contenait des guillemets simples imbriqués ; le jeton restait **vide** et l'initialisation renvoyait 401 dans notre test (le fichier de repli `backend/.boot_token` n'a pas été créé). Remplacé par `python -c "import secrets; ..."` (64 caractères hexadécimaux vérifiés). Garde-fou ajouté dans `test_photo_ui_contract.py`.

Sauvegarde préalable (lecture seule, `scripts/backup_db.py`) : `C:/Users/desco/AppData/Local/LocalAiStudio-Backups/20261110-002138` (3 bases, 8,3 Mo, JSON Lines, GridFS inclus).

Constats sur l'édition installée `NextGen-Avant-Fusion` (non modifiée, action à décider par vous) :
- `CORS_ORIGINS=*` et la réponse renvoie l'origine demandée (`Access-Control-Allow-Origin: https://evil.example`) : une page web ouverte dans votre navigateur peut interagir avec son API.
- Sans cookie, `/api/media` et `/api/projects` répondent **500** au lieu de 401 : la requête atteint le gestionnaire sans contrôle d'authentification (l'erreur 500 vient de l'ancien client Motor corrigé en `d005a34`, pas d'un refus d'accès).
- `tunnel-preview.bat` de l'édition installée lance encore `cloudflared` (tunnels publics vers Ollama et ComfyUI, sans authentification). Aucun tunnel n'était actif au moment du contrôle. La version du dépôt est neutralisée depuis V1-B.
- Action recommandée : remplacer l'édition installée par la version V2-E après votre autorisation (son dossier, sa base et ses données restent intacts ; la sauvegarde ci-dessus permet un retour arrière).

Non validé : installation Windows complète par le script `install.ps1` ; installeurs Inno/NSIS (compilateurs absents) ; la version distincte n'a pas encore été testée avec le navigateur par défaut de Windows.
