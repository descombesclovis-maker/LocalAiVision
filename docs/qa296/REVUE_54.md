# Recette de la revue 54

La branche de la PR 53 conserve les captures du Build 295 sous les noms `avant-*.jpg`. Les cinq images `apres-*.jpg` montrent la nouvelle révision. La [capture UHD examinée lors de la revue initiale](https://github.com/descombesclovis-maker/LocalAiVision/blob/30fb5c5bcd848a5b2b7d69f6254f792e88bc87b3/docs/qa296/apres-3840.jpg) permet de comparer directement les deux versions de la PR.

| Demande | Vérification |
| --- | --- |
| Surface 4K | À 3840 × 2160, la largeur de la grille dépasse 75 % de la fenêtre. Le test vérifie les rectangles du titre, de la scène et de l’action dans chaque carte aux cinq dimensions. [Capture UHD](apres-3840.jpg) |
| Mouvement | Chaque illustration utilise trois plans SVG animés séparément et un trait de lumière. Le test mesure la matrice de transformation sur 90 rappels d’animation en UHD. Le commutateur arrête les animations décoratives et persiste après rechargement. La préférence système arrête également la scène. [Vidéo de démonstration](studio-motion.mp4) · [Trace et mesures Linux](browser-report.json) · [Mouvement activé](motion-active.jpg) · [Mouvement réduit](motion-reduced.jpg) |
| Vision | Le caractère ASCII + ouvre le véritable sélecteur et reçoit un PNG. Le mode passe à I2V. Photo et Vidéo activent leurs modes respectifs. Les tests de menu couvrent le focus clavier, Échap, l’annulation de la demande d’accès et le retour des mêmes commandes lors du changement d’état visuel public/isolé. Le test d’état ne charge aucune création privée. [Capture Vision](vision.jpg) |
| Icônes | Chaque pictogramme conserve son intitulé accessible. L’interface utilise l’emoji couleur rendu par le système, ou le dessin vectoriel si le glyphe couleur est indisponible. Le rapport liste le rendu réellement utilisé pour les quatre destinations et les quatre modes. |
| Carte | Leaflet 1.9.4 utilise un jeu de six fiches injectées par le navigateur de test, dont cinq propositions dans le tiroir. Tous, Non renseigné et Renseigné produisent respectivement 6, 5 et 1 fiches. Le test compte aussi les marqueurs, y compris ceux regroupés, clique sur une fiche et utilise le bouton de zoom Leaflet. Les tuiles visibles proviennent du fournisseur de fond de carte. |
| Mobile | Le contenu se déroule dans la zone au-dessus du dock. Chaque action est atteignable au clavier et au défilement. Le test contrôle le point de clic au centre de chaque action. [Vue initiale](apres-390.jpg) · [Après défilement](mobile-vision-scroll.jpg) |
| Mise à l’échelle | Les contextes navigateur sont testés à 1365 × 768 avec des facteurs 1, 1,25 et 1,5 et un zoom de mise en page à 125 %. Le rapport conserve les coordonnées mesurées. Le réglage d’affichage Windows et le zoom utilisateur WebView2 nécessitent un contrôle dans l’application installée. |

## Parcours de carte

| Cas | Ordinateur | Mobile |
| --- | --- | --- |
| Tous, cinq propositions ouvertes | [1365 px](map-1365-all.jpg) | [390 px](map-390-all.jpg) |
| Site non renseigné | [1365 px](map-1365-missing.jpg) | [390 px](map-390-missing.jpg) |
| Site renseigné | [1365 px](map-1365-recorded.jpg) | [390 px](map-390-recorded.jpg) |
| Fiche sélectionnée | [1365 px](map-1365-fiche.jpg) | [390 px](map-390-fiche.jpg) |
| Après zoom | [1365 px](map-1365-zoom.jpg) | [390 px](map-390-zoom.jpg) |

Les fiches « démo » existent uniquement dans le test. Le scénario du mode natif vérifie le contrat de l’interface lorsque l’adaptateur signale que Places est prêt. Le filtre est désactivé et sa limite est expliquée. La validation sur le fournisseur réel demande des clés Maps et Places configurées et une vérification manuelle de l’ouverture d’une fiche Google.

## Reproduction

Depuis la racine du dépôt, lancer `python -m local_app.server` avec `LOCALVISIONAI_SKIP_SETUP=1` dans un environnement de test. Fournir `playwright-core` et `leaflet@1.9.4` au runtime de test. Lancer `node scripts/review_studio_54.cjs`. Le script utilise Edge par défaut, accepte un chemin Chromium dans `CHROME_PATH` et un dossier de résultats dans `QA_OUTPUT`. Le workflow « LocalAiWeb 3D checks » effectue ce parcours sous Windows et dépose le rapport et les captures dans l’artefact « Studio-54-Windows-Edge ».

La trace mesure la fréquence des rappels du navigateur dans l’environnement testé. La vidéo de huit secondes montre l’animation puis son arrêt. La cadence sur RTX 3060, le rendu WebView2 natif et la génération ComfyUI restent à mesurer sur une installation équipée.
