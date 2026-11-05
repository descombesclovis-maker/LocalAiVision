# Build 316 — contrôles encore nécessaires

## GPU public, sans installation ni changement des workflows

Fermer les générations actives ; conserver les modèles actuels. Démarrer le
ComfyUI existant. Depuis la racine des sources, dans son Python déjà fonctionnel :

```powershell
python scripts/benchmark_public_engine.py --engine sdxl --case dog-grass
python scripts/benchmark_public_engine.py --engine sdxl --case dog-grass --run --seed 314159 --model-root "CHEMIN_COMFY_EXISTANT\models"
python scripts/benchmark_public_engine.py --engine hunyuan-t2v --case walk-3 --run --seed 314159 --model-root "CHEMIN_COMFY_EXISTANT\models"
```

La première commande inspecte sans soumettre de rendu. `--run` envoie exactement
un rendu public et copie ses sorties et SHA-256 dans `benchmark-results`.
Aucun modèle, nœud ni package n'est téléchargé par ce script. Ne jamais remplacer
un chemin existant par une installation de secours arbitraire. Les fichiers
privés et les LoRAs ne sont ni examinés ni modifiés par ce protocole.

Répéter avec les trois seeds du corpus et examiner les originaux selon les axes
listés dans `benchmarks/public-cases.json`. Passer ensuite à `walk-5` puis `walk-10`
si les durées précédentes réussissent. Ne pas enchaîner après un OOM : conserver
le reçu, vérifier la file ComfyUI et les journaux avant toute relance.

La durée inclut attente et observation de fin ; elle n'est pas un temps
 d'inférence pur. Les échantillons `/system_stats` concernent toute la machine et
les périphériques ComfyUI ; ce ne sont pas des pics mémoire du seul processus.
Les hashes modèles ne sont renseignés que si un fichier unique est retrouvé dans
le répertoire explicitement fourni. Une qualité visuelle non revue reste non
qualifiée. I2V, image 2.1 haute résolution, caches et attention optimisée restent
à qualifier séparément ; aucun réglage rapide n'est imposé sans mesure.

## Web

Les six briefs sont dans `benchmarks/web-briefs.json`. Exiger Codex CLI connecté à
ChatGPT Plus, sans substitution automatique par une API payante. Trois créations
indépendantes par brief, puis modification ciblée, restauration, export. Garder
brief, commit des sources, logs, captures 390/820/1440, résultats métier et ZIP.
Un scénario mocké dans les tests Python ne compte pas comme une génération.

`/api/web/project/delivery?id=...` expose l'état courant. Compilation réussie,
contrôles navigateur exécutés et recette métier liée à l'empreinte des fichiers
sont distincts de la prévisualisation. Le parcours de saisie/exécution des preuves
métier reste à terminer : il ne faut pas remplir `functional_checks.json` avec une
validation inventée pour faire passer la livraison. Les captures de secours
`captured` ne valent pas un contrôle Playwright réussi. L'art reste à revoir.

## Dates

`LOCALAI_BUSINESS_TIMEZONE=Europe/Paris` choisit une zone IANA disponible. Sans
configuration, le fuseau et les règles DST du système sont employés. Les nouveaux
devis mémorisent la politique utilisée. Sous Windows, si la base IANA n'est pas
présente dans Python, une zone explicite indisponible échoue clairement ; utiliser
le fuseau local du PC en attendant l'ajout autorisé de cette dépendance. Les anciens
devis sans zone ne sont pas réécrits et suivent la politique configurée courante.

## Windows et rendu

La CI doit fabriquer un nouvel EXE depuis les sources, et conserver les preuves
icône, DLL Python, WebView2, démarrage et mise à jour. La version produit 316
(version 3.1.6) est distincte de l'identifiant unique du run `build-N` utilisé par
le protocole de mise à jour. Le manifeste de sources et `pip freeze` identifient
les ressources et dépendances ; ils ne garantissent pas un PE bit-identique.

Comparer aussi le rendu 315.5 personnalisé au 316, et pas seulement au 315 GitHub.
Aucun refactor CSS visuel ne doit être certifié sans ces captures. Tester DPI
100/125/150 %, clavier, fermeture/redémarrage et conservation des données sur une
copie de travail. Les archives 315.5 originales restent la possibilité de retour.
