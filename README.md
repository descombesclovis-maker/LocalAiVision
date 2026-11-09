# LocalAiStudio NextGen — branche dédiée

> **ÉTAT : ACCUEIL / TRANSFERT EN ATTENTE.** Cette branche est réservée à **LocalAiStudio NextGen original (avant fusion)**. Le code source NextGen n'a **pas encore été transféré dans cette branche**. Ne pas commencer de modification du moteur tant que l'import n'est pas vérifié.

## Source attendue
Archive de référence : `LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip` (capture NextGen transmise dans ChatGPT, avant fusion).

SHA-256 : `83b002299261f6935eb09165b4cd4fca98ef071251ffd47df34e0202208c9cfa`.

Cette archive n'inclut pas nécessairement les derniers correctifs Claude Code (sous-lots 1.1-a et 1.2). **Avant toute optimisation, importer également ces commits depuis le vrai workspace Claude si disponibles** ; ne pas présumer qu'ils sont présents.

## Arborescence voulue
- `backend/` — FastAPI, routes, moteurs, tests et logique de génération.
- `frontend/` — React/Vite et ressources de l'interface.
- `installer/` — installateurs Windows.
- `docs/localai-nextgen/` — architecture, état du projet, décisions.
- `docs/localaivision-nextgen/` — audits, compatibilité des modèles, mesures et progression.
- `install.ps1`, `start-localaistudio.bat`, `download-models.ps1`, `INSTALLATION.md` — scripts de la version source.

## Règles
1. **Branche unique : `nextgen/claude-code`.** Ne pas écrire sur `main` ni `codex/*`.
2. **NextGen prioritaire, aucune fusion avec l'ancien LocalAiStudio.**
3. Conserver fidèlement les moteurs et paramètres originaux. Ne jamais modifier un checkpoint par défaut sans benchmark.
4. Ne publier ni `.env`, ni clés API, ni jetons, ni modèles (> plusieurs Go), ni données personnelles et créations d'utilisateur.
5. Ne jamais supprimer un modèle ni lancer un téléchargement multi-Go sans confirmation utilisateur.
6. Scripts Windows, API et tests à corriger par petites missions ; commit + compte rendu après chaque lot.
7. Les tests GPU (RTX 3060 12 Go, ComfyUI) **doivent être réalisés sur le PC Windows** ; un audit cloud ne les valide pas.
8. Ne pas présenter comme opérationnelle une fonctionnalité non testée.

## Prochaine action
**Importer intégralement le ZIP source indiqué, sans réécriture, et contrôler qu'il s'agit du bon snapshot.** Voir `docs/localai-nextgen/IMPORT.md`. Ne démarrer ensuite que la mission V1-A de protection des modèles, sur cette branche.
