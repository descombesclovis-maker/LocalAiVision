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
