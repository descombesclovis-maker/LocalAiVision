# Recette PC — audit humain 1

Dans PowerShell, depuis les sources correspondant exactement au paquet testé. ComfyUI doit être démarré sur `127.0.0.1:8188`. Ces commandes n'installent rien. Les benchmarks s'exécutent l'un après l'autre ; ne pas lancer un autre rendu simultanément.

## Codex

```powershell
codex login status
python scripts/diagnose_codex.py --output diagnostic-codex.json
```

Si le CLI indique réellement une absence de session, utiliser `codex login`, terminer la connexion puis revérifier dans LocalAiWeb. Un état `timeout`, `check_failed` ou `launch_failed` demande un diagnostic, pas un effacement des identifiants. Ne pas transmettre `auth.json` ni de jeton.

Tester un site réel, fermer puis rouvrir Studio, reprendre le même projet, puis vérifier une interruption réseau momentanée. La génération ne doit pas être redémarrée en doublon tant que son état est actif. En cas d'arrêt du processus, le projet et ses fichiers doivent rester accessibles ; la reprise d'une tâche interrompue n'est pas une garantie de continuation de session CLI.

## Comparaisons contrôlées du conditionnement public

Le mode `original` transmet le prompt brut ; `public` applique les enrichissements serveur actuels et le planificateur public. Cette comparaison isole ces traitements : **elle ne reproduit pas intégralement l'ancienne interface** et exclut l'enrichissement animalier propre au navigateur. Pour comparer les versions de l'application, conserver les sorties de l'ancien build et leurs provenances, puis reproduire ses seeds et réglages dans le nouveau build.

```powershell
$cases = @('audit-seated', 'audit-dog', 'audit-products')
foreach ($case in $cases) {
  python scripts/benchmark_public_engine.py --engine sdxl --case $case --seed 314159 --quality quality --conditioning original --run --output benchmark-results/raw
  if ($LASTEXITCODE -ne 0) { break }
  python scripts/benchmark_public_engine.py --engine sdxl --case $case --seed 314159 --quality quality --conditioning public --run --output benchmark-results/public
  if ($LASTEXITCODE -ne 0) { break }
}
```

Recommencer avec `--engine hunyuan-image` si ce moteur est installé, puis les seeds `271828` et `161803`. Les images, graphes, paramètres, contrôles de décodage et mesures disponibles sont enregistrés. Laisser les mesures absentes à null ; ne pas leur attribuer une valeur supposée.

## Vidéos réelles

```powershell
python scripts/benchmark_public_engine.py --engine hunyuan-t2v --case audit-turn-3 --seed 314159 --quality balanced --conditioning public --run --output benchmark-results/video3
python scripts/benchmark_public_engine.py --engine hunyuan-t2v --case audit-turn-5 --seed 314159 --quality balanced --conditioning public --run --output benchmark-results/video5
```

Arrêter la progression de la recette si le rendu précédent échoue ou présente des déformations fortes. Dix secondes seulement après validation des durées courtes :

```powershell
python scripts/benchmark_public_engine.py --engine hunyuan-t2v --case audit-turn-10 --seed 314159 --quality balanced --conditioning public --run --output benchmark-results/video10
```

I2V avec le même prompt, une référence autorisée et une empreinte conservée :

```powershell
python scripts/benchmark_public_engine.py --engine hunyuan-i2v --case audit-turn-3 --seed 314159 --quality balanced --conditioning public --image .\reference.png --run --output benchmark-results/i2v3
```

Le fichier original de référence est lu, jamais modifié. Une copie est envoyée au ComfyUI local. Les sorties du benchmark ne sont pas automatiquement ajoutées à la galerie Studio.

Pour une comparaison explicite Wan, remplacer le moteur par `wan-t2v`. Cela ne change pas le moteur sélectionné dans l'application. Ajouter `--model-root` avec le véritable dossier `ComfyUI\models` pour enregistrer les SHA-256 des poids ; ce calcul peut être long.

Les snapshots mémoire du benchmark concernent le système / périphérique ComfyUI. Ce ne sont pas des pics exacts du seul processus, ni des temps d'inférence isolés. Qualifier séparément la netteté, l'anatomie, les mains non demandées, le visage, le mouvement et la stabilité des textures.

## Interface et marques

- Ouvrir Vision : accueil Chat, logo au-dessus du titre ; tester menu, Photo, Vidéo, Publicité, Mes créations puis retour Chat.
- Écrire en Chat une phrase contenant « photo » et « vidéo » : aucune génération ne doit être soumise.
- Choisir une marque depuis la troisième carte Studio, redémarrer ; vérifier son nom et son logo.
- Associer cette marque à un site et à une publicité ; changer ensuite la marque globale : ces projets doivent conserver leur association.
- Pendant un rendu : vérifier la pastille d'en-tête, la galerie et l'aperçu ; aucun succès ne doit être annoncé sur simple disparition d'une tâche.
- Vérifier l'accès à l'aperçu Web pendant les finitions et la consultation des fichiers / versions précédentes.
- Comparer les sorties exportées avec les logos officiels ; les fichiers originaux doivent rester disponibles.
