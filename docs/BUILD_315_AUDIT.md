# Build 315 — audit et preuves disponibles

Date de l'audit : 4 novembre 2026. Branche de travail : `codex/studio-315-premium-stabilisation`, basée sur le commit exact `742e34e40e91af0734ed28bfa4842ac3c582c3fc` de la PR #63.

## Périmètre livré dans cette révision

LocalAiWeb reçoit déjà l'état réel du moteur média via `/api/studio/activity`. Le Build 315 relaie au seul aperçu intégré de l'éditeur l'information indiquant qu'un travail média est en préparation ou en cours. La scène WebGL du modèle `cinematic3d` limite alors sa cadence à 8 images/s. Une file d'attente inactive ne déclenche pas cette limite. La cadence habituelle revient lorsque la préparation et le rendu actif sont terminés.

La limite porte sur les appels de rendu du site de démonstration embarqué. Elle ne change pas la cadence des vidéos générées, les paramètres des workflows, ni la qualité d'un média exporté. Elle ne garantit pas à elle seule un gain mesuré de VRAM, de RAM ou de durée d'inférence.

## Protection de l'espace NSFW

Les fichiers de génération, les prompts, les modèles, les workflows Hunyuan, les samplers, les CFG, les LoRAs et le routage NSFW n'ont pas été modifiés. Le message de réduction est émis uniquement depuis `data-studio-page="editor"` et n'est accepté que par la fenêtre parente de même origine dans le visualiseur 3D. Il n'est pas envoyé depuis l'espace Vision ou NSFW.

La liste des fichiers de la PR #64 comprend uniquement le workflow CI, le relais d'activité, le visualiseur WebGL, les tests de cadence et de portée, ainsi que la documentation Build 315. Aucun fichier de modèles ou de workflows n'y figure.

## Vérifications locales

| Contrôle | Résultat |
|---|---|
| Tests Python | 311 réussis ; 1 test Windows ignoré sous Linux |
| Tests Node | 10 réussis |
| Syntaxe JS modifié | `node --check` réussi pour `studio-activity.js`, `cinematic3d/app.js` et `qa_ui_314.cjs` |
| Syntaxe Python modifié | `py_compile` réussi pour le fixture navigateur et le test de portée |
| Diff | `git diff --check` réussi |
| Hôte | 9,7 GiB de RAM; `nvidia-smi` absent; aucun ComfyUI/Codex connecté |
| Navigateur local | Playwright présent; exécutable Chromium absent |

## Contrôles CI en attente

Le workflow Build 315 déclenche pour la branche de base de la PR #63. Il compile et démarre le nouvel EXE Windows, vérifie les icônes, attend une vraie première peinture non vide de WebView2 et teste l'auto-update, puis exécute la suite d'interaction dans Chromium et Edge. La recette inclut les six résolutions et un contrôle du signal média « en attente » puis « en cours » dans le vrai éditeur local.

Les résultats et les captures de ce run ne seront consignés comme preuves qu'après la fin des travaux GitHub Actions. Aucun résultat de CI n'est supposé dans ce rapport.

## Capacités préexistantes constatées dans le dépôt

Le dépôt de référence contient déjà un agent de génération de sites choisi avec Codex CLI authentifié, une conservation du brief initial, une direction créative liée au secteur, un plan multipage, des contrôles du site compilé et une revue navigateur facultative. Il possède aussi un modèle WebGL adaptatif avec des modes qualité/équilibré/performance, une résolution ajustable, des solutions de repli mobile et une pause quand l'onglet est masqué.

Ces éléments sont présents avant cette PR. Les tests unitaires qui les couvrent ne prouvent pas qu'une génération réelle fonctionne avec le compte Codex ou les projets de l'utilisateur.

## Éléments non certifiables depuis cet hôte

- Aucun benchmark RTX 3060 de génération photo ou vidéo, pic VRAM, consommation RAM en rendu IA ou séquence de 10 secondes n'a été réalisé.
- Aucun site PawMood réel n'a été généré; l'agent Codex n'est pas installé/authentifié ici.
- Aucune génération photo, vidéo ou publicité par IA n'a été exécutée; ComfyUI et les modèles ne sont pas disponibles sur cet hôte.
- Les clés Google Maps/Places n'ont pas été testées en direct.
- Les déploiements, transactions, campagnes, achats et publications n'ont pas été exécutés.
- Le rendu WebView2 est contrôlé sur le runner Windows lorsque la capture CI passe; les DPI Windows 100 %, 125 % et 150 % restent à contrôler sur le PC de l'utilisateur.
- Les dérivés SVG de marque issus de contours raster sont des tracés vectoriels de chemins avec dégradés approximés, pas des fichiers sources parfaits ni des équivalents pixel-identiques. Les PNG maîtres demeurent la référence visuelle verrouillée.

La PR reste en brouillon; aucun merge, release ou déploiement n'est effectué.
