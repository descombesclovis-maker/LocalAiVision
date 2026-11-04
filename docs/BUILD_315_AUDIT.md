# Build 315 — audit et preuves disponibles

Date de l'audit : 4 novembre 2026. Branche de travail : `codex/studio-315-premium-stabilisation`, basée sur le commit exact `742e34e40e91af0734ed28bfa4842ac3c582c3fc` de la PR #63.

## Périmètre livré dans cette révision

LocalAiWeb reçoit déjà l'état réel du moteur média via `/api/studio/activity`. Le Build 315 relaie au seul aperçu intégré de l'éditeur l'information indiquant qu'un travail média est en préparation ou en cours. La scène WebGL du modèle `cinematic3d` limite alors sa cadence à 8 images/s. Une file d'attente inactive ne déclenche pas cette limite. La cadence habituelle revient lorsque la préparation et le rendu actif sont terminés.

La limite porte sur les appels de rendu du site de démonstration embarqué. Elle ne change pas la cadence des vidéos générées, les paramètres des workflows, ni la qualité d'un média exporté. Elle ne garantit pas à elle seule un gain mesuré de VRAM, de RAM ou de durée d'inférence.

## Protection de l'espace NSFW

Les fonctions de génération, les prompts, les modèles, les workflows Hunyuan, les samplers, les CFG, les LoRAs et le routage NSFW n'ont pas été modifiés. Le message de réduction est émis uniquement depuis `data-studio-page="editor"`. Il vise l'origine exacte `preview-web-<identifiant>.localhost` du projet, jamais une origine arbitraire. Le visualiseur vérifie la fenêtre parente, l'origine loopback et le port. Il n'est pas envoyé depuis l'espace Vision ou NSFW.

La PR #64 touche la présentation, les recettes CI et le transport HTTP local. Dans `server.py`, seule la capacité d'accueil des connexions passe à 128; les fonctions média ne changent pas. Aucun fichier de modèles ou de workflows ComfyUI n'y figure.

## Vérifications locales

| Contrôle | Résultat |
|---|---|
| Tests Python | 313 exécutés avec succès ; 1 test Windows ignoré sous Linux |
| Tests Node | 10 réussis (`node --test tests/*.mjs`), dont transport et validation des origines |
| Syntaxe JS modifié | `node --check` réussi pour `studio-activity.js`, `cinematic3d/app.js` et `qa_ui_314.cjs` |
| Syntaxe Python modifié | `py_compile` réussi pour le fixture navigateur et le test de portée |
| Diff | `git diff --check` réussi |
| Hôte | 9,7 GiB de RAM; `nvidia-smi` absent; aucun ComfyUI/Codex connecté |
| Navigateur local | Chromium 153 extrait d'une dépendance de test temporaire; 8 scénarios d'interaction réussis |

## Dernières preuves CI et correction de transport

Le run `41811438336`, au commit `79873a303c4cd82cd03a47334b35ba0dc07318d1`, compile et démarre l'EXE Windows, confirme une fenêtre WebView2 non noire et réussit les contrôles d'icône, de DLL et de transfert de mise à jour. La publication de version est ignorée. Les exports de marque 4096 px sont archivés.

Une première exécution Chromium passait lorsque le témoin se trouvait encore sur le document initial de l'iframe. Le vrai aperçu est redirigé vers un sous-domaine local distinct : la restriction initiale à l'origine de l'éditeur empêchait le message d'y parvenir après navigation. La correction vise maintenant l'origine exacte du projet et accepte uniquement son parent loopback de même port, sans supprimer l'isolation des API. Le test attend le véritable contenu du site sur ce sous-domaine avant d'envoyer les deux états. Les huit scénarios passent localement, avec accusés de réception sur l'origine isolée. L'activité média est une fixture étiquetée; aucun rendu IA/GPU n'est présenté comme réel.

Edge révèle ensuite une page Pro dépourvue de sa feuille de style principale, avec un débordement horizontal à 1280 px. La capture conserve cette erreur. Le serveur utilisait la file d'accueil par défaut de cinq connexions; cette révision la porte à 128 pour absorber les rafales de ressources. Un test établit 32 connexions en attente sans refus. La recette navigateur exige désormais que toutes les feuilles de style soient chargées et journalise les échecs de ressources. La correction attend encore sa validation complète Chromium/Edge.

Les captures d'accueil ordinateur et mobile ont été inspectées : les deux photographies, les cartes et les textes s'affichent. Cela ne certifie pas toutes les vues ni tous les moteurs de génération.

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
