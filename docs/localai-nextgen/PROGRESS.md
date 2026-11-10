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

## V2-E — Étape 3 : contrôle spatial par régions SDXL (expérience, non adoptée)

Script d'expérience (hors application) : `backend/scripts/regional_sdxl_experiment.py`. Protocole : SDXL base `sd_xl_base_1.0`, 1024², 30 étapes, CFG 6,5, `dpmpp_2m` karras, négatif = `NEGATIVE` de l'application, graines 1001–1008, un rendu à la fois, file ComfyUI vide. Ollama : aucun modèle chargé, vérifié et déchargé avant la campagne (`unloaded=[]`).

Variantes :
- `base_fr` : prompt A0 du benchmark (référence exacte).
- `base_en` : même contenu en un seul prompt anglais (contrôle de la langue).
- `region_en` : prompt global + zone « flacon » (512×768 à x=256, y=128) + zone « bouchon » (256×256 à x=768, y=448), combinées par `ConditioningCombine`.

Mesures brutes (`backend/bench_runs/regional_sdxl/20261110-003252/results.json`, gitignoré) :

| Variante | n | Moyenne (s) | Min–max (s) |
|---|---|---|---|
| base_fr | 8 | 22,5 | 22,4–22,8 |
| base_en | 8 | 22,4 | 22,4–22,8 |
| region_en | 8 | 34,9 | 34,8–34,9 |

Le rendu régional coûte environ 55 % de temps en plus (passes de conditionnement supplémentaires).

Jugement visuel (un seul évaluateur, non aveugle, vignettes 200 px : subjectif, à confirmer) :

| Critère | base_fr | base_en | region_en |
|---|---|---|---|
| Flacon bleu | 8/8 | 8/8 | 4/8 (les autres : ambre, clair/blanc, ou motif de cartes) |
| Bouchon doré | environ 8/8 | 8/8 | 1/8 |
| Bouchon séparé à droite | 0/8 | 1/8 | 0/8 (3/8 avec un objet décoratif chromé à droite, pas un bouchon) |

Décision : contrôle par régions **non adopté**. Il dégrade la fidélité des couleurs demandées et ne produit pas le bouchon séparé. Workflows par défaut inchangés (aucune amélioration démontrée). La campagne en une graine de vérification (`20261110-003123`) est conservée.

Limites : un seul sujet, 8 graines, un seul évaluateur, zones non optimisées, régions en anglais seulement (français non testé), pas de métrique objective. Le doute sur B et C de l'ancien benchmark (possiblement liés à Ollama) n'est pas tranché : Ollama était déjà déchargé pendant cette campagne et ces deux approches n'ont pas été relancées.

Pistes non testées : inpainting SDXL en deux passes (sans téléchargement, avec le checkpoint existant) ; FLUX Dev (téléchargement à autoriser) ; ControlNet ou IP-Adapter (téléchargements à autoriser).

## V2-F — Étape 1 : export ZIP sécurisé

- `/api/kit/download` ne parcourt plus les dossiers locaux : `backend/kit_manifest.txt` est une liste explicite, révisable et livrée sans dépendance à Git. Les fichiers absents, les chemins dangereux, liens symboliques, jonctions Windows, liens physiques et entrées privées rendent l'export indisponible (503), sans archive partielle. Pas de repli sur un balayage.
- Aucune copie des `.env*`, `.api_key`, `.boot_token`, environnements Python/Node, benchmarks, modèles ou médias utilisateur. L'ancien générateur pointait vers `local-kit` absent et omettait les scripts d'installation : le ZIP contient maintenant les sources et scripts explicitement listés. Le modèle d'environnement est un fichier d'exemple `installer/env.template`, pas la configuration locale.
- Tests : 33 ciblés (route réellement authentifiée, jeu de faux secrets et données, refus de parcours de chemins, lien physique et jonction Windows), puis 450 tests backend passés. Mongo pointé sur `127.0.0.1:1` et base de test fictive : aucune écriture en base utilisateur. Export réel contrôlé : 113 fichiers, CRC valide, aucun secret ou dossier local interdit trouvé dans les noms.
- Limite : le manifeste de distribution doit être mis à jour explicitement lorsqu'un fichier indispensable est ajouté. Les installateurs et leurs modèles de configuration restent à traiter pendant l'étape distribution.

## V2-F — Étape 2 : sessions, réseau et ancien backend

- Un test réseau a révélé que Vite répondait `Access-Control-Allow-Origin: *` même devant un backend au CORS restreint. Corrigé par défaut (`cors: false` sauf exposition explicitement demandée avec `LAS_VITE_EXPOSE=1`). Le proxy n'injecte le jeton que sur `POST /api/auth/init` exact ; une origine étrangère et `Sec-Fetch-Site: cross-site` sont rejetés avant consommation du jeton.
- Exemptions limitées aux lectures de prévisualisations/médias et à l'init POST exact ; comparaisons de jetons à temps constant et résistantes aux caractères non ASCII. Les fichiers médias et prévisualisations restent volontairement lisibles sans cookie quand leur URL est connue : nécessaires aux prévisualisations sandboxées ; ce n'est pas une protection contre un autre processus local.
- Test réel Vite + backend sur ports isolés, sans démarrage de Mongo : origine étrangère 403 (sans ACAO), export sans session 401, ouverture locale 200 avec cookie HttpOnly/SameSite=Strict, export authentifié 200, rejeu du jeton 401, preflight étranger 400. Interface chargée dans le navigateur avec backend factice ; aucune erreur console après configuration des réponses factices. `tsc` OK ; 458 tests backend passés.
- `docs/localai-nextgen/V2-F-ANCIENNE-EDITION.md` décrit une neutralisation réversible à soumettre à autorisation. Aucune action sur l'ancienne édition : son API 8001 reste sans authentification et CORS `*`, son script de tunnel demeure dangereux ; aucun processus cloudflared actif au contrôle. Les instances V2-E déjà lancées utilisent encore leur ancien code tant qu'elles ne sont pas mises à jour/redémarrées.

## V2-F — Étape 3 : sauvegarde logique vérifiée avant distribution

- `scripts/backup_db.py` utilise le JSON étendu canonique BSON (préservation des ObjectId, Int64, dates et données binaires GridFS), refuse d'écraser un répertoire de sauvegarde existant et propose `--verify`. Les documents exportés sont comparés par empreinte SHA-256 à une nouvelle lecture de chaque collection ; aucune écriture MongoDB.
- Sauvegarde `C:/Users/desco/AppData/Local/LocalAiStudio-Backups/V2F-20261110-010754` : `localaistudio`, `localaistudio_nextgen_original` (1 projet, 6 médias, 6 fichiers et 34 blocs GridFS) et `localaistudio_fusion_beta` ; toutes les collections correspondent au moment de la vérification. Documents `_manifest.json` et `_verification.json` fournis. Taille : environ 10 Mo.
- Limites : ce n'est pas un snapshot atomique et aucune restauration n'a été testée ; les données de `fusion_beta` portent des statuts actifs historiques et n'ont pas été modifiées. La file ComfyUI était vide lors du relevé.
- Tests : 9 tests de sauvegarde (dont types BSON, GridFS, modification détectée et non-écrasement), 467 tests backend passés. Les tests utilisent une base Mongo fictive et n'accèdent pas aux bases utilisateur.

## V2-F — Étape 4 : dépendances Windows indépendantes

- Le runtime local est figé dans `requirements-local.txt` (23 paquets directs et transitifs) ; `requirements-windows-py311.lock` contient les SHA-256 des roues Windows x64 / CPython 3.11, installables avec `--require-hashes --only-binary=:all:`. Les moteurs payants restent optionnels, non requis pour démarrer le moteur local.
- Création d'un venv entièrement neuf depuis les roues vérifiées (5,5 Mo, cache local), `pip check` et import réel du serveur réussis. `uvicorn==0.52.1` et `websockets==17.4` sont présents. Le venv du dépôt a aussi été synchronisé sur ce runtime : `uvicorn`, `python-multipart`, `tzdata` et `click` manquants ajoutés ; FastAPI et pymongo remis aux versions indiquées par le dépôt. `pip check` OK.
- Préparation de Yarn 1.22.22 local via `installer/tooling/package-lock.json` (intégrité npm) ; aucun lien vers l'ancienne édition nécessaire. Le futur installateur doit encore utiliser cet outil et `frontend/yarn.lock`.
- Tests : 469 backend passés, dont vérification du lock et de son inclusion dans le kit. Limites : ce lock vise Windows x64/Python 3.11 ; pas de validation d'un .exe ni de machine Windows vierge à ce stade. Le fichier historique `backend/requirements.txt` contient encore des dépendances développeur/optionnelles non utilisées par ce runtime.

## V2-F — Étape 5 : installation Windows isolée, test réel

