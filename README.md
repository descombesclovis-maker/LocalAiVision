# LocalAiStudio NextGen — branche de référence unique

**Branche officielle de développement : `nextgen/claude-code`.**

Contient le code source **LocalAiStudio NextGen de Claude Code avant fusion** (frontend React/Vite, backend FastAPI, scripts Windows), récupéré depuis `nextgen/claude-original`. Ce n'est PAS l'ancien moteur LocalAiVision présent sur `main`.

## Structure
- `backend/` : serveur API et moteurs de génération Web, photo, vidéo et publicité.
- `frontend/` : interface React/TypeScript.
- `installer/` : installation Windows.
- `install.ps1`, `start-localaistudio.bat` : scripts locaux.
- `docs/localai-nextgen/` : provenance, import et progression.
- `docs/localaivision-nextgen/` : audits des moteurs.

## Provenance et limites
Archive de référence reçue dans ChatGPT : `LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip`, SHA-256 **83b002299261f6935eb09165b4cd4fca98ef071251ffd47df34e0202208c9cfa**.
Le **code principal importé** a été recoupé par empreinte Git des fichiers critiques avec cette archive. Quatre fichiers d'icônes binaires absents de la branche donneuse restent à importer (voir PROVENANCE.md). Ne pas présenter cette branche comme un miroir complet octet par octet du ZIP tant que cette vérification n'est pas achevée.
Les sous-lots de sécurité Claude Code **1.1-a, 1.2 et 1.3** ne sont pas attestés ici : récupérer séparément leurs commits d'origine, sans simuler leur présence.

## Règles pour Manyfold
1. Travailler **uniquement** sur `nextgen/claude-code`. Ne modifier ni `main`, ni `codex/*`, ni `nextgen/claude-original`.
2. Ne jamais supprimer un modèle, une création ou un projet, ni télécharger plusieurs Go sans confirmation explicite.
3. Ne pas publier de clés API, fichiers `.env`, données privées, modèles lourds ni médias utilisateur.
4. Faire une mission de développement à la fois ; tests ciblés, commit, mise à jour PROGRESS.md ; pas de déploiement des moteurs dans le cloud.
5. L'audit V0 effectué sur `main` n'est pas une preuve concernant le code NextGen ; refaire les contrôles utiles sur cette branche.
6. Les tests GPU 12 Go, ComfyUI et Windows ne sont vérifiables que sur un PC équipé. Ne pas déclarer de génération validée sur la base d'un test statique.
