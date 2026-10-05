# Validation — 5 octobre 2026

## Réussi sur cette version

- Compilation syntaxique des modules Python principaux.
- Vérification syntaxique de `app.js`, `styles.js` et `intent.js` avec Node.js.
- **42 tests Python (unittest)** : workflows, prompts, profils RealVis/Animagine/VACE, reprise de téléchargement, endpoints HTTP, chat streaming, cohérence HTML/JS, installation/réparation des modèles et régressions précédentes.
- **20 cas JavaScript de routage** texte/image/vidéo/retouche/mouvement.
- **10 cas JavaScript de sélection de workflow** automatique ou manuel, dont RealVisXL, Animagine, Wan, image-to-video et VACE.
- Validation JSON du workflow `Video Motion VACE 1.3B.json`.

## Non validé matériellement ici

- Exécution sur Windows/WebView2 et construction de l’EXE.
- Téléchargement complet des modèles de plusieurs Go.
- Inférence réelle sur la RTX 3060 de l’utilisateur.
- Qualité visuelle finale et temps de calcul réels.
- `tests/test_mask.js` n’a pas été relancé dans cet environnement car le module de test `@napi-rs/canvas` n’y est pas installé. Le code masque n’a pas été modifié par la v2.1.
- Test Playwright de bout en bout non exécuté dans cet environnement.

## Reproduire les tests

```text
python -m unittest discover -s tests -p "test_*.py"
node --check local_app/web/app.js
node tests/test_intent.js
node tests/test_styles.js
```

Le test de masque nécessite `@napi-rs/canvas`. Le test navigateur nécessite Playwright/Chromium et doit être lancé avec un dossier de données de test et `LOCALVISIONAI_SKIP_SETUP=1` pour éviter les téléchargements de modèles.
