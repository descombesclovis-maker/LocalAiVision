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
