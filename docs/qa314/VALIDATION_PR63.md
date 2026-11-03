# Studio 314 — suivi de finalisation de la PR #63

## Empilement exact
- PR #60 (reconstruction UI) → PR #62 (Codex, logos officiels et thèmes) → **PR #63 (finitions et corrections)**.
- La PR #63 reste en **brouillon**, ne doit pas être fusionnée ni publiée automatiquement.
- Les PNG maîtres des trois logos sont conservés sans modification dans `local_app/web/assets/brand-reference/`.

## Demandes précises après la reprise
| Demande | Implémentation | Preuve |
| --- | --- | --- |
| Remettre les icônes du menu Vision | Mes créations, Photo, Vidéo, NSFW, Publicité gardent leurs pictogrammes | `studio-system.css`, `qa_ui_314.cjs`, capture `vision-menu-desktop.png` |
| « LoRA et modèles » sans icône, autre couleur | Icône masquée seulement pour cet item, fond bleu-cyan spécial | Test Chromium et Edge |
| « + Nouvelle discussion » sans icône graphique, autre couleur | `+` conservé dans le texte du bouton ; aucune image/SVG décorative | Test Chromium et Edge |
| Éléments derrière le menu masqués | Popover top-layer, focus, inert restauré | Test interaction |
| Retours chariot Windows du presse-papiers | Comparaison normalisée uniquement pour le presse-papiers ; métadonnées `original_prompt` comparées sans transformation | Test interaction Chromium et Edge + Python |
| Logos officiels sur pages secondaires et manifestes | PNG officiels Web/Vision/Studio, pas d'icônes historiques sur ces surfaces | `studio-brands.html`, manifests, favicon Vision public |
| Animations fluides et adaptatives | Traînées lumineuses violettes/cyan, reflets, transitions entre cartes/pages et contrôles | CSS composité, tests paused/reduced motion |
| Respect des moteurs et de l'espace réservé | Aucun changement ComfyUI/Codex/CRM ; sélecteurs visuels exclusifs `:not(.nsfw-active)` | Tests de régression ; tests sur poste réel encore requis |

## Résultat de CI observé
La dernière exécution de la PR #63, run `41738792950`, commit `91c299fe41dc187707ffa50b4a7e2276ec3cb85d`, est **entièrement verte** :
- Windows EXE PyInstaller et test de démarrage.
- Tests Python et contrôles de ressources/identités.
- Recettes Chromium et Edge : menu Vision, copier le prompt, absence de preview, suppression avec confirmation, animations réduites/suspendues, mobile.
- Captures aux résolutions 390×844, 1280×720, 1365×768, 1920×1080, 2560×1440 et 3840×2160.
- Artefacts Windows, icône, dérivés graphiques et captures/vidéos fournis par GitHub Actions.

Lien du workflow : https://github.com/descombesclovis-maker/LocalAiVision/actions/runs/41738792950

## Points non certifiés
- Fidélité **pixel à pixel** des SVG issus de VTracer (dégradés approximatifs) : le produit affiche les originaux PNG verrouillés, les SVG restent des exports dérivés.
- Fluidité sur la RTX 3060 en véritable génération ComfyUI ; aucun benchmark matériel réel dans GitHub Actions.
- Google Maps/Places avec tes clés, appels Codex, prestataires Stripe/Dropbox Sign/Vercel en production.
- WebView2 natif à tes DPI et comportement du logiciel installé sur le PC utilisateur.
- Appréciation artistique finale des animations et textes : les tests Chromium/Edge n'ont pas valeur d'acceptation esthétique humaine.

## Critères avant fusion
Vérifier sur le PC Windows que le nouveau menu s'ouvre et ferme correctement, que seuls les deux boutons spéciaux n'ont pas d'icônes, que les trois logos/photographies s'affichent, et que l'accès aux projets existants ne change pas.

**Statut : candidate de test UI validée automatiquement ; non certifiée comme livraison commerciale ou graphique définitive.**
