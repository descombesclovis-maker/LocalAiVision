# V2-AC — Évaluation de Wan 2.2 TI2V 5B pour le Space distant

Date de l'audit : 2026-11-11. Branche `nextgen/claude-code`, point de départ `eb4a3c3`.

## Décision

**Ne pas installer ni intégrer Wan 2.2 dans ce Space pour l'instant; ne pas lancer de génération Wan.** La carte modèle confirme un vrai modèle Apache-2.0, T2V+I2V, natif 1280×704 à 24 FPS, et l'allocation distante de 48 Go paraît suffisante en VRAM sur le papier. Mais le budget Free documenté est de 300 s GPU/jour, le benchmark constructeur pour un clip 720p de 5 s est de 534,7 s sur une RTX 4090, le Space ne fournit pas le quota restant, et le coût réel sur son GPU Blackwell 48 Go n'a pas été mesuré. De plus, l'environnement existant de SANA impose Transformers >=5 alors que les dépendances du code Wan de référence pinent Transformers <=4.51.3. Charger les deux dans le même environnement n'est donc pas validé. L'installation, le redémarrage et un appel GPU risqueraient de compromettre le candidat SANA ou de dépasser le quota gratuit; ces étapes ne sont pas justifiées par les preuves disponibles.

Aucun crédit payant, déploiement, téléchargement de checkpoint, installation, inférence Wan ou modification du Space n'a été effectué pendant V2-AC. Aucun rendu supplémentaire SANA n'a été lancé. L'API d'état existante a été interrogée sans GPU : le Space demeure `RUNNING`, SANA 4-step est `generation_ready=true`, T2V seulement.

## 1. SANA conservé — constat réel

Aucun fichier, endpoint, checkpoint ni configuration SANA n'a été supprimé ou modifié. Le rendu de référence V2-AB reste dans `backend/bench_runs/v2ab/` (gitignored) :

- MP4 H.264, 1280×736, 16 FPS, 81 images, 5,0625 s.
- 17,594 s de l'appel complet incluant soumission/attente/récupération; temps mesuré dans le traitement du moteur 12,95 s. Ces durées ne sont pas le téléchargement initial des poids.
- Aspect visuel photoréaliste prometteur et décor stable sur les images examinées; le sujet est cependant un chat tigré roux, et non le renard demandé. Il enjambe/marche sur le tronc au lieu d'effectuer clairement le saut demandé. La direction demandée n'est pas démontrée par le clip. Quelques images ne suffisent pas à certifier anatomie ou cohérence temporelle globale.
- Verdict : fichier vidéo valide et présentation convaincante, mais échec de fidélité sur les exigences centrales. Ne pas présenter SANA comme un modèle qui suit parfaitement les prompts.
- Aucun relevé de VRAM au moment de ce rendu n'existe; aucun chiffre de consommation n'est donc affirmé ici.

## 2. Compatibilité Wan 2.2 TI2V 5B

### Fichiers et stockage

Lecture des métadonnées de la branche `main` du dépôt officiel HF `Wan-AI/Wan2.2-TI2V-5B` (requête API, sans récupérer les poids) : **34 184 542 285 octets** de fichiers de poids pertinents (environ 31,84 GiB) :

- Transformer : trois shards safetensors, 9 825 014 472 + 9 995 661 736 + 178 558 176 octets.
- UMT5 XXL BF16 : 11 361 920 418 octets, plus tokenizer/config.
- VAE : 2 818 839 170 octets.

Le Space existant conserve aussi les artefacts SANA/Gemma/VAE, estimés à 23,43 GiB par son propre préflight. Les deux familles représenteraient environ 55,27 GiB (59,35 Go décimaux) de fichiers en cache. Le `storage_status` du Space a rapporté environ 2,7 TiB libres : le disque n'est pas le blocage. Cette addition ne constitue pas une installation et n'est pas une mesure de taille de chargement mémoire.

### GPU et RAM

