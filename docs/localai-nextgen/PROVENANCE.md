# Provenance de LocalAiStudio NextGen

## Snapshot ChatGPT
- Fichier : `LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip`
- SHA-256 **confirmé sur l'archive** : `83b002299261f6935eb09165b4cd4fca98ef071251ffd47df34e0202208c9cfa`
- Source du snapshot : `LocalAiStudio-kit-windows.zip`, SHA-256 `2f86ef2458950912eef5dc0ee5cc267970b8bec0687ab748e4b6d2e4a5af595c`
- Fichiers `.env` et secrets exclus du dépôt.
- La différence entre le SHA-256 d'un ZIP et celui d'une autre archive ne démontre pas une différence des fichiers extraits.

## Import GitHub
- La branche `nextgen/claude-original` contenait déjà le code source des moteurs React/FastAPI.
- Les SHA Git des fichiers clés ont été comparés avec ceux du snapshot : `backend/server.py`, `backend/routers/media.py`, `backend/routers/projects.py`, `backend/lib/comfy.py`, `backend/lib/local_engine.py`, `frontend/src/App.tsx`, `frontend/src/pages/Vision.tsx`, `frontend/vite.config.ts`, `install.ps1` : **identiques**.
- Le code a été repris depuis cette branche donneuse, sans reprendre `main` ni les branches `codex/*`.
- Fichiers Python vides restaurés : `backend/lib/__init__.py`, `backend/models/__init__.py`, `backend/routers/__init__.py`.
- **Manquants par rapport au ZIP source**, à compléter depuis l'original avant une distribution Windows :
  - `frontend/public/apple-touch-icon.png`
  - `frontend/public/favicon-16x16.png`
  - `frontend/public/favicon-32x32.png`
  - `frontend/public/favicon.ico`

## Limitations critiques
1. Ce transfert ne contient pas nécessairement les corrections Claude Code ultérieures (sécurité 1.1-a, 1.2, 1.3).
2. Aucune compilation Windows ni génération GPU réelle effectuée pour valider ce snapshot.
3. Les modèles IA volumineux et créations sont locaux et ne doivent pas être envoyés sur GitHub.
