# LocalAiVision NextGen — journal de progression

**État : NextGen source poussé sur GitHub, aucune optimisation V1-A appliquée.**

## Opérations réalisées
- [x] Branche dédiée `nextgen/claude-original` créée sans modifier `main`.
- [x] Code source NextGen avant fusion importé : `backend`, `frontend`, `installer`, scripts et spécifications.
- [x] Plugin Windows binaire `INetC.dll` importé.
- [x] Contrôle distant de la présence de `backend/server.py`, `frontend/package.json`, `frontend/src/App.tsx`, `install.ps1`.
- [ ] Récupération et vérification éventuelles des correctifs Claude Code 1.1-a, 1.2 et 1.3.
- [ ] Audit V0 ciblé sur **cette branche**, plutôt que l’ancien `main`.
- [ ] V1-A : supprimer la suppression automatique des modèles et empêcher leurs téléchargements sans consentement.
- [ ] Tests réels Windows + RTX 3060 et benchmarks.

## Règles
Ne jamais déclarer les moteurs fonctionnels sans tests locaux ; ne supprimer aucun modèle. L'audit V0 fait précédemment par Manyfold sur `main` est **non applicable** à cette branche. Tout développement doit partir du commit source NextGen et conserver les fonctionnalités existantes.
