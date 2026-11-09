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

Commit : à venir sur `nextgen/claude-code`.

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

Base : `4124cef` (V1-C). Commit dédié V1-D sur `nextgen/claude-code`.

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

## Prochaine étape recommandée

**V2-A — Compréhension et préparation indépendante des prompts**, uniquement après validation
et push de V1-D : LLM entièrement local optionnel, repli exact sur le prompt original,
STRICT/ÉQUILIBRÉ/CRÉATIF, adaptateurs photo/T2V/I2V/retouche/publicité et comparaison explicite.
Ne pas changer les paramètres ou les workflows ; ne pas activer automatiquement le nouveau moteur
avant validation comparative sur RTX 3060 12 Go.