- Le runtime de ce Space est le profil ZeroGPU `large`; l'audit de déploiement V2-Y a observé une RTX PRO 6000 Blackwell, 48 512 MiB VRAM. La requête de statut non-GPU actuelle confirme encore le profil `large`; aucun probe GPU n'a été relancé.
- La carte officielle Wan indique un minimum de 24 Go VRAM et recommande `--offload_model True --convert_model_dtype --t5_cpu` sous 80 Go. Son tableau constructeur mesure 22,9 GB de mémoire de crête pour TI2V-5B sur une RTX 4090 à 720p. Cela rend 48 Go **plausibles**, pas validés pour cette allocation ZeroGPU, son overhead, ou la coexistence avec SANA.
- Les options officielles de déchargement déplacent de la charge vers la RAM hôte. Ni le besoin RAM de pointe exact de ce parcours ni la RAM disponible du worker Space n'étaient accessibles par les endpoints lus. La RAM n'est donc pas vérifiée.
- Wan natif documente 1280×704 (720p nominale) à 24 FPS, pas 1280×736. Le modèle Diffusers officiel confirme aussi la tâche I2V. Aucun chemin 1080p natif n'est établi dans cette évaluation; un upscale ne serait pas compté comme résolution native.

### Dépendances et coexistence SANA/Wan

- Le dépôt d'inférence de référence Wan réclame Torch >=2.4, torchvision >=0.19, torchaudio, OpenCV, Diffusers, Accelerate, tokenizers, NumPy <2 et `flash_attn`, entre autres. Sans FlashAttention, son code contient un repli SDPA PyTorch, avec avertissement de masquage/performance; compatibilité et vitesse sur cette carte Blackwell n'ont pas été testées.
- Le Space SANA existant déclare `transformers>=5.0.0` et `diffusers>=0.40.0`. Les requirements Wan de référence pinent `transformers>=4.49.0,<=4.51.3`; la recette Diffusers Wan demande de prendre Diffusers depuis `main`. Ce conflit de versions exclut une installation côte à côte non isolée tant qu'un environnement commun compatible n'a pas été démontré.
- SANA charge déjà ses propres composants au niveau module et sur CUDA. Aucune politique sûre d'éviction/récupération des poids, de verrouillage entre modèles, de nettoyage après échec, ni de validation mémoire partagée n'est en place. Une simple entrée de registre « Wan » ne suffirait pas.

### Licence et budget GPU gratuit

- La carte du dépôt original et celle du dépôt Diffusers indiquent Apache-2.0, y compris usage commercial, sous les obligations usuelles de la licence. Il faut également conserver les avis de licence/attribution du code de référence et examiner séparément les droits des composants/données qui seraient ajoutés.
- La documentation officielle ZeroGPU consultée annonce 5 minutes de quota GPU quotidien pour un compte Free; le restant n'est pas retourné par le Space. La fonction GPU réserve une durée maximale déclarée, et `xlarge` consomme deux fois le quota de `large`. Nous conservons le Space sur `large` et n'activons aucun crédit ni option payante.
- La table de performance officielle Wan rapporte **534,7 s** pour une vidéo TI2V-5B T2V 720p sur une seule RTX 4090, après warm-up; environ 22,9 GB peak. C'est un benchmark fournisseur, pas une mesure sur notre RTX PRO 6000 Blackwell, et ce n'est pas une garantie de temps. C'est déjà supérieur aux 300 s/jour gratuits annoncés, sans compter les incertitudes du Space/du chargement et les appels antérieurs du compte. La quota restante est inconnue. Nous n'avons donc pas soumis le travail « au cas où » : un échec pourrait quand même réserver/consommer du quota.
- La doc consultée n'énonce pas dans cette page une limite universelle fixe de runtime supérieure pour chaque compte; `duration` détermine la durée maximale de la fonction. Le budget journalier connu suffit à refuser ce test non démontré. Aucun facteur d'accélération Blackwell n'est extrapolé.

## 3. Résultat comparatif

Pas de vidéo Wan produite : il n'existe donc pas de comparaison visuelle Wan/SANA appariée et pas de classement général possible. Pour cette seule vidéo SANA, on peut conclure photoréalisme visuel prometteur mais sujet/action faux. L'objectif « meilleur moteur réel » reste **indéterminé** entre Wan et SANA; seule SANA a réellement été rendue sur ce Space. V2-AB n'est pas une preuve qu'une architecture est généralement supérieure, et aucune image Wan n'est présentée comme existante.

## 4. Prompt français — plan de travail, pas de promesse de résultat

