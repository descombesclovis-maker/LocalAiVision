# Studio 314 — priorité 1 : icône Windows officielle

Cette première étape répond à la demande de remplacer immédiatement l’icône
de l’EXE. Elle est empilée sur la branche de la PR #60, avec la charte verrouillée.
Les autres travaux de l’issue #61 ne sont pas déclarés terminés.

## Acceptation

- [x] Archiver les quatre PNG maîtres intacts et leur manifeste fourni.
- [x] Vérifier SHA-256 de chaque fichier avant conversion.
- [x] Utiliser le carré Studio complet, sans retouche ni découpe intérieure.
- [x] Produire 16/24/32/48/64/128/256 px à partir de l’original entier.
- [x] Comparer pixel par pixel les sept images de l’ICO à des réductions indépendantes.
- [x] Remplacer le dessin procédural de l’ancien monogramme.
- [x] Relier l’ICO aux builds PyInstaller GitHub/local et à la fenêtre native.
- [ ] Vérifier le résultat du job Windows sur le commit de cette PR.
- [ ] Examiner ses preuves Shell, fenêtre et raccourci avant certification Windows.

## Source et conversion

Source : `local_app/web/assets/brand-reference/LocalAIStudio_Official_Original.png`.
SHA-256 : `9c8e94862781f263b1b95d2e13504518f7a624b809db93e074ce1a498b9fdcd4`.
Dimensions : 724 × 724, carré complet approuvé.

Le générateur refuse un maître différent. Il effectue uniquement une réduction
proportionnelle LANCZOS, puis un encodage PNG sans perte dans un véritable
conteneur ICO multirésolution. Aucun masque, changement de transparence,
recoloriage, dessin ou suppression du texte/cadre n’est appliqué.

Les originaux Web, Vision et le triptyque sont aussi conservés sans modification.
Les sommes du manifeste incluent la charte de l’archive, conservée telle quelle.

## Points de raccordement

- `scripts/prepare_windows_brand.py` : conversion et métadonnées PE.
- `local_app/assets/LocalAiStudio.ico` : icône disponible en exécution depuis les sources.
- `.github/workflows/build-windows.yml` et `BUILD_LOCALVISIONAI.bat` :
  `--icon build/branding/LocalAiStudio.ico` et inclusion dans les ressources natives.
- `local_app/launcher.py` : même icône explicitement transmise à la fenêtre pywebview.
- Les raccourcis de l’updater référencent déjà `LocalVisionAI.exe,0` ; ils
  utilisent donc la nouvelle ressource sans modifier les autres propriétés.

Le nom de l’EXE et les chemins de mise à jour sont conservés.

## Vérification Windows

`scripts/verify_windows_icon.py` lit les icônes du vrai EXE via Win32, puis
l’icône choisie par Windows Shell pour l’Explorateur. Il compare leurs pixels
à des réductions du maître entier. Il crée seulement un raccourci temporaire
et vérifie sa cible et son `IconLocation`.

Il lance aussi l’application compilée dans un répertoire de données temporaire,
avec installation des moteurs et mises à jour automatiques désactivées. Le
script lit l’icône de la vraie fenêtre et enregistre une capture du bureau.
L’icône utilisée pour la fenêtre/barre des tâches doit correspondre à la source.

Les preuves sont jointes au job sous `LocalAiStudio-OfficialIcon`.
Un ancien raccourci épinglé peut conserver une image mise en cache par Windows ;
ce test ne modifie ni les raccourcis ni le cache du PC utilisateur.

Aucune fusion ni release automatique n’est autorisée. Cette étape ne modifie
pas les interfaces Web/Vision, l’espace réservé, les moteurs ou les projets.
