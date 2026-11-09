# LocalAiStudio NextGen — branche de référence

**Branche dédiée :** `nextgen/claude-original`

## État actuel : IMPORT DU CODE NEXTGEN À FINALISER

Cette branche est volontairement isolée du code historique de `main`. Elle ne doit pas être confondue avec les branches `codex/studio-*`.

Le snapshot original **NextGen avant fusion** est disponible dans l’archive nommée :
`LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip`.
C’est le code React + FastAPI remis dans la conversation ChatGPT. **Il ne contient pas nécessairement les dernières corrections 1.1-a et 1.2 de Claude Code** réalisées après la création de ce ZIP.

**IMPORTANT : le code complet n’a pas encore été importé dans cette branche.** N’effectue pas de développement ni d’audit des moteurs sur cette branche tant que `backend/server.py` et `frontend/package.json` ne sont pas présents dans le dépôt distant.

## Procédure d’import contrôlée

1. Fournir à Manyfold l’archive NextGen originale mentionnée ci-dessus (ne pas utiliser le ZIP « Fusion »).
2. Se placer sur la branche `nextgen/claude-original` et vérifier `git status`.
3. Exécuter `python scripts/import_nextgen_archive.py /chemin/vers/LocalAiStudio-NextGen-Source-Avant-Fusion-Pour-Manyfold.zip` depuis la racine.
4. Vérifier l’absence de secrets, de modèles téléchargés, d’environnements locaux et d’écrasements de fichiers existants.
5. Vérifier `backend/server.py`, `frontend/package.json`, `frontend/src/App.tsx`, `INSTALLATION.md` et les scripts Windows.
6. Lancer les tests ciblés **sans télécharger de modèles**.
7. Faire un commit uniquement après validation, pousser la branche, vérifier les fichiers sur GitHub.
8. Si une archive plus récente de Claude Code devient disponible, l’intégrer dans une **révision séparée** avec comparaison des fichiers et sans perte des protections.

## Structure attendue après import
```text
backend/             # FastAPI, pipelines Web/Vision, ComfyUI
frontend/            # React, TypeScript, Vite
installer/           # Windows, scripts installateurs
docs/                # Suivi et provenance
scripts/             # Outils d'import et diagnostic
install.ps1
start-localaistudio.bat
INSTALLATION.md
SPEC.md
```

## Politique de sécurité
Aucun `.env`, clé API, modèle IA, création multimédia ou dossier utilisateur dans Git. **Ne déployez pas publiquement** cette version non validée, et ne présumez pas qu’elle inclut le verrou d’accès/isolement développés plus tard dans Claude Code.