Le connecteur SANA conserve et envoie actuellement le prompt français verbatim, et l'enregistre comme `requested_prompt_verbatim`. C'est sûr et testable, mais le clip montre que cette précaution ne garantit pas la compréhension sémantique.

Une prochaine expérimentation contrôlée pourrait produire, pour chaque clause source, une traduction anglaise structurée liée à l'original : sujet/quantité/attributs, position, action et direction, ordre temporel, négations, contraintes de style. Le prompt original doit rester conservé dans les métadonnées et être envoyé avec la représentation traduite uniquement après un test d'équivalence clause-par-clause. Aucun élément visuel nouveau ne doit être complété par le traducteur. Les tests doivent comparer, sur le même moteur/seed/profil, la version française seule et la version anglaise structurée, puis examiner séparément identité, compte, couleurs, position, direction, action, négations et stabilité. Une comparaison d'un seul essai ne prouverait toujours pas une amélioration générale.

Aucune traduction n'a été ajoutée au connecteur ni activée automatiquement : l'environnement Space ne comporte pas de traducteur vérifié, et le traducteur/LLM local ne garantit pas à lui seul l'équivalence sémantique. Cela évite de remplacer un prompt utilisateur par une reformulation non vérifiée. Les tests ciblés de V2-AC confirment que le comportement existant envoie toujours la chaîne originale intacte.

## 5. Suite proposée (non exécutée)

Avant toute installation : régler l'incompatibilité Transformers sans casser SANA, établir un chargement exclusif (un seul modèle en mémoire), valider RAM/VRAM via diagnostic distant à coût minimal, et disposer d'un moyen fiable de connaître le quota restant ou d'attendre une fenêtre où au moins la durée attendue tient dans le quota gratuit. Ensuite seulement, publier une branche du Space réversible et contrôler son `generation_ready`, sans lancer automatiquement de génération. Si le runtime/quotas Free ne peuvent pas héberger la durée mesurée ou si le quota reste inconnu, garder Wan hors du Space gratuit; demander une autorisation explicite avant toute autre infrastructure payante. Toute comparaison qualitative future doit recevoir une autorisation pour un essai et un seuil de quota, puis n'effectuer qu'une génération.

Durées 3/6/9/12/20 s, 1080p, I2V dans ce Space, continuité multi-segments et objectif de quelques minutes restent non validés.

## Vérifications V2-AC

- Backend : `python -m pytest backend/tests/test_hf_sana.py backend/tests/test_hf_video.py -q` — **10 passed**.
- Space : `python -m pytest spaces/LocalAiStudio-VideoEngine/tests/test_engine_registry.py spaces/LocalAiStudio-VideoEngine/tests/test_storage_preflight.py -q` — **8 passed**.
- Lecture API/stockage/statut HF authentifiés mais sans GPU : Space `RUNNING`, SANA `generation_ready=true`; modèle Wan absent de la liste des fichiers du Space; aucun quota restant exposé.
- Interface React, paramètres UI, atelier Publicité, moteurs locaux, base de données, projets, données utilisateur, modèles locaux et stash `preserve-v2q-before-v2r` inchangés.

## Sources

- Carte et fichiers Wan originaux : https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- API métadonnées fichiers : https://huggingface.co/api/models/Wan-AI/Wan2.2-TI2V-5B/tree/main?recursive=true&expand=true
- Licence officielle Apache-2.0 : https://raw.githubusercontent.com/Wan-Video/Wan2.2/main/LICENSE.txt
- Code et dépendances de référence : https://github.com/Wan-Video/Wan2.2/blob/main/requirements.txt et https://github.com/Wan-Video/Wan2.2/blob/main/wan/configs/wan_ti2v_5B.py
- Carte/recette Diffusers et benchmark de temps/mémoire : https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers
- Documentation officielle ZeroGPU (quota, `duration`, tailles) : https://huggingface.co/docs/hub/spaces-zerogpu
- Statut Space privé : https://huggingface.co/spaces/clocltrrh/LocalAiStudio-VideoEngine

**Arrêt V2-AC :** Wan n'est ni téléchargé, ni intégré, ni rendu; SANA est préservé. La compatibilité VRAM est plausible, mais le quota gratuit, la RAM hôte et le conflit de dépendances empêchent un test responsable dans cette étape. Aucun classement Wan/SANA n'est revendiqué.