- `install-v2f.bat` / `scripts/build-parallel-edition.ps1` construisent une **nouvelle** édition depuis le manifeste explicite, sans Git obligatoire ni copie/jonction d'un autre environnement. Refus d'une cible existante, d'une jonction dans son chemin ou d'un chevauchement avec le dépôt/les éditions existantes. Si une installation échoue, le dossier partiel reste à inspecter ; aucune suppression automatique.
- Python 3.11 x64, Node 20.19+ ou 22.12+ et npm requis ; pip vérifie toutes les empreintes des roues, npm vérifie Yarn 1.22.22, puis Yarn installe avec son lock et compile l'interface. Le lanceur n'installe ni ne démarre MongoDB, Ollama ou ComfyUI et ne télécharge aucun modèle. Vérification des ports, écoute loopback, CORS limité, cookie propre et jeton à usage unique.
- Base vide `las_v2f_<identifiant aléatoire>` distincte ; le premier lancement vérifie en lecture seule qu'elle n'existe pas avant de créer un marqueur local. Aucune migration. Tests réels dans `C:/Users/desco/AppData/Local/Temp/LocalAiStudio V2F Test 01` et `... Test 02` : venv et node_modules sont de vrais répertoires, compilation `tsc -b && vite build` réussie (avertissement de gros bundle), démarrage par le lanceur sur 8031/3031, UI et sélection des modèles visibles, console sans erreur. Premier essai : sans cookie 401, origine étrangère 403, préflight 400, connexion locale 200 ; ComfyUI 8188 et Ollama 11434 détectés. Aucune génération.
- Les deux bases de test `las_v2f_35535a3366d2fd9c3711` et `las_v2f_276f5c7d2a6566f08772` ont été créées et conservées. Les 3 bases utilisateur correspondent encore document par document à la sauvegarde V2-F après les essais. Refus d'écraser un dossier existant vérifié via le .bat. 484 tests backend passés.
- Ce résultat valide l'installateur **script**, pas un `.exe` compilé/signé ni une machine vierge. Les anciens scripts Inno/NSIS ne sont pas recommandés ; l'édition V2-E existante n'est pas encore déliée dans cette étape.

## V2-F — Étape 6 : préparation vidéo (inventaire, compatibilité RTX 3060, recommandation)

Inventaire des modèles vidéo réellement installés (ComfyUI-Shared, vérifié via `object_info` et listing disque) :
- `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors` (3,2 GB, `models/diffusion_models/`) — UNETLoader, compatible RTX 3060 12 Go
- `ltx-2.3-22b-dev-fp8.safetensors` (29,1 GB, `models/checkpoints/`) — CheckpointLoaderSimple, trop volumineux pour 12 Go de VRAM
- VAE : `wan_2.1_vae.safetensors`, `ltx-2.5-video-vae-bf16.safetensors` présents
- CLIP : `umt5_xxl_fp8_e4m3fn_scaled.safetensors`, `t5xxl_fp8_e4m3fn.safetensors` présents

Présets dans `VIDEO_PRESETS` (`backend/lib/comfy.py`, inchangés par défaut) :
- `wan22` (Wan 2.2 TI2V 5B) : modèle `wan2.2_ti2v_5B_fp16.safetensors` ABSENT, text_encoder présent, VAE `wan2.2_vae.safetensors` ABSENT → génération vidéo échouera si sélectionné
- `ltxv` (LTX-Video 2B) : modèle `ltx-video-2b-v0.9.5.safetensors` ABSENT, text_encoder `t5xxl_fp16.safetensors` ABSENT → génération vidéo échouera si sélectionné
- `wan21_fun_camera` (ajouté) : modèle PRÉSENT, text_encoder PRÉSENT, VAE PRÉSENT → prêt pour vérification

