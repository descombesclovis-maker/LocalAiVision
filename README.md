# LocalAiStudio NextGen — version Claude Code avant fusion

**Branche unique de travail : `nextgen/claude-original`**

Ce dépôt contient désormais **le code source original NextGen avant fusion**, React/TypeScript + FastAPI, scripts Windows et plugin NSIS. Les fichiers ont été importés depuis l'archive partagée dans ChatGPT, sans remplacer le moteur par celui de LocalAiStudio historique.

## Références principales
- Backend : `backend/server.py`, `backend/lib/`
- Frontend : `frontend/package.json`, `frontend/src/`
- Installation Windows : `install.ps1`, `start-localaistudio.bat`, `installer/`
- Spécifications : `SPEC.md`, `INSTALLATION.md`
- Suivi : `docs/localaivision-nextgen/PROGRESS.md`

## Important : limites de cette archive
La copie source est **antérieure à la fusion**, mais elle n'intègre pas nécessairement les sous-lots **1.1-a, 1.2 et 1.3** exécutés ensuite dans l'environnement Claude Code. Ces corrections devront être récupérées et comparées séparément. La présence de scripts et workflows ne prouve pas une génération fonctionnelle sur Windows RTX 3060.

Ne pas importer le code de `main` ou des branches `codex/studio-*` comme s'il s'agissait de NextGen. Ne pas réutiliser l'audit V0 antérieur, puisqu'il visait `main`.

## Consignes pour Manyfold
1. Basculer explicitement sur `nextgen/claude-original`, vérifier `git status` et l'origine distante.
2. Auditer ce code **sans suppression ni téléchargement de modèles** et sans déploiement cloud.
3. Créer une branche de travail basée sur NextGen pour chaque sous-lot, puis ouvrir une PR vers NextGen (pas vers `main`).
4. Tester les modifications ciblées. Documenter ce qui n'a pas pu être testé sur GPU local Windows.
5. Préserver les modèles, médias, projets, clés utilisateur et configurations.
