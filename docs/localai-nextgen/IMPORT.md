# Import du code NextGen dans la branche unique

## Avant toute modification
- Dépôt : `descombesclovis-maker/LocalAiVision`
- Branche cible : **`nextgen/claude-code`**
- Important : branche de staging actuellement **sans le code NextGen** ; elle est volontairement isolée des anciens fichiers LocalAiVision.
- Le code à importer provient exclusivement de l'archive NextGen **avant fusion**, SHA-256 `83b002299261f6935eb09165b4cd4fca98ef071251ffd47df34e0202208c9cfa`.

## Instructions à Manyfold
1. Recevoir l'archive ZIP envoyée par l'utilisateur (ou avoir accès à une copie fiable déjà extraite dans son workspace).
2. Contrôler l'empreinte SHA-256 puis lister les fichiers. Refuser si archive inattendue.
3. Vérifier l'absence de secrets et de caches lourds ; ne pas publier `.env`, modèles IA, `node_modules/`, `.venv/`, données MongoDB, vidéos ou photos privées.
4. Importer les répertoires `backend/`, `frontend/`, `installer/`, les scripts Windows et la documentation. Préserver les fichiers déjà présents dans `docs/`.
5. Commit clair **`chore(nextgen): import Claude Code source before fusion`** uniquement sur `nextgen/claude-code`, puis **push** sur GitHub.
6. Contrôler l'arborescence distante et la présence du frontend, du backend et du fichier de lancement.
7. Récupérer, si disponibles, les modifications postérieures du vrai workspace Claude Code (notamment authentification 1.1-a et isolation 1.2) sous forme de commits séparés ; ne pas les simuler.
8. Ne pas commencer les optimisations des moteurs au même moment que l'import.

### Vérification minimum
`backend/server.py`, `frontend/package.json`, `frontend/src/App.tsx`, `install.ps1`, `INSTALLATION.md` présents.
