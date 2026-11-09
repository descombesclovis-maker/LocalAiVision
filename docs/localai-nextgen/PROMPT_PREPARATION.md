# V2-A — Compréhension et préparation locale des prompts

## Statut : expérimental, indépendant, désactivé par défaut

Package : `backend/lib/prompt_preparation/`.
Aucune route photo/vidéo/publicité/LocalAiWeb n'est branchée sur ce composant.
Le mode **ÉQUILIBRÉ est recommandé**, mais `enabled=False` reste la valeur par défaut.
Ni les modèles, ni les workflows, ni les paramètres de génération ne sont modifiés.

## Fonctionnement et contrat de fidélité

1. Conserver **exactement** le texte original (Unicode, espaces, retours de ligne compris).
2. Si activé et compatible avec la tâche, demander au LLM **local déjà configuré** une analyse JSON :
   sujet, caractéristiques, environnement, actions, cadrage, lumière, exigences obligatoires,
   interdictions, détails à conserver, style, relations spatiales, mouvements et identité.
3. Chaque élément doit citer un extrait exact et une phrase source. Les diagnostics exposent
   l'extrait, son contexte et ses offsets en caractères Unicode (pas en octets).
4. Refuser les extraits inventés, les réécritures libres, les clés inconnues/dupliquées et les
   tentatives d'ajouter un modèle, CFG, steps ou un prompt négatif.
5. Garder **tout l'original, une seule fois**, en tête du candidat. Ajouter uniquement des politiques
   fixes de fidélité/exécution propres à la tâche et au mode, jamais des détails visuels inventés.
   **Les extraits sélectionnés par le LLM restent dans les diagnostics, pas dans le texte générateur.**
   Même une citation exacte pourrait inverser une négation si elle perd le titre d'une liste ou une
   exception située dans une autre phrase. Une erreur de classification ne doit pas promouvoir
   volontairement une couleur interdite ou un mouvement non demandé.
6. Si le LLM signale des exigences incompatibles, conserver l'original et retourner
   `needs_clarification` / `safe_to_apply=False`. Ne pas choisir silencieusement une des exigences.

C'est une première préparation **volontairement conservatrice**, pas une réécriture créative libre
ni une traduction automatique. Le LLM est utilisé pour comprendre/classer et signaler les risques,
mais ne peut pas dicter de nouveaux attributs au générateur.

### Les trois modes

| Valeur API | Mode | Politique du candidat |
|---|---|---|
| `strict` | STRICT | Aucune addition créative, exigences explicites obligatoires. |
| `balanced` | ÉQUILIBRÉ | Clarté et cohérence d'exécution, jamais au détriment d'une exigence. |
| `creative` | CRÉATIF | Liberté esthétique seulement pour les détails non spécifiés. |

Les trois modes conservent toutes les instructions originales. Leur supériorité visuelle n'est
**pas démontrée** ; en particulier, aucune activation automatique du mode équilibré n'est faite.

## Adaptateurs et capacités réelles

- `photo` : apparence, couleurs, disposition, cadrage, éclairage et style explicitement demandés.
- `text-to-video` : ordre des actions et mouvements caméra demandés, sans travelling automatique.
- `image-to-video` : référence nécessaire, détails protégés et identité avant mouvements.
- `retouch` : référence nécessaire, seules les modifications demandées ; conservation du reste.
- `advertising` : produit, marque et libellés demandés, sans allégation commerciale inventée.

Les priorités de l'analyse locale sont adaptées à la tâche. Le résultat contient **uniquement du
texte + analyse + diagnostics**, jamais de paramètres d'inférence ni de champ `negative_prompt`.
Les interdictions utilisateur restent dans le texte source, y compris pour un moteur qui ignore
ou ne supporte pas de prompt négatif séparé.

Profils fournis, limités aux workflows intégrés actuels :

| Profil | Tâches | Ce qui n'est pas promis |
|---|---|---|
| `COMFY_IMAGE` | Photo, img2img/retouche, publicité ; référence acceptée | Masque/inpainting, identité verrouillée, contrôle spatial, texte lisible exact. |
| `COMFY_VIDEO` | T2V, I2V ; référence acceptée | Masque, identité verrouillée, commande caméra dédiée. |

Une tâche ou un masque explicitement non pris en charge donne `unsupported`, sans appel LLM.
Une retouche sans masque reste préparée textuellement, mais signale `unmasked_edit` : le workflow
img2img actuel ne peut pas garantir les pixels hors zone. Identité, relations spatiales et mouvements
font aussi l'objet d'avertissements lorsqu'ils ne reposent que sur un conditionnement textuel.
**Un workflow personnalisé doit fournir son propre `EngineCapabilities`**, pas hériter des profils intégrés.
`reference_provided` / `mask_provided` sont des métadonnées : le module ne lit ni ne transmet aucune image.

## API indépendante et diagnostic JSON

Depuis `backend`, dans un appel asynchrone :

```python
from lib.prompt_preparation import COMFY_IMAGE, compare_preparations, prepare_prompt

raw = "Une voiture noire à gauche d’un vélo rouge. Ne pas intervertir les couleurs."
legacy = raw + ", highly detailed, professional photography, sharp focus, premium quality"

# Défaut : original identique, aucun appel LLM ou lecture des réglages.
disabled = await prepare_prompt(raw)

# Opt-in explicite : configuration LLM locale existante, aucun nouveau modèle.
candidate = await prepare_prompt(raw, enabled=True, task="photo", mode="balanced", capabilities=COMFY_IMAGE)
print(candidate.to_dict())  # original, candidat, analyse sourcée, statut, avertissements

# Comparaison uniquement : fournir le VRAI texte de l'ancien chemin.
comparison = await compare_preparations(raw, legacy, enabled=True, task="photo", capabilities=COMFY_IMAGE)
assert comparison.selected_prompt == legacy
assert comparison.to_dict()["automatic_application"] is False
```