Modification : `backend/lib/comfy.py`
- Ajout du preset `wan21_fun_camera` (Wan 2.1 Fun Camera 1.3B, RTX 3060 12 Go)
- Constante `UNET_BASED_VIDEO_PRESETS = {"wan22", "wan21_fun_camera"}` pour la vérification des modèles (UNETLoader vs CheckpointLoaderSimple)
- `verify_ready` et `_model_requirements` reconnaissent les deux presets UNET
- Le `video_preset` par défaut reste `wan22` (aucun changement de comportement par défaut, aucun modèle n'est téléchargé)
- `_video_workflow` n'a pas de branche dédiée à `wan21_fun_camera` : ce preset nécessite un `custom_video_workflow` utilisateur (nodes WAN 2.1 spécifiques non intégrés par défaut)

Meilleur candidat T2V/I2V pour RTX 3060 12 Go : **Wan 2.1 Fun Camera 1.3B** (3,2 GB, VRAM compatible). LTX 2.3 22B (29 GB) est hors de portée de 12 Go.

Optimisations proposées (non testées) :
- Quantification fp8/bf16 déjà appliquée sur les modèles installés
- Chargement séquentiel (un modèle à la fois) pour éviter la fragmentation VRAM
- `custom_video_workflow` utilisateur pour WAN 2.1 Fun Camera

Tests : 104 tests comfy/kit passés. Aucune génération vidéo lancée (pas de workflow WAN 2.1 validé, pas de téléchargement de modèle).

## V2-G — Première vidéo locale réelle (réalisé)

Commit : `2890de6` sur `nextgen/claude-code`. Poussé et confirmé.

### Objectif

Première génération vidéo locale réelle sur RTX 3060 12 Go via l'API authentifiée de LocalAiVision, avec le modèle Wan 2.1 Fun Camera 1.3B (Image-to-Video avec contrôle de caméra).

### Corrections apportées

**`backend/lib/comfy.py`** :
- `_video_workflow()` : les presets inconnus sont refusés explicitement, jamais routés vers la branche LTX par défaut
- Nouvelle branche `wan21_fun_camera` : `UNETLoader` + `CLIPLoader` + `VAELoader` + `ModelSamplingSD3` + `CLIPVisionLoader` + `CLIPVisionEncode` + `WanCameraEmbedding` + `WanCameraImageToVideo` + `KSampler` + `VAEDecode` + `CreateVideo` + `SaveVideo`
- Wan 2.1 Fun Camera est Image-to-Video uniquement : refuse sans image de référence (`ref_media_id` obligatoire)
- `video_settings(s, preset)` applique le preset avant `verify_ready()` pour que les bons modèles soient vérifiés
- `video_model_status()` retourne l'état d'installation de chaque preset vidéo

**`backend/models/schemas.py`** :
- `VideoRequest` : nouveaux champs `camera_pose` (Literal) et `comfy_preset` (Literal, valeurs inconnues rejetées)

**`backend/routers/media.py`** :
- `create_video()` applique `comfy.video_settings(s, body.comfy_preset)` avant `verify_ready(s, video=True)`
- `POST /api/media/videos` accepte `camera_pose` et `comfy_preset`

**`backend/tests/test_comfy_v1d.py`** :
- Test : preset non supporté refusé
- Test : I2V sans image de référence refusé
- Test : construction complète du workflow Wan 2.1 Fun Camera I2V (tous les nœuds, connexions, modèles)

### Première génération vidéo — résultat réel

**Requête API** (via `POST /api/media/videos`, authentifié) :
- Prompt : « un flacon bleu sur marbre, bouchon doré à droite »
- Modèle : `comfy`, mode `image`, durée `3s`, ratio `16:9`
- Pose caméra : `Zoom In`
- Preset : `wan21_fun_camera`
- Image de référence : photo SDXL générée précédemment (flacon bleu, bouchon doré, marbre)

**Résultat** :
- Média créé : `4e4f076d-d699-4484-aba5-238dd87c8c71`, statut `done`
- Fichier : `backend/bench_runs/video_wan21_api/video_00001_.mp4`
- Taille : 360 834 octets (~352 Ko)
- Format : h264 MP4, 832×480, 24 fps, 73 frames, durée 3,04 s
- Temps de génération : ~412 s (6 min 52 s), dont ~400 s pour les 20 étapes de dénoisage
- Progression WebSocket : « étape 1/20 … 20/20 » en direct

**Évaluation visuelle (4 frames extraites)** :
- Frame 1 (0 s) : flacon bleu avec bouchon doré sur marbre — conforme à l'image de référence
- Frame 2 (0,13 s) : début du zoom avant
- Frame 3 (0,25 s) : zoom en cours, flacon plus grand
- Frame 4 (0,38 s) : zoom poursuivi, cadrage serré sur le flacon

**Qualité** :
- Identité de l'image de référence préservée (flacon bleu, bouchon doré, marbre)
- Mouvement de caméra (zoom avant) fluide et cohérent
- Pas d'artefact majeur visible sur les 4 frames examinées
- La couleur dorée du bouchon est respectée

### Limitations

- Temps de génération élevé (~412 s pour 3 s de vidéo à 832×480, 20 étapes) : le modèle 1.3B est lent sur RTX 3060 12 Go
- VRAM non mesurée pendant cette exécution (pas de relevé nvidia-smi durant le rendu)
- Un seul sujet, une seule seed, une seule pose caméra (Zoom In)
- Aucune métrique objective de qualité ou de stabilité temporelle
- Le preset `wan22` (Wan 2.2 TI2V 5B) et `ltxv` (LTX-Video 2B) restent non installés : seul `wan21_fun_camera` est utilisable
- Le preset par défaut reste `wan22` (inchangé) : l'utilisateur doit choisir `wan21_fun_camera` explicitement

### Recommandations

1. Mesurer la VRAM pendant une génération vidéo (nvidia-smi en parallèle)
2. Tester d'autres poses caméra (Pan Left/Right, Tilt Up/Down, Rotate)
3. Tester avec plusieurs seeds pour évaluer la stabilité
4. Envisager FLUX Dev pour une meilleure fidélité photo (fichier absent, téléchargement à autoriser)
5. Tester la composition régionale (`ConditioningSetArea`) pour le contrôle spatial sans téléchargement

### Tests

- 487 tests backend passés (dont 104 comfy/kit, 16 V2-E WebSocket, nouveaux tests V2-G)
- `tsc` sans erreur
- Aucun test GPU vidéo supplémentaire lancé (la génération réelle via l'API sert de validation)

### Fichiers modifiés

- `backend/lib/comfy.py` — branche wan21_fun_camera, refus des presets inconnus, `video_settings`, `video_model_status`
- `backend/models/schemas.py` — `camera_pose` et `comfy_preset` dans `VideoRequest`
- `backend/routers/media.py` — application du preset avant vérification, acceptation des nouveaux champs
- `backend/tests/test_comfy_v1d.py` — 3 nouveaux tests V2-G
- `docs/localai-nextgen/PROGRESS.md` — cette section

## V2-H — intégration vidéo, mesures et validation Chrome (réalisé)

### Correctifs
- Interface vidéo : sélection du preset ComfyUI avec état réel installé/absent, commandes caméra, transmission de `comfy_preset` et `camera_pose`; Wan Fun Camera force I2V et requiert une référence.
- Durée : la durée initiale de l'UI est maintenant 3 s, évitant le défaut où la valeur initiale vide était remplacée par le dernier choix (5 s). Le backend mappe explicitement 3 s → 73 frames et 5 s → 121 frames; les valeurs inconnues sont refusées au lieu d'être silencieusement interprétées comme 3 s.
- Pic VRAM : le sampler `nvidia-smi` accepte maintenant `vram_peak_mib=None` (première mesure initialise le pic au lieu d'évaluer `max(int, None)`). Tests de régression ajoutés.
- Diagnostic vidéo persisté dans le média : temps total, intervalle de débruitage, moyenne par étape, nœud d'encodage, VRAM de base/pic et contexte (modèle, seed, résolution, FPS, frames, sampler, CFG/steps). Le WebSocket a un repli par horloge murale lorsque des événements de démarrage sont manqués.

### Validation réelle — une seule génération après correction

- Chrome réel, profil temporaire, application sur `127.0.0.1:3003` avec backend et base Mongo de test `localaistudio_v2h_test` (pas les bases utilisateur).
- Le POST UI a transmis exactement `duration="3"`, `comfy_preset="wan21_fun_camera"`, `camera_pose="Pan Left"`, `mode="image"`; le workflow ComfyUI confirme 73 frames et 20 étapes.
- Progression WebSocket visible jusqu'à 20/20. Média `done`, vidéo lue dans l'élément HTML et téléchargement vérifié.
- Résultat local ignoré par Git : `backend/bench_runs/v2h/ui_pan_left_3s.mp4` (255 613 octets); planche de toutes les frames : `backend/bench_runs/v2h/ui_pan_left_all_frames.jpg`.
- Décodage exhaustif des 73 frames : H.264, 832×480, 24 fps, durée 3,0417 s.
- Mesures enregistrées sur le média : ComfyUI 461,359 s; échantillonnage 423,953 s, 20 étapes observées (~22,313 s par intervalle); nœud SaveVideo 1,454 s. La première étape apparaît ~15 s après la soumission dans l'UI; le chargement du modèle n'est pas isolé des autres préparatifs.
- VRAM système : base 3 562 MiB, pic 10 344 MiB / 12 288 MiB, delta 6 782 MiB. Un échantillonnage indépendant a observé le même pic.
- Examen visuel de toute la séquence : flacon reconnaissable et stable, sans artefact majeur évident; le déplacement « Pan Left » reste faible/subtil et l'étiquette/textures fluctuent légèrement. Le mouvement n'est pas encore professionnellement convaincant. Les différences inter-images calculées sont descriptives, pas une métrique de qualité.

### Tests et limites
- Suite complète backend finale : 501 réussis, 0 échec (5 avertissements de dépréciation de dépendances); TypeScript (`tsc --noEmit -p tsconfig.app.json`) réussi; `git diff --check` propre.
- Un premier essai UI a généré 121 frames (5 s) alors que le testeur voulait 3 s; interrompu. Le rendu suivant à 73 frames a terminé, mais l'ancienne version du sampler a ensuite remonté `'>' not supported between NoneType and int`; correctif couvert et génération de contrôle réussie.
- La génération de contrôle a utilisé `localaistudio_v2h_test`; aucune base utilisateur, création existante ou aucun modèle n'a été modifié dans cette validation.
- Les mesures de chargement et pré/post-sampling restent partielles si le WebSocket manque des événements; la VRAM est globale, échantillonnée toutes les ~0,75 s, pas par processus.
- Aucun moteur ni paramètre d'inférence par défaut n'a été remplacé. Pas de V2-I.

### Fichiers V2-H

- `backend/lib/comfy.py`, `backend/models/engines.py`, `backend/models/schemas.py`
- `backend/routers/engines.py`, `backend/routers/media.py`
- `backend/tests/test_video_v2h.py`, ajustements de compatibilité dans `backend/tests/test_comfy_reliability.py` et `backend/tests/test_comfy_v1d.py`
- `frontend/src/components/vision.tsx`, `frontend/src/lib/companyHooks.ts`, `frontend/src/lib/companyTypes.ts`, `frontend/src/lib/types.ts`
- `docs/localai-nextgen/PROGRESS.md`

Validation V2-H committée sur `nextgen/claude-code` après les tests finaux.

## V2-I — optimisation mesurée du workflow vidéo (réalisé, optimisation non activée par défaut)

### Environnement et protocole
- ComfyUI Desktop existant sur `127.0.0.1:8188`, version API `0.37.2`, PyTorch `2.12.1+cu130`, RTX 3060 12 Gio. File vide avant l'essai ; Ollama n'avait aucun modèle chargé.
- Aucun paquet, modèle ou installation n'a été téléchargé ou modifié.
- Comparaison sur le même historique V2-H : même seed `753934134`, image d'entrée `las_5bd50f6f4a.png`, prompt, pose `Pan Left`, 832×480, 73 frames, 24 fps, 20 steps, CFG 6, `uni_pc`/`simple`.
- Une seule modification expérimentale : insertion du nœud ComfyUI `ModelAttentionBackend` avec `comfy kitchen attention` (attention dense INT8 Comfy Kitchen). Le workflow actif de LocalAiVision n'a pas été modifié.

### Mesures observées
| Mesure | Référence V2-H (PyTorch attention) | Comfy Kitchen INT8 | Écart |
|---|---:|---:|---:|
| Mesure | Référence PyTorch | Comfy Kitchen INT8 | Écart observé |
|---|---:|---:|---:|
| Temps ComfyUI start→success, seed 753934134 appariée | 447,069 s | 286,813 s | −35,9 % |
| Intervalle d'échantillonnage (mesure V2-H distincte / cette expérience) | 423,953 s | 254,391 s | indicatif : −40,0 % |
| Pic VRAM global (mesure V2-H distincte / cette expérience) | 10 344 MiB | 9 989 MiB | indicatif : −355 MiB (−3,4 %) |
| Durée MP4 | 3,0417 s | 3,0417 s | identique |
| Taille vidéo | 258 414 o | 262 161 o | +1,5 % |

La comparaison visuelle et le temps ComfyUI start→success sont appariés sur le même seed `753934134`. Les temps d'échantillonnage et pics VRAM de V2-H proviennent d'une autre génération de mêmes paramètres dont le seed n'a pas été enregistré dans le résumé UI : ces deux deltas sont indicatifs, pas une mesure A/B strictement appariée. Le rendu expérimental a gardé 20 étapes et 73 images ; aucune réduction de résolution, FPS, durée ou steps. `nvidia-smi` a relevé une utilisation GPU généralement à 100 % pendant l'échantillonnage. Cela, ainsi que la part dominante des étapes, pointe vers le calcul de débruitage/attention comme levier principal ; aucun profilage Nsight n'a été effectué, donc le partage exact calcul/bande passante/transferts reste non démontré.

### Qualité — examen exhaustif des frames
- Les deux MP4 ont été décodés en entier : 73/73 frames chacun, mêmes dimensions, cadence et durée.
- Planche appariée de toutes les frames : `backend/bench_runs/v2i/paired_all_frames.jpg`. Mesures descriptives locales dans `visual_comparison_summary.json` (erreur moyenne inter-images réduites : 1,012/255 entre sorties ; MAE temporelle 3,088 contre 3,102). Ces différences de pixels ne sont pas des scores de qualité.
- À l'examen visuel côte-à-côte, le flacon, ses couleurs et le décor paraissent stables et quasi identiques ; aucun nouvel artefact évident. Le mouvement Pan Left reste faible dans les deux versions : l'attention INT8 n'améliore pas l'amplitude caméra.
- Cette vérification sur une seed est un criblage qualitatif, pas une preuve statistique d'absence de dégradation sur tous les prompts/seeds.

### Décision et prochaines pistes
- Gain de vitesse substantiel démontré sur cet essai, sans dégradation visuelle évidente ; le workflow de production reste inchangé tant qu'une comparaison multi-seed n'a pas confirmé le résultat. V2-I n'introduit donc aucune modification comportementale dans l'application.
- Le temps expérimental reste 286,8 s, au-dessus de l'objectif progressif de 180 s ; il faudrait encore environ 37 % de réduction.
- Piste suivante prioritaire : comparaison multi-seed du backend Comfy Kitchen INT8. SageAttention/xFormers ne sont pas installés ; Triton, SageAttention, xFormers et FlashAttention séparé sont absents de l'environnement inspecté. Torch SDPA reste disponible. `torch.compile` est à faible priorité ici : Triton absent et coût de compilation/compatibilité Windows non mesurés.
- Ne pas accélérer en diminuant silencieusement frames, résolution ou étapes ; le décodage/encodage n'est pas le goulet principal vu la durée mesurée de l'échantillonnage.

### Validation et artefacts locaux
- Tests ciblés : `tests/test_video_v2h.py` + `tests/test_comfy_v1d.py` — 46 réussis. Aucun rendu vidéo supplémentaire après cette comparaison.
- Les vidéos, mesures et scripts expérimentaux sont locaux et ignorés par Git dans `backend/bench_runs/v2i/` : référence `baseline_v2h_seed753934134.mp4`, sortie `comfy_kitchen_int8_seed753934134.mp4`, mesures `comfy_kitchen_int8_metrics.json`, `visual_comparison_summary.json`, planche `paired_all_frames.jpg`.
- Sources consultées : documentation officielle ComfyUI [Model Attention Backend](https://docs.comfy.org/built-in-nodes/ModelAttentionBackend) (backend INT8 et repli PyTorch si indisponible) ; tutoriel PyTorch [Scaled Dot Product Attention](https://docs.pytorch.org/tutorials/intermediate/scaled_dot_product_attention_tutorial.html) (kernels SDPA fusionnés et dispatch CUDA).
- Aucun changement de modèle, workflow par défaut, installation existante ou données utilisateur. Seule cette documentation est ajoutée pour V2-I.

Fin de V2-I : arrêter ici, ne pas activer le backend expérimental par défaut sans validation multi-seed.

## V2-J — LongForm local, prototype de continuité sur deux segments

### But et garde-fous
- Prototype hors production : `backend/lib/video_longform.py`, assemblage local par PyAV `backend/scripts/longform_assemble_av.py`, tests `backend/tests/test_video_longform.py`. **Aucune route, valeur par défaut, workflow de génération existant, modèle ou installation ComfyUI n'a été changé.** Aucun téléchargement, achat ou arrêt de service utilisateur.
- Prototype réel : deux rendus WAN 2.1 Fun Camera I2V de 3 s, segment 2 amorcé par la dernière image décodée du segment 1, reprise par segments via manifeste JSON atomique + empreintes SHA-256. Assemblage local supprime une image au raccord et vérifie la cadence/durée; galerie autonome.
- La reprise refuse un manifeste si le prompt, l'image source, le modèle ou les paramètres diffèrent. Run local/gitignored : `backend/bench_runs/v2j/continuity_two_segment_20261110/` (manifest, deux MP4, deux images de fin, MP4 assemblé, planche contact, rapport). Galerie vérifiée dans le navigateur local.

### Ressources et capacité observées
- Windows x64, 32,65 GiB RAM physique; ComfyUI 0.37.2 / PyTorch 2.12.1+cu130 / Python 3.13.12, RTX 3060 12 Gio. ComfyUI rapportait avant le rendu 15,85 GB RAM libre (~14,78 GiB) et 9,28 GB VRAM libre (~8,64 GiB); nvidia-smi au repos environ 3,3 GiB occupés. Ollama sans modèle chargé; file ComfyUI vide avant l'essai.
- Les quatre poids Wan requis étaient présents d'après `object_info` : `wan2.1_fun_camera_v1.1_1.3B_bf16.safetensors`, `umt5_xxl_fp8_e4m3fn_scaled.safetensors`, `wan_2.1_vae.safetensors`, `clip_vision_h.safetensors`. Pas de rendu LTX effectué (workflow/RAM/VRAM non qualifiés).
- RAM utilisée observée : segment 1, 17 524 MiB au départ / 19 378 MiB pic (13 287 MiB libres minimum); segment 2, 18 080 / 19 160 MiB (13 505 MiB libres minimum). Pas d'épuisement RAM sur le modèle 1,3B; ces chiffres ne prédisent pas la charge d'un modèle plus grand.
- VRAM : le collecteur intégré avait un bug (`max(int, None)`), laissant ses pics `null`. Un moniteur nvidia-smi séparé, ~1 Hz, lancé alors que le segment 2 tournait déjà, a observé jusqu'à **8 074 / 12 288 MiB** pendant le reste de ce segment. C'est un pic observé, pas le pic absolu des deux rendus. Le collecteur est corrigé et couvert par un test pour les essais ultérieurs.

### Rendu vérifié
| Segment | ComfyUI start→success | setup→premier pas | échantillonnage observé | encodage | RAM pic |
|---|---:|---:|---:|---:|---:|
| 1, seed 753934134 | 426,750 s | 22,859 s | 385,016 s / 20 steps | 1,344 s | 19 378 MiB |
| 2, seed 753934135 | 424,453 s | 9,328 s | 396,156 s / 20 steps | 1,344 s | 19 160 MiB |

- MP4 assemblé : H.264, 832×480, 24 fps, **144 images décodées = 6,000 s**, sources de 73 images chacune, une image de raccord retirée, fichier ~665 Ko. PyAV/FFmpeg était déjà présent dans le Python ComfyUI; rien n'a été installé. GPU time total environ 14 min 11 s, hors prévol/fichier.
- Projection non garantie : dix segments × ~425 s = ~71 minutes de calcul pour 30 s. Wan impose 73 images (4n+1) par segment de 3 s; dix segments avec neuf images de frontière partagées produisent 721 candidates, rognées à 720 pour une sortie exactement 30,000 s à 24 fps.

### Qualité et verdict du test de continuité
- Flacon bleu/cobalt, silhouette, décor marbre et lumière restent visuellement cohérents entre segments. Raccord après retrait d'une image : MAE RGB 5,76/255, contre 4,37/255 moyenne entre images internes adjacentes; statistiques descriptives uniquement, pas des scores perceptuels. Planche de toutes les images : `continuity-contact.jpg`.
- **Défaut bloquant avant extension** : répéter `Pan Left` dans le segment suivant cumule le mouvement; le flacon est fortement rogné puis presque hors cadre à la fin du segment 2. Le capuchon initial reste fixé au flacon (il l'est déjà dans l'image source); le texte d'étiquette est illisible.
- **Décision : ne pas lancer 30 s avec cette stratégie.** D'abord tester une politique de pose par segment (trajectoire absolue/pose neutre ou plan-clés avec contrôle de mouvement), puis plusieurs seeds; conserver la reprise par segment et vérifier cadrage, vitesse et stabilité au raccord. Aucun résultat de perfection n'est revendiqué.

### Offload, Dynamic VRAM, Block Swap, VAE Tiling, quantification
- Capacités réellement interrogées sur le ComfyUI installé : `main.py --help` expose `--enable/disable-dynamic-vram`, `--async-offload`, `--fast-disk`, `--cpu-vae`, `--lowvram/--novram`, réserve VRAM et options de cache. Le processus utilise le démarrage Desktop standard, sans `--disable-dynamic-vram`; modèle manuel non imposé. L'offload CPU/asynchrone peut réduire la VRAM mais augmente les transferts PCIe et sollicite la RAM; ce n'est pas un gain gratuit.
- `object_info` (968 types de nœuds) confirme `VAEDecodeTiled` disponible, avec `tile_size`, `overlap`, `temporal_size`, `temporal_overlap`. Il peut baisser le pic VAE spatial/temporel, mais ne réduit pas les poids Transformer ni le coût dominant du sampler; risque de coutures possible. Pas testé ici : le workflow a conservé `VAEDecode` standard.
- Block swap : l'unique `wanBlockSwap` dans `object_info` est explicitement marqué **deprecated no-op** (« intercept ... unstable and make it no-op »), il ne swap donc pas les blocs. Le nœud d'extension `WanVideoBlockSwap` n'est pas installé. Ne pas confondre le no-op avec une optimisation valide; vérifier maintenance/compatibilité et autorisation avant d'installer un custom node. Le catalogue a des nœuds `LTXVAddLatentGuide`, mais compatibilité du modèle LTX-2.3 local non prouvée.
- Quantification FP8/INT8/GGUF peut réduire les poids/VRAM au prix potentiel de fidélité ou compatibilité. Le checkpoint LTX-2.3 FP8 installé pèse ~27,14 Go; la RAM libre mesurée (~14,78 GiB) est inférieure à sa taille. Un chargement entier en RAM CPU n'est pas prudent; mmap/block-swap ne sont pas validés et peuvent ralentir fortement.
- La distillation en 8 steps n'amoindrit pas la taille des poids : le LTX-2.3 distilled reste un modèle 22B; potentiellement moins de calcul, pas un « modèle 2B ».

### Modèles et licences
| Modèle | Statut local | Profil RTX 3060 12 Gio | Licence à contrôler |
|---|---|---|---|
| Wan 2.1 Fun Camera 1.3B bf16 | Installé; I2V testé | Seul chemin vidéo prouvé sans nouveau modèle; ~7 min/3 s; ~8 GiB observés partiellement; cadrage/mouvement à améliorer | La fiche du checkpoint Fun Camera cite Apache-2.0; vérifier chaque fichier associé et usage visé |
| LTX-2.3 22B dev FP8 | Checkpoint local ~27,14 Go; pas de rendu V2-J | Potentiel qualité/polyvalence mais poids trop grands pour 12 Gio; workflow natif LTX-2.3, offload et vitesse non validés, RAM libre < taille fichier | LTX-2 Community License : entités ≥10 M$ de revenus annuels doivent obtenir une licence commerciale payante; examiner les restrictions d'usage |
| LTX-2.3 22B distilled / distilled 1.1 | Non inventoriés localement | 8 steps réduisent le calcul, pas l'empreinte mémoire 22B; offload requis | Même licence LTX-2 |
| LTX-Video v0.9.8 2B distilled (FP8 possible) | Absent localement | Candidat léger plausible pour 12 Gio, compromis qualité possible; workflow, poids et performance à vérifier avant toute acquisition | Ancienne Open Weights License 0.X; pas Apache, lire les termes de la version exacte |
| Wan 2.2 TI2V 5B / LTX-Video 2B 0.9.5 | Absents; aucun téléchargement | Candidats de comparaison ultérieure seulement | Vérifier la licence du checkpoint exact avant usage commercial |

Wan 1.3B est la seule option vidéo qualifiée sur ce poste. LTX-Video 2B distilled pourrait être un compromis pertinent, mais modèle, poids, workflow et licence locale restent à vérifier; aucun téléchargement n'a été fait. Pour usage commercial, examiner séparément checkpoint, encodeur, VAE, LoRA et droits de redistribution.

### Validation et état final
- `tests/test_video_longform.py` : plan 3/5 s et calcul 30 s, reprise par hashes, workflow strict, manifeste atomique, mesure VRAM. Tests ciblés `test_video_longform.py`, `test_video_v2h.py`, `test_comfy_v1d.py` : **54 réussis**; suite backend complète : **509 réussis**; compilation Python réussie. Deux avertissements Starlette/httpx préexistants et avertissements de configuration pytest-asyncio; aucun échec.
- Sources officielles consultées : [ComfyUI CLI flags/offload/dynamic VRAM](https://docs.comfy.org/development/comfyui-server/startup-flags); [fiche Wan 2.1 Fun Camera et licence Apache-2.0](https://huggingface.co/alibaba-pai/Wan2.1-Fun-V1.1-1.3B-Control-Camera); [LTX-2.3 model card](https://huggingface.co/Lightricks/LTX-2.3) et [licence LTX-2 (version datée)](https://huggingface.co/Lightricks/LTX-2.3/blob/3c6a4e66e5d0a684231950b9c74dd4ded7b6fadc/LICENSE); [repo officiel LTX-Video/distilled 2B](https://github.com/Lightricks/ltx-video); [LTX-Video Open Weights License 0.X](https://huggingface.co/Lightricks/LTX-Video-0.9.8-13B-distilled/blob/main/LTX-Video-Open-Weights-License-0.X.txt).
- Run local ignoré Git : `backend/bench_runs/v2j/continuity_two_segment_20261110/index.html`; ComfyUI actif, file vide après le test. Aucun autre changement à l'installation.
- Fin V2-J : **arrêt après prototype 6 s**. Ne pas télécharger de poids, activer LongForm dans l'UI ni promettre 30 s avant validation multi-seed du cadrage/mouvement.

## V2-K — Contrôle de continuité vidéo, prototype deux segments

### Modifications ciblées
- `backend/lib/video_longform.py` garde le mode historique `legacy` par défaut et ajoute des modes expérimentaux `neutral`, `bounded` et `keyframe`.
- `bounded` choisit une correction latérale à la frontière de segment depuis la position mesurée du sujet; dans les modes `bounded` et `keyframe`, l'image initiale reste la référence CLIP Vision, tandis que l'image finale précédente demeure l'image de départ I2V.
- Garde-fou de cadrage local : déduit une teinte dominante dans une ROI normalisée opérateur, suit les pixels chromatiques correspondants sur l'image de fin, enregistre boîte/risque et refuse le segment suivant si le sujet n'est plus détectable ou approche du bord. **C'est un détecteur chromatique expérimental, pas de la détection sémantique; les sujets achromatiques/multicolores ou les reflets peuvent demander une ROI adaptée ou désactiver explicitement le garde.**
- `ModelAttentionBackend` de Comfy Kitchen est désormais disponible comme option CLI explicite et enregistrée dans l'empreinte du run. PyTorch reste le défaut; aucun moteur par défaut n'a été changé.
- Prévalidation auprès de l'API ComfyUI des checkpoints, poses caméra et backends attention effectivement exposés. Les données et sorties restent dans `backend/bench_runs/` (ignoré par Git).

### Contrôle sur l'ancien rendu V2-J (sans GPU)
- Extraction/détection sur toutes les **144 images** de la vidéo V2-J; 144/144 observations de l'ancre bleue obtenues. Centre horizontal du flacon : x=0,510 au départ, 0,805 à la frontière (frame 72), 0,940 en fin; premier contact du masque avec le bord à la frame 78. La politique bornée aurait donc choisi `Pan Right` à la frontière, avant la sortie observée.
- Les trois stratégies sont exposées et testées au niveau de la construction/politique : `neutral` = `Static`; `bounded` = correction de dérive; `keyframe` = poses explicites par segment et référence initiale persistante. Faute de coût raisonnable pour plusieurs campagnes à ~7 min par segment, seules la trajectoire bornée et la référence persistante ont été rendues ensemble; neutral et keyframe n'ont pas reçu de rendu visuel indépendant. Ne pas interpréter cela comme un A/B visuel des trois stratégies.

### Un rendu GPU contrôlé (2 × 3 s)
- Même source/hachage, prompt, seeds (753934134/135), 832×480, 24 fps, 73 frames/segment, 20 steps, CFG 6, sampler `uni_pc`, scheduler `simple`; attention PyTorch, sans Ollama chargé. Le segment 1 reçoit `Pan Left`; le contrôleur observe x=0,805 à sa fin et choisit `Pan Right` pour le segment 2. Les deux segments utilisent la même image initiale persistante comme référence CLIP Vision; le second démarre de l'image de fin du premier.
- Sortie locale : `backend/bench_runs/v2k/bounded_keyframe_20261110/` (galerie `index.html`, MP4 assemblé et manifeste). H.264, **144 frames = 6,000 s**, 832×480 à 24 fps. File ComfyUI vide après le test.
- Temps ComfyUI : segment 1 **428,752 s**, segment 2 **430,375 s**, total **859,127 s (~14 min 19 s)**. Segment 2 : échantillonnage observé 399,968 s, setup au premier pas 11,375 s, SaveVideo 1,344 s. Le client de collecte du segment 1 a été interrompu après soumission; le job ComfyUI a fini sans être relancé, puis ses sorties ont été récupérées via l'historique Comfy et le run repris pour le segment 2. Sa VRAM n'a donc qu'une mesure externe partielle.
- VRAM globale NVIDIA observée : segment 1 **7 973 MiB** (échantillonnage externe commencé ~30 s après soumission, donc pas pic absolu garanti); segment 2 **8 544 MiB / 12 288 MiB** avec le collecteur du prototype. Occupation GPU observée jusqu'à 100 %. Le segment 2 a observé 19 234 MiB RAM système utilisés au pic, sur 32 665 MiB.
- Référence V2-J : 426,750 + 424,453 = 851,203 s. Le nouveau run est ~7,9 s (0,9 %) plus lent, différence trop faible pour conclure; l'objectif était le cadrage, pas le débit.

### Résultat visuel mesuré et limites
- Analyse couleur des 144 frames du nouveau MP4 : 144/144 détectées; centre x=0,510 au départ, 0,805 à la frontière puis 0,567 en fin; aucune boîte détectée ne touche le bord. Le flacon repart vers le centre avec Pan Right; déplacement par frame reste progressif (maximum observé du centroïde ~0,005 largeur de frame). MAE RGB au raccord 5,295/255 contre moyenne intra-segment 4,670/255 : valeurs descriptives seulement, pas un score perceptuel.
- À l'examen de la vidéo entière et de la planche-contact, silhouette bleu cobalt, décor et cap restent cohérents; pas de sortie de cadre dans ce run. Le cap est attaché à la bouteille dans l'image source et le texte d'étiquette reste illisible. Une seed et un sujet ne démontrent pas la robustesse générale.
- Le garde-fou ne surveille les transitions de segment qu'au moment où l'image de fin est disponible; il ne coupe pas un segment en cours. La détection par couleur ne convient pas à tous les sujets et ne prouve pas la stabilité d'identité sémantique.
- ComfyUI local expose bien les options `pytorch attention` et `comfy kitchen attention`; le graphe opt-in `ModelAttentionBackend` est testé structurellement, mais **aucun rendu V2-K avec INT8 n'a été effectué**. Pas de gain de performance revendiqué. PyTorch reste inchangé par défaut.

### Validation V2-K
- `tests/test_video_longform.py`, `test_video_v2h.py`, `test_comfy_v1d.py`: **60 réussis**; compilation Python et `git diff --check` réussis. Aucune suite backend complète relancée.
- Aucun téléchargement, changement de modèle, installation, route de production ou workflow par défaut. Pas de génération 30 s.
- Artefacts/vidéos locaux ignorés par Git : `backend/bench_runs/v2k/bounded_keyframe_20261110/`. Le commit contient uniquement le prototype, ses tests et ce suivi.
- Prochaine étape recommandée : campagnes courtes contrôlées et distinctes `Static`, trajectoire bornée et keyframes sur au moins plusieurs seeds, puis sujets à hue différente; décider si un détecteur vision local plus générique est justifié avant de rendre LongForm accessible dans l'interface.

Fin de V2-K : arrêter ici; ne pas étendre à 30 s et ne pas activer Comfy Kitchen par défaut.

## V2-L — Extension LongForm à 9 puis 12 secondes

### Implémentation ciblée
- `backend/lib/video_longform.py` accepte maintenant `--target-seconds 6|9|12` (défaut inchangé à 6 s), planifie 2/3/4 segments Wan de 73 images, suit les graines successives et assemble dynamiquement tous les segments.
- Reprise/extension sûre : un run terminé peut passer de 9 à 12 s uniquement si les paramètres de génération hors durée sont identiques et si les vidéos/images de fin de tous les segments précédents passent la vérification SHA-256. La reprise ajoute le segment manquant, sans recalculer les anciens. Un changement de prompt, image, caméra, seed, modèle ou réglages est refusé.
- `backend/scripts/longform_assemble_av.py` assemble N segments, vérifie le nombre d'images exact et enregistre chaque raccord dans l'ordre. Le contact sheet couvre toutes les frames/segments; les écarts RGB sont descriptifs, pas des scores perceptuels.
- Aucun changement aux routes, workflows ou presets de production, au modèle, au backend d'attention, ni aux paramètres Wan. PyTorch reste utilisé. Aucun téléchargement.

### Rendus réels et ressources
- ComfyUI existant, Wan 2.1 Fun Camera I2V, RTX 3060 12 Gio, 832×480, 24 fps, 73 frames par segment, 20 steps, CFG 6, `uni_pc`/`simple`, graines 753934134–137. La source est l'image SDXL existante; le prompt demande de conserver le bouchon attaché comme dans l'image (contrairement au prompt historique contradictoire). Ollama n'avait aucun modèle chargé; aucune file ComfyUI concurrente.
- **9 s** : 3 segments, sortie H.264 `longform-9s.mp4`, exactement 216 frames / 9,000 s. Temps ComfyUI : **450,323 + 1 124,562 + 606,688 = 2 181,573 s (~36 min 22 s)**. Segment 2 a pris 1 067,609 s d'échantillonnage observé; le pic système mesuré était **11 517 / 12 288 MiB VRAM** et **31 067 / 32 665 MiB RAM** (RAM disponible minimale 1 598 MiB).
- **Extension à 12 s** : la reprise a validé les trois segments existants et n'a rendu que le segment 4 (seed 753934137, pose Static), **429,188 s**. Sortie H.264 `longform-12s.mp4`, exactement 288 frames / 12,000 s. Temps cumulé des quatre segments **2 610,761 s (~43 min 31 s)**. Segment 4 : pic 10 042 MiB VRAM, pic RAM 19 353 MiB; le maximum observé sur l'ensemble du run demeure celui du segment 2. Le premier segment a été récupéré de l'historique ComfyUI après interruption du client; son temps de 450,323 s est confirmé, mais son pic VRAM/RAM n'a pas été collecté de bout en bout.
- Rapport d'assemblage 12 s : 73 frames par source, 3 images partagées supprimées, 288 frames finales, 832×480, 24 fps; mesures des raccords RGB MAE : **4,530 / 1,696 / 1,566** (échelle 0–255). Ces valeurs sont descriptives uniquement.

### Vérification de l'ensemble des images et qualité observée
- Les **216 frames** du rendu 9 s puis les **288 frames** de la sortie 12 s ont été décodées. L'ancre chromatique bleue du flacon est retrouvée dans **216/216** et **288/288** frames respectivement (contrôle couleur, non sémantique).
- Sur 12 s, le centre suivi varie de x=0,413 à 0,800; début x=0,510, fin x=0,558. Le flacon reste entièrement à l'intérieur des zones sûres détectées. Les poses consignées sont `Pan Left` → correction `Pan Right` → `Static` → `Static`; les transitions de centre adjacentes aux trois raccords sont environ 0,004, 0,004 et 0,000 largeur de frame. L'image de référence initiale reste utilisée pour CLIP Vision et l'image de fin du segment précédent amorce chaque nouveau segment.
- Examen visuel du contact sheet complet : bouteille bleu cobalt, bouchon attaché, marbre et éclairage restent globalement cohérents. Le mouvement est modéré : correction de panoramique puis cadrage presque statique pendant les deux derniers segments. L'étiquette reste illisible; légères variations de reflets/textures restent visibles. Ce cas unique ne valide ni toutes les scènes ni une qualité commerciale constante.
- L'extension à 12 s est jugée acceptable pour vérifier la continuité et le cadrage sur cette référence, pas comme démonstration d'un mouvement cinématographique professionnel.

### Validation, limites et artefacts
- Tests ciblés `tests/test_video_longform.py` + `tests/test_video_v2h.py` : **31 réussis**. Compilation Python, `git diff --check` et assemblage smoke de trois clips existants en 9,000 s (216 frames, 2 métriques de raccord) réussis. Suite backend complète non relancée.
- Les temps varient fortement entre segments; le segment 2 a approché la limite RAM et VRAM. À la moyenne de 12 s, une extrapolation linéaire vers 30 s serait d'environ **109 minutes**, mais cette projection est incertaine et la pression mémoire peut causer ralentissements/échec. **Aucune génération 30 s n'a été lancée ni validée.**
- Les créations sont locales, ignorées par Git : `backend/bench_runs/v2l/longform_9s_20261110/` contient les deux MP4, manifeste de reprise, mesures, rapport et galerie `index.html`; `continuity-contact.jpg` montre les 288 frames échantillonnées. Aucun ancien média, modèle, installation ou base utilisateur n'a été modifié.
- Recommandation : avant tout palier supérieur, améliorer/valider le mouvement continu (Pan Left suivi de Pan Right corrige le cadre mais inverse le mouvement à un raccord) et surveiller l'utilisation RAM; effectuer ensuite plusieurs seeds/sujets. Ne pas promettre 30 s sur la base d'un seul run.

Fin de V2-L : arrêter ici; ne pas commencer V2-M.


## V2-M — SmartMotion 2.5D et moteur hybride expérimental

### Prototype fonctionnel
- Ajout de `backend/lib/smartmotion.py`, indépendant des routes et workflows actifs, et `tests/test_smartmotion.py`. Le CLI utilise exclusivement un snapshot local complet de Depth Anything V2 Small (`local_files_only=True`, mode offline forcé); il refuse de continuer si le poids ou sa configuration manque, sans aucun téléchargement.
- Le système calcule une profondeur relative par pixel, puis anime une image par reprojection CUDA avec une courbe caméra bornée (push-in 7 %, petit arc latéral/vertical). PyAV encode en `h264_nvenc` (preset p5, VBR/CQ 19). La sortie est redécodée pour vérifier toutes les frames; une galerie `index.html`, carte de profondeur et manifeste JSON sont conservés.
- Le routeur expérimental `recommend_mode` distingue SmartMotion (image fixe + mouvement de caméra), FastVideo (seulement si un modèle léger a été explicitement vérifié disponible) et Cinematic (mouvement/contenu génératif). Il s'agit d'une recommandation non intégrée à l'UI ni aux routes de production. Aucun modèle vidéo léger dédié n'a été trouvé; Wan Fun Camera reste lent, et LTX-2.3 22B est trop volumineux pour devenir un mode rapide sur ce poste.
- SmartMotion ne fait pas de segmentation sémantique, n'anime pas séparément le flacon ou une personne, et ne recrée pas les surfaces cachées. Le champ de profondeur produit un effet de pseudo-couches; une marge de zoom évite ici les grands bords découverts, avec padding miroir en recours. Ce mode n'est donc pas un substitut à la vidéo générative.

### Environnement vérifié (sans installation ni téléchargement)
- RTX 3060 12 Gio; mémoire système ComfyUI reportée : 34 252 099 584 octets (~31,9 Gio), environ 14,25 Gio libres au contrôle initial.
- ComfyUI 0.37.2 actif sur loopback. Checkpoints annoncés par son API : Wan Fun Camera 1.3B et checkpoints FLUX Schnell, LTX-2.3 22B, SDXL. Aucun autre générateur vidéo léger n'est présent.
- Le cache Hugging Face local contient Depth Anything V2 Small : `model.safetensors`, 99 173 660 octets (~94,5 Mio), SHA-256 `3152477c…249a16b70`. Transformers, PyTorch CUDA, Pillow, NumPy et PyAV 18.1.0 étaient déjà présents dans le venv ComfyUI; OpenCV et Blender ne sont pas installés. PyAV a ouvert et utilisé le codec `h264_nvenc` sur cette RTX.
- Source Depth Anything V2 Small annoncée sous Apache-2.0 par le dépôt officiel; les variantes Base/Large/Giant sont CC-BY-NC-4.0 et ne sont pas retenues pour une distribution commerciale. Aucun modèle n'a été modifié.

### Rendu réel de 5 secondes
- Entrée : image produit SDXL locale `backend/bench_runs/app_flow/349182bf-8fa3-4598-ae62-27865428ea89.png` (1024×1024). Sortie : `backend/bench_runs/v2m/smartmotion_product_5s_measured/smartmotion.mp4`; galerie : `index.html`; mesures : `manifest.json`, `visual_checks.json`, `depth-relative.png`, `contact-sheet.jpg`. Résolution source 1024×1024, H.264/NVENC, 24 fps, 120 frames, exactement 5,000 s.
- Temps mesurés : chargement du modèle 0,365 s; inférence profondeur 0,426 s; reprojection + encodage 1,426 s (84,151 fps de calcul/encodage); validation/décodage de sortie 0,270 s; temps mur total du processus 9,129 s (inclut démarrage/interprétation/imports). Aucune diffusion vidéo n'est exécutée.
- VRAM globale : baseline 3 449 MiB, pic échantillonné 3 661/12 288 MiB (+212 MiB); pic d'allocation PyTorch du calcul de profondeur 209 MiB. RAM système : 19 643 MiB utilisée en baseline, pic échantillonné 19 835/32 665 MiB (~12 830 MiB restants). Mesures globales échantillonnées (pas isolées par processus; les pointes très brèves peuvent être manquées); ComfyUI restait actif.
- Vérification vidéo exhaustive : 120/120 frames décodées. Un masque simple de pixels cobalt détecte le sujet dans les 120 frames; son centroïde horizontal varie de x=0,499 à 0,514 (plage 0,498–0,514), et la largeur détectée croît de 0,319 à 0,339 de l'image avec le push-in. Il s'agit d'un test couleur, pas de suivi sémantique/optical flow.
- Examen visuel de la planche complète : le mouvement dolly/arc est fluide, le produit reste cadré et ses couleurs/décor sont conservés. Des déformations légères du contour en verre et du texte/étiquette sont visibles avec la reprojection de profondeur; les détails existants restent illisibles. Il n'y a aucun mouvement réel du bouchon, du liquide, de la lumière ou d'un personnage. Résultat utile pour une publicité produit subtile, pas encore une animation 3D ou une vidéo professionnelle générale.

### Projection et choix des modes
- Extrapolation strictement indicative à résolution identique 1024×1024 : 720 images (30 s à 24 fps) ÷ 84,151 fps ≈ 8,56 s pour la reprojection/encodage. En conservant les coûts fixes observés (démarrage/imports et estimation de profondeur) et en extrapolant le décodage de vérification, le temps de processus serait de l'ordre de 18 s. **Aucun rendu de 30 s n'a été lancé**; la résolution 1080p n'a pas été testée ni n'est proposée par ce prototype. Cette projection ne valide donc pas l'objectif « 30 s, 1080p ».
- SmartMotion peut rendre un long plan caméra-only nettement plus rapidement que le sampler Wan parce qu'il transforme une image existante; le compromis est explicite : aucun mouvement d'objet, aucune génération de nouveaux détails ou de géométrie. Le mode Cinematic renvoie conceptuellement vers le pipeline génératif existant, sans changement. FastVideo reste indisponible jusqu'à validation d'un checkpoint et d'un workflow légers.
- Piste FastVideo : LTX-Video 2B distilled (les cartes officielles 0.9.6 le décrivent comme orienté faible VRAM/rapide); aucune vitesse ni compatibilité RTX 3060 n'est démontrée ici. Vérifier la licence propre au checkpoint avant commercialisation. Les poids LTX-2.3 22B FP8 déjà présents ne sont pas un candidat rapide adapté aux 12 Gio.
- Depth Anything V2 Small : licence de dépôt Apache-2.0; OpenCV (Apache-2.0) pourrait apporter optique-flow/inpainting si installé ultérieurement, mais ne résout pas à lui seul les surfaces invisibles. Blender est GPL, gratuit pour usage commercial, et l'œuvre produite appartient à son auteur; distribution d'un Blender modifié ou de scripts bpy exige une analyse de conformité GPL. Blender n'est pas installé et n'a pas été utilisé. NVENC est effectivement actif; il accélère seulement l'encodage, pas les moteurs de diffusion.
- La carte officielle annonce `ltxv-2b-0.9.6-distilled` comme modèle 2B léger/distillé (revendication fournisseur « 15× faster », pas une mesure RTX 3060). Sa licence modèle versionnée est royalty-free sous restrictions d'usage; les entités à au moins 10 M$ de revenus annuels peuvent devoir obtenir une licence commerciale payante. Ce candidat mérite un test après autorisation, sans préjuger de sa compatibilité/vitesse sur 12 Gio. Références : [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2), [LTX-Video model card](https://huggingface.co/Lightricks/LTX-Video), [licence LTX-Video 2B distilled 0.9.6](https://huggingface.co/Lightricks/LTX-Video/blob/2f2df7f6d769fc11386dca330b03688bbfb1c508/ltxv-2b-0.9.6-distilled-04-25.license.txt), [licence Blender](https://www.blender.org/about/license/), [licence OpenCV](https://github.com/opencv/opencv/blob/4.x/LICENSE), [NVIDIA Video Codec SDK](https://developer.nvidia.com/video-codec-sdk).

### Validation, limites et livraison
- `tests/test_smartmotion.py` et tests vidéo ciblés : **34 réussis**. Un test préexistant de suivi couleur a été exclu de cette commande car le venv backend Python 3.11 n'a pas Pillow; les autres tests passent, et le rendu de production a été effectué avec Pillow déjà disponible dans le venv ComfyUI Python 3.13. `py_compile` et `git diff --check` réussis.
- Aucun téléchargement, changement de modèle, workflow/paramètre par défaut, installation existante, base de données, route ou interface de production. Les deux sorties expérimentales restent locales et ignorées par Git.
- Commande reproductible depuis `backend/` avec l'interpréteur ComfyUI existant : `& "$env:LOCALAPPDATA\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe" -m lib.smartmotion --input bench_runs/app_flow/349182bf-8fa3-4598-ae62-27865428ea89.png --output-dir bench_runs/v2m/my_smartmotion_5s --seconds 5 --fps 24` (le modèle est trouvé dans le cache local; sinon arrêt sans téléchargement).
- Fin V2-M : prototype SmartMotion 5 s démontré; pas d'intégration UI, de FastVideo valide, de génération dynamique d'objets, ni de validation réelle 30 s/1080p. Prochaine validation appropriée : mesurer un 30 s à la définition source en V2-N, puis tester une vraie sortie 1080p et des scènes plus difficiles avant de revendiquer l'objectif commercial.


## V2-N — Validation SmartMotion 30 s / 1080p

### Correctifs ciblés
- `backend/lib/smartmotion.py` accepte maintenant une taille explicite `WIDTHxHEIGHT`. Le redimensionnement est refusé implicitement comme comportement par défaut : sans option, le rendu garde la résolution native.
- Si le ratio cible diffère, le prototype applique un recadrage central sans étirement, puis indique explicitement dans `manifest.json` le rectangle source, la résolution source/sortie et tout upscale. Pour la photo carrée 1024x1024, le mode 1920x1080 utilise le crop `(0,224,1024,800)` (1024x576), puis un upscale Lanczos 1,875x; ce n'est pas un détail natif 1080p.
- La revue vidéo décode toutes les frames, compte les répétitions exactes adjacentes, mesure la différence pixel moyenne adjacente et génère une planche à une image/seconde. Le chronomètre de profondeur synchronise CUDA avant d'arrêter la mesure afin d'inclure les opérations GPU asynchrones.
- Tests de parsing/limites de sortie et de calcul de crop ajouté; paramètres caméra et NVENC inchangés.

### Deux rendus réels sur RTX 3060 12 Go
Entrée commune : photo SDXL locale `app_flow/349182bf-8fa3-4598-ae62-27865428ea89.png` (1024x1024), Depth Anything V2 Small déjà en cache local. Génération camera-only SmartMotion, H.264 `h264_nvenc` preset p5/VBR/CQ19, 24 fps. Le GPU ComfyUI était actif mais sa file était vide; mesures nvidia-smi et RAM sont globales système, pas isolées du processus.

| Sortie | Images/durée vérifiées | Durée murale SmartMotion | Rendu + encodage | Décodage/revue complète | VRAM globale pic observé | RAM système pic observé |
|---|---:|---:|---:|---:|---:|---:|
| Native 1024x1024 | 720 / 30,000 s | **30,566 s** | 7,921 s | 14,850 s | 3 644 / 12 288 MiB | 19 959 / 32 665 MiB |
| 1920x1080 | 720 / 30,000 s | **44,276 s** | 12,473 s | 24,361 s | 3 812 / 12 288 MiB | 20 043 / 32 665 MiB |

Le temps mur inclut chargement des bibliothèques appelé dans `render`, chargement/inférence de profondeur (respectivement ~0,35/0,42 s; 0,35/0,43 s), rendu, encodage, décodage de vérification et génération de galerie/mesures. Il démarre à l'entrée de `render()` et n'inclut pas le lancement initial de l'interpréteur Python avant l'appel. L'objectif <60 s est donc atteint par la chaîne de rendu mesurée dans les deux modes; la marge 1080p est ~15,7 s. Ces temps ne sont pas une garantie sur d'autres PC ou sous contention GPU.

- Les deux fichiers sont réellement 24 fps H.264 NVENC, durée 30 s. Les 720 frames de chaque fichier ont été décodées, aucune paire consécutive n'est identique; les planches couvrent 0–29 s à pas d'une seconde.
- MAE moyenne entre frames adjacentes : 0,126/255 en 1024 et 0,162/255 en 1080; c'est un indicateur de variation, pas un score perceptuel.
- Un masque cobalt heuristique retrouve une zone produit dans 720/720 frames. Son centroïde horizontal normalisé varie de 0,5034–0,5200 (1024) et 0,5089–0,5235 (1080). Le frame 0 décodé reste proche du crop/upscale de référence (MAE 1,46/255 et 1,42/255); l'écart au frame final (16,80/255 et 18,11/255) est cohérent avec le mouvement/zoom et la compression, pas une mesure de fidélité sémantique.

### Créations locales (ignorées par Git)
- 1024 natif : `backend/bench_runs/v2n/smartmotion_30s_1024/smartmotion.mp4`; galerie `index.html`; planche `contact-sheet.jpg`; mesures `manifest.json`, `visual_metrics.json`, `quality_analysis.json`.
- 1080 : `backend/bench_runs/v2n/smartmotion_30s_1080p/smartmotion.mp4`; mêmes fichiers d'inspection.
- La planche échantillonne une frame par seconde; le manifeste confirme aussi la lecture complète des 720 images. Les MP4 restent locaux et ne sont pas versionnés.

### Qualité et limites (examen de l'ensemble)
- Le produit bleu, les proportions principales, les couleurs et le décor restent visuellement cohérents sur les 30 s. Le mouvement est fluide, borné et sans répétition adjacente; il s'agit d'un lent push-in 7 % avec un arc latéral très léger, et non de mouvements complexes ou variés au sens cinématographique. Il peut paraître presque statique à un spectateur.
- La sortie 1080 respecte le ratio par crop (aucun étirement), mais retire les bandes haute/basse de la source carrée puis agrandit 1,875x. La bouteille reste visible sur la planche; le rendu n'ajoute aucun détail au-delà de l'image SDXL et son texte illisible reste illisible.
- Les déformations légères des bords de verre/étiquette, reflets, zone de profondeur et pixels de bord réfléchis héritent de la reprojection 2.5D; l'upscale ne les corrige pas. Aucun masque sémantique, optical-flow, nouvelle géométrie ou mouvement d'objet n'est généré. Ce n'est pas une vidéo générative et le résultat n'est pas équivalent à une animation commerciale tournée/rendue en 3D.
- Les métriques de mouvement sont descriptives, et le masque cobalt est heuristique. Aucun jugement humain aveugle ni métrique perceptuelle n'a été réalisé. La qualité n'est validée que pour cette image produit.

### Tests et livraison
- `tests/test_smartmotion.py` : **6 réussis**; compile Python ComfyUI et `git diff --check` vérifiés.
- Aucun modèle ou paquet téléchargé, aucune configuration d'installation, base utilisateur, workflow de production ou modèle existant modifié. Les deux vidéos et les analyses restent ignorées par Git.
- Fin V2-N : un vrai MP4 30 s/24 fps a été validé à la résolution source (1024x1024) et un second à 1920x1080, chacun sous 60 s dans cette session. L'objectif concerne exclusivement SmartMotion camera-only sur cette image; il ne signifie pas 30 s de vidéo générative, une qualité native 1080p, ni une promesse générale de qualité professionnelle.

## V2-O — mémoire, moteur vidéo et intégration SmartMotion (réalisé, portée qualifiée)

### Mission 1 — ressources mémoire gratuites : inventaire vérifié

Mesures de cette machine pendant V2-O : RAM physique Windows 31,90 Gio, dont 13,51 Gio disponibles au relevé; fichier d'échange `C:\pagefile.sys` de 4 337 Mio réservé, usage courant 75 Mio. ComfyUI 0.37.2 expose une RTX 3060 avec 12 288 Mio VRAM; un relevé ComfyUI à file vide indiquait 10 853 Mio libres. Ce sont des mesures à différents instants, non une garantie de disponibilité simultanée. Dans les deux rendus V2-O, les pics échantillonnés globaux étaient 3 714/12 288 et 3 701/12 288 Mio VRAM, et 20 140/32 665 et 20 148/32 665 Mio de RAM utilisée. L'échantillonnage est système et peut manquer des pointes; il ne mesure pas l'allocation propre au backend.

- RAM physique = mémoire réelle partagée par Windows et les programmes. Le pagefile SSD est de la mémoire virtuelle de secours : il permet de dépasser le commit physique au prix d'accès disque bien plus lents; il n'augmente ni la RAM physique ni la VRAM et ne rend pas viable un modèle qui manque de mémoire GPU.
- VRAM = mémoire locale de la carte graphique; seule une meilleure efficacité/offload de l'application ou une autre carte change la capacité GPU directement accessible. SmartMotion infère la profondeur sur CUDA puis libère explicitement le modèle avant de rendre/encoder les frames; le modèle Depth Anything V2 Small alloue ~209 Mio CUDA au pic observé sur la scène produit 1024². Cela évite de garder ses poids pendant le rendu, mais ne crée pas de mémoire.
- Mémoire distante / calcul déporté gratuit : aucun endpoint gratuit, sans carte bancaire et fiable n'a été intégré ou utilisé. Un PC personnel supplémentaire peut traiter une tâche distribuée si le logiciel et le réseau sont configurés, mais cela fournit une ressource distante, pas de la VRAM locale; réseau, sécurité, disponibilité et orchestration sont à la charge de l'utilisateur. Aucune machine secondaire n'a été supposée.
- Quantification : aucune conversion ni installation faite. Le moteur Comfy Kitchen INT8 testé précédemment avait accéléré un test vidéo V2-I (résultat indicatif, seed non comparable) mais n'a pas été qualifié comme réduction mémoire de SmartMotion et reste désactivé par défaut. La profondeur reste en précision standard. Aucun changement de pagefile n'a été appliqué.
- Conclusion utile et gratuite appliquée : réutiliser le runtime ComfyUI/PyTorch et le modèle Depth Anything déjà installés, lancer hors ligne, vérifier CUDA/local files avant d'accepter une tâche, libérer le modèle de profondeur avant le rendu. Aucun paquet ou poids téléchargé. Le détecteur runtime confirme réellement PyTorch CUDA + Transformers + PyAV + Pillow; sinon l'API refuse explicitement SmartMotion en 503.

### Mission 2 — capacités 2026 et améliorations effectivement livrées

Sources consultées le 2026-11-10 : VBench (qualité image, cohérence sujet/arrière-plan, scintillement, fluidité, sémantique) et VBench-2.0 (fidélité intrinsèque/physique); ces suites évaluent de la vidéo générée et ne permettent pas d'assimiler un déplacement caméra 2.5D à un modèle génératif. SmartMotion ne prétend donc pas rivaliser avec les meilleurs générateurs 2026.

- SmartMotion conserve Depth Anything V2 Small déjà en cache, avec inférence locale hors ligne. Il propose maintenant 7 trajectoires image-space bornées (push-in, pan G/D, tilt haut/bas, arc subtil pseudo-3D, fixe); ce ne sont ni des poses 3D résolues ni un suivi sémantique. Les détails/couleurs de la source restent visibles parce que l'image est reprojetée, mais le texte illisible de la source reste illisible.
- Le masque d'objet précis, segmentation vidéo, correction sémantique de déformations et inpainting des régions révélées ne sont pas implémentés. Aucun poids SAM/SAM2 ou nouveau modèle n'a été téléchargé; aucune reconstruction ne peut être affirmée. Le padding miroir existant peut montrer des bords réfléchis. Intégrer une segmentation généralisable et une reconstruction temporelle fiable nécessite un modèle + validation plus lourde, absents des ressources installées et hors achat/téléchargement autorisé.
- Mouvement réel : le preset local Wan 2.1 Fun Camera 1.3B (I2V) et son workflow génératif existant restent le chemin ComfyUI distinct; il n'est pas remplacé par SmartMotion et continue à nécessiter ses poids et ComfyUI. SmartMotion ne fait pas marcher des personnages/objets. Aucun nouveau checkpoint téléchargé. Le preset peut échouer si ses dépendances ComfyUI ne sont pas installées.

### Mission 3 — intégration UI/API

- Nouveau choix `SmartMotion · local 2.5D` dans le sélecteur vidéo, indépendant de ComfyUI/Wan et des autres moteurs conservés. API `GET /api/media/models/smartmotion` annonce disponibilité/référence de profondeur; `POST /api/media/smartmotion` accepte une image existante, durée 5/10/15/20/30 s, 24 fps, taille source/720p/1080p et trajectoire caméra. La durée est plafonnée à 30 s, aucune sortie >1080p exposée dans l'UI.
- Tâche intégrée à la file GPU, états running/done/error/cancel, progrès réel toutes les secondes pendant la boucle de rendu, MP4 sauvegardé dans la bibliothèque, lecture/téléchargement via les cartes média existantes. Les métadonnées persistées incluent durée murale, images décodées, trajectoire, résolution et relevés système RAM/VRAM.
- Le message UI avertit explicitement que le prompt n'est pas interprété en mode SmartMotion; la consigne effective se limite au mouvement caméra choisi. Pour demander une action/mouvement d'objet, utiliser l'option générative locale et son modèle vidéo.

### Validation V2-O — deux scènes, reproductible

Deux rendus réels exécutés avec le runtime ComfyUI existant, RTX 3060, NVENC, 24 fps, Depth Anything V2 Small en cache; toutes les frames ont été décodées. Scène 1 : photo produit SDXL (1024²), push-in, sortie native. Scène 2 : paysage géométrique de test créé localement (1024x576), arc subtil, recadrage/agrandissement explicite 1280x720. Ce deuxième test valide une autre composition, mais **n'est pas une photo naturelle**.

| Scène | Sortie | Temps mur total (modèle/profondeur + rendu + vérification) | Rendu/encodage | RAM utilisée pic système | VRAM utilisée pic système | Décodage | MAE adjacente moyenne |
|---|---|---:|---:|---:|---:|---:|---:|
| Produit, push-in | 1024x1024, 5 s, 120 frames | 12,248 s | 1,506 s | 20 140/32 665 Mio | 3 714/12 288 Mio | 120/120, 0 identique | 0,636/255 |
| Paysage synthétique, arc | 1280x720, 5 s, 120 frames | 11,252 s | 1,420 s | 20 148/32 665 Mio | 3 701/12 288 Mio | 120/120, 0 identique | 0,275/255 |

La MAE mesure un changement simple, pas une qualité perceptuelle : la scène synthétique a un mouvement moindre et des formes simples. Examen visuel des cinq frames par seconde : le produit reste centré et le paysage demeure stable, mais l'arc reste subtil; pas de mouvement d'objet. Aucun benchmark perceptuel automatisé complet ni test comparatif à paramètres/scènes égaux avec modèle 2026 exécuté localement; fidélité d'instructions non mesurable puisque le prompt est explicitement ignoré.

Artefacts ignorés par Git : `backend/bench_runs/v2o/product/render/` et `backend/bench_runs/v2o/synthetic_landscape/render/` (MP4, planches, profondeur, manifeste); source synthétique dans `.../synthetic_landscape/source.png`. La vidéo initiale d'essai n'a pas été modifiée.

### Tests et limites

- `backend/tests/test_smartmotion.py` + `test_smartmotion_api.py` : **11 réussis**; `py_compile`, typecheck et `yarn build` réussis. À l'instant du build, le backend répond au statut SmartMotion `available: true` grâce au runtime local détecté. Le parcours complet API+Mongo+UI n'a pas été cliqué en navigateur dans V2-O; la persistance tâche est couverte par tests mockés, et la génération directe du moteur a été réellement exécutée deux fois.
- Limites restantes : segmentation et inpainting absents; profondeur monoculaire relative (pas métrique); pas de vrais mouvements d'objets/acteurs; pas d'interprétation prompt SmartMotion; 1080p issu d'un crop/upscale si l'image source est plus petite; performances variables sous contention; les deux scènes V2-O sont courtes, une seule est une photo; aucune équivalence aux générateurs de pointe démontrée.
- Aucun modèle/paquet téléchargé, aucun abonnement/service payant, aucun changement de configuration Windows/pagefile, aucune autre édition, base ou workflow précédent modifié. Presets antérieurs conservés.
- Sources : https://arxiv.org/abs/2311.17982 (VBench), https://arxiv.org/abs/2503.21755 (VBench-2.0), https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf (modèle de profondeur Apache-2.0 déjà présent).
- Livraison V2-O : 530 tests backend réussis, 24 ciblés SmartMotion/vidéo réussis, `py_compile`, `git diff --check`, TypeScript et `yarn build` réussis (avertissement existant de bundle >500 kB). Deux rendus locaux réels terminés et examinés visuellement. Les MP4/manifests restent ignorés par Git. Code et présent rapport livrés dans le commit V2-O suivant.