`safe_to_apply=True` signifie seulement que la **préparation textuelle** a été validée. Ce n'est
ni une garantie de conformité des pixels/frames, ni une autorisation de changer le chemin actif.
Le module n'appelle jamais un générateur, ne sauvegarde rien et ne consomme pas de crédit cloud.
L'affichage diagnostic V2-A est l'API Python/JSON et la CLI ; pas de nouvelle UI ou route HTTP.

### CLI de comparaison (lecture seule)

Fichiers UTF-8, depuis `backend` (aucun fichier n'est écrit par la CLI) :

```bash
.venv/Scripts/python.exe -m lib.prompt_preparation --prompt-file original.txt --legacy-file legacy.txt --task photo --profile comfy-image
```

Ajouter `--enable` pour autoriser l'analyse locale. Sans cela, aucun accès réseau/DB.
Par défaut, la configuration locale existante est lue une seule fois, paresseusement.
Pour utiliser explicitement un serveur/modèle **déjà installé** sans lecture Mongo :

```bash
.venv/Scripts/python.exe -m lib.prompt_preparation --prompt-file original.txt --legacy-file legacy.txt --task photo --profile comfy-image --enable --local-kind ollama --local-url http://127.0.0.1:11434 --local-model MODELE_DEJA_INSTALLE
```

Pour LM Studio : `--local-kind openai --local-url http://127.0.0.1:1234/v1` et son modèle déjà chargé.
Pour I2V/retouche, déclarer `--reference`. `--mask` n'invente pas de capacité et est refusé par les
profils ComfyUI intégrés. Les diagnostics sont imprimés en JSON sur stdout ; `--help` liste les options.

## Repli, confidentialité et limites

- Serveur absent, modèle absent, réponse mal formée, analyse non sourcée, erreur de configuration,
  timeout, prompt vide/trop long : **original exact**, `fallback`, motif dans `diagnostics`.
- Une requête locale d'analyse au maximum, pas de découverte/listage préalable, pas de retry,
  aucun téléchargement, pas de fallback cloud et aucun journal automatique des prompts.
- Endpoints HTTP(S) loopback exclusivement (`localhost`, IPv4 loopback, `::1`) ; proxy d'environnement,
  redirection, credentials, query/fragment, port invalide et URL distante/LAN sont refusés.
  Les autres alias réseau (dont IPv4-mapped IPv6) restent volontairement refusés ; repli sans envoi.
- Les endpoints compatibles locaux avec authentification ne sont pas couverts par cette V2-A.
- Requête HTTP : 35 s (connexion 3 s), délai global d'analyse : 45 s par défaut. Un chargement local
  plus lent peut provoquer le repli ; une annulation de l'appelant est propagée.
- Plafonds : 12 000 caractères, 128 phrases, réponse JSON 65 536 caractères ; pas de troncature du
  prompt original en cas de dépassement. Le découpage est conservateur, pas un parseur linguistique complet.
- Le LLM réel peut mal classer, omettre un détail ou ne pas détecter une contradiction. Les citations
  vérifiées ne sont pas une preuve de compréhension sémantique parfaite. Aucun score de qualité inventé.
- Ajouter des politiques textuelles peut ne pas aider certains encodeurs. Les profils ne tokenisent
  pas selon chaque modèle et ne garantissent ni texte lisible, ni comptage exact, ni fidélité d'identité.
- Les anciens prompts et négatifs fixes des workflows sont **inchangés**. Un conflit possible de ces
  anciens négatifs avec une demande de caméra fixe ou de typographie n'est pas corrigé dans V2-A.
- Aucune orchestration GPU supplémentaire. Avant une intégration active, comparer aussi le coût de
  chargement/VRAM du LLM local et de ComfyUI sur la RTX 3060 12 Go.

## Validation et prochaine mission

Corpus versionné : `backend/tests/fixtures/prompts_v2a.json` : photo détaillée, objets multicolores,
positions, mouvements séquencés/caméra fixe, chorégraphie caméra demandée, identité I2V, retouche
localisée, publicité/texte exact et contradictions de même portée. Les trois modes sont testés.

```bash
# Depuis backend ; pytest.ini conservé (2 workers configurés)
.venv/Scripts/python.exe -m pytest tests/test_prompt_preparation.py tests/test_prompt_local_provider.py -q
.venv/Scripts/python.exe -m pytest tests/ -q
```

Résultats V2-A : **175 tests ciblés**, **334 tests backend**, tous réussis. Réponses LLM, HTTP,
stockage et génération simulés. Les annotations du corpus sont des fixtures de test, **pas une
mesure de précision d'un LLM réel**. Aucun test GPU/visuel ni téléchargement de modèle effectué.

Prochaine mission recommandée : **V2-B — validation comparative locale** de l'analyse réelle puis
original/ancien/candidat sur RTX 3060 12 Go (fidélité, mouvements, identité, zones préservées,
latence/VRAM), à paramètres de génération contrôlés et sans activation par défaut avant décision.
L'implémentation s'arrête à V2-A.
