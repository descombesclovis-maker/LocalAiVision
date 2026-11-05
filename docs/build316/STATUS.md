# Build 316 — registre de réalisation

Mission en cours. Aucun résultat GPU, génération Codex, contrôle visuel ou Windows
n'est certifié sans son exécution réelle. Base : b2666902b008a82fc91c98839467782fba106e7c.

## Critères d'acceptation par lot

1. Intégration : conserver les 47 fichiers personnalisés octet pour octet ; archiver
   leurs SHA-256 ; conserver les ZIP 315.5 originaux pour retour arrière.
2. Temps métier : même fuseau explicite pour devis, échéances et signatures ;
   tester minuit et les deux transitions DST ; conserver les événements en UTC.
3. Prompts publics : les exclusions humaines ne deviennent pas des sujets ;
   conserver l'original et l'effectif ; aucune modification du parcours privé.
4. Stockage : remplacement atomique, interruption et restauration avec médias
   vérifiés ; compatibilité des anciens projets et snapshots.
5. Traçabilité : enregistrer les paramètres réellement soumis et distinguer toute
   mesure absente d'une valeur mesurée ; pas de télémétrie.
6. Qualification : installé ne signifie pas testé ; preuves attachées au matériel,
   au modèle et au workflow ; aucun benchmark simulé.
7. Livraison Web : compilation et revue navigateur requises ; absence de test
   explicite ; fonctionnalités commerciales déclarées avec preuves.
8. Confidentialité : tests HTTP d'accès direct, sessions et médias ; conserver le
   PIN existant et toutes les capacités de génération privées.
9. Windows : compilation native, sources/version vérifiées, icône, démarrage,
   mise à jour et SHA-256 ; aucune publication automatique.
10. Interface : préserver le rendu ; comparaison desktop/mobile avant refactor.

## Dix problèmes obligatoires

| ID | Priorité | Défaillance / cause | Fichiers | Correction / test / résultat | Impact et reste à faire |
|---|---|---|---|---|---|
| D1 | P0 | Installation confondue avec qualification | engine_qualification, benchmark_public_engine | États et reçus implémentés ; 2 tests passent ; inspection locale : indisponible | Intégration UI et benchmark RTX 3060 réel ouverts |
| D2 | P0 | 315.5 sans recompilation native, métadonnées anciennes | web, workflow Windows | 47 fichiers intégrés ; manifeste SHA-256 ; CI 41937343935 : build natif, icône, DLL, démarrage et mise à jour réussis | Nouveau build après les corrections suivantes requis ; QA visuelle initiale échoue sur attente de fond ancien |
| D3 | P1 | Fonctionnalités Web sans preuve métier | web_hybrid, browser_qa | À faire | Contrats, statuts et six briefs à tester réellement |
| D4 | P0 | Dates locales comparées à UTC | business_time, CRM, factures, pipeline, signatures | Corrigé ; 21 tests ciblés passent, dont minuit et DST | Zone IANA explicite ou fuseau OS ; anciens devis non réécrits |
| D5 | P1 | Profils HunyuanImage non qualifiés | workflows | Non testé matériel | Ne pas appliquer un profil prétendument qualifié |
| D6 | P0 | Écritures et snapshots incomplets | atomic_storage, web_builder | 7 tests passent : mort du processus, disque plein, médias, corruption, anciennes versions | Journal et récupération ; lecteurs externes hors verrou non transactionnels |
| D7 | P1 | Revue visuelle non bloquante | web_delivery, web_hybrid, server | Gate et empreinte des sources/médias ; 4 tests passent | Recette métier et revue artistique réelle encore nécessaires |
| D8 | P1 | CSS/DOM fragiles | web/*.css, *.js | À faire | Refactor seulement après captures comparables |
| D9 | P0 | Négation humaine interprétée comme sujet | app.js | 13 tests Node passent ; original/effectif distincts | Parseur ciblé FR/EN ; validation sur images encore ouverte |
| D10 | P0 | PIN client insuffisant | private_access, server, app.js | Session serveur HttpOnly, index privé durable, garde API/médias ; 3 tests passent | Ancien inventaire du navigateur à indexer au premier déverrouillage ; pas de chiffrement ; test PC ouvert |

## Dix opportunités suivies

| ID | Priorité | Chantier | État / dépendance vérifiable |
|---|---|---|---|
| O1 | P1 | Contrat de projet vérifiable | À faire |
| O2 | P1 | Profils GPU qualifiés | RTX 3060, modèles et ComfyUI nécessaires |
| O3 | P0/P1 | Journal durable et reprise | Réservations SQLite, IDs ComfyUI conservés, réconciliation après redémarrage, 4 tests passent ; aucune reprise d’inférence revendiquée |
| O4 | P2 | Identité de marque commune | À faire ; conserver catalogue actuel |
| O5 | P1 | Édition Web transactionnelle | À faire |
| O6 | P1 | Banc permanent de six briefs | Corpus préparé ; aucune génération réelle exécutée ; Codex authentifié requis |
| O7 | P1 | Critique visuelle et réparation | Navigateur et captures nécessaires |
| O8 | P1 | Campagnes éditables | À faire ; médias originaux à préserver |
| O9 | P1 | Orchestration ressources | À faire ; gains matériels à mesurer |
| O10 | P1 | Livraison professionnelle | À faire ; tests absents jamais validés |

## Limites observées au départ

Environnement Linux sans NVIDIA/ComfyUI ni Codex CLI authentifié. Aucun test sur
le PC de l'utilisateur. Le ZIP complet 315.5 et les sources Web originaux sont
conservés hors dépôt. L'intégration ne touche aucune donnée utilisateur.
Un ajout de navigateur temporaire avait été refusé par le contrôle automatique
pendant l'audit ; ne pas contourner cette restriction par une autre installation.

## Retour arrière et collaboration

Le commit d'intégration reste distinct des corrections. Pour examiner l'ancien
rendu : checkout du commit d'intégration dans un autre worktree. Pour retrouver
315.5 : archives originales, sans migration. Ne jamais copier des dossiers data
sur les sauvegardes personnelles. Une branche courte par modification manuelle,
commit et PR vers cette branche de travail ; mise à jour par merge/rebase local
après sauvegarde, jamais de force-push silencieux ni de travail concurrent sur
le même fichier. La PR reste en brouillon, sans fusion/release/déploiement.

## Résultats intermédiaires — 5 novembre 2026 UTC

- Référence 315.5 importée : 313 tests, 10 échecs DOM/identité obsolètes, 1 erreur
  de date, 1 ignoré. Les assertions obsolètes ont été adaptées aux personnalisations
  acceptées ; aucun bouton/fenêtre retiré n'a été réintroduit.
- Suite locale après lots : 335 tests Python, 1 ignoré Linux ; résultat final à
  reconfirmer après les dernières modifications. 13 tests Node des prompts passent.
- Provenance publique enregistrée : graph exact soumis (seeds compris), empreinte
  workflow/graph, original/effectif, modèles nommés, sorties et checksum à la
  récupération du média. Hashes modèles et mesures RAM/VRAM/inférence restent
  explicitement absents tant qu'ils ne sont pas mesurés. Détails UI à terminer.
- CI Windows 41937343935 : EXE natif produit, icône vérifiée, démarrage/DLL/mise à
  jour testés, ZIP/SHA produits, release ignorée. Ce run précède la gate et les
  sessions privées : son EXE n'est pas un livrable final de la mission.
- QA Chromium initiale : échec avant la capture menu car l'ancien test attend un
  fond uni alors que le 315.5 utilise un dégradé translucide. Le test est adapté au
  rendu personnalisé ; les autres contrôles restent requis.

## Confidentialité — portée et travail restant

Le PIN configuré est conservé, désormais vérifié côté serveur ; le navigateur
ne conserve pas le code. Les sessions sont HttpOnly/SameSite Strict, expirent et
peuvent être révoquées. Les nouvelles tâches privées, leur historique, previews
et fichiers connus sont contrôlés. Un journal écrit avant soumission ferme les
accès anonymes si le serveur s'arrête entre acceptation et indexation.

Les créations anciennes qui n'existent que dans localStorage ne peuvent pas être
classées depuis cet environnement : leur indexation se fait après déverrouillage
du navigateur contenant les sauvegardes d'origine. Avant cette indexation, ne pas
considérer les anciens chemins inconnus comme protégés. Les conversations restent
dans leur stockage d'origine ; pas de chiffrement ajouté, pas de protection contre
un autre processus du même compte Windows ni contre l'accès direct au ComfyUI.
Le PIN à quatre chiffres reste une protection locale limitée. La génération,
les modèles, LoRAs et workflows privés n'ont pas été modifiés.

Prochaine validation : CI Windows/Chromium/Edge après publication du lot, puis
captures du 315.5 personnalisé et comparaison. Poursuivre statuts métier/édition,
provenance détaillée, tâches durables et campagnes ; ne pas annoncer 100 %.

## Lot journal et concurrence

- Journal SQLite de préparation : réservation idempotente avant le worker,
  empreinte de requête sans prompt/média stocké, IDs ComfyUI persistés à chaque
  acceptation. Requête interrompue sans ID : état explicite, sans redémarrage
  automatique. IDs connus : surveillance de la tâche existante après redémarrage.
- 4 tests journal et 8 tests stockage passent. Une lecture depuis un deuxième
  processus attend désormais le verrou de l'écriture active avant récupération.
- CI 41938207085 : build natif, icône, démarrage et mise à jour réussis ; contrôle
  PIN serveur dans le navigateur réussi. La suite navigateur échoue ensuite sur
  l'iframe d'aperçu masquée après injection du site de recette. Diagnostics API et
  DOM ajoutés pour distinguer source absente et défaut frontend. La revue reste
  ouverte, pas de certification visuelle globale.

## Lot mémoire et recette explicite

- Snapshot/restauration/journal binaire traités par blocs. Mesure synthétique Linux
  sur 32 Mio : pic d'allocations Python 114 942 291 → 3 800 400 octets ; durée
  observée 1,5827 → 1,0913 s (un essai par variante, pas une garantie de vitesse).
  Reçu et hashes dans `storage-memory-benchmark.json`. Aucun gain GPU revendiqué.
- Contrat fonctionnel demandé à l'agent ; une déclaration « functional » de sa
  part ne vaut pas preuve. Cinq statuts réels et constat manuel de l'opérateur
  accessibles depuis le menu supplémentaire de l'éditeur, sans nouvelle fenêtre
  de configuration. Chaque constat est lié aux sources et médias de la version.
- 4 tests de recette passent ; un constat métier manuel ne peut pas valider des
  captures d'une ancienne version. Les tests métier automatiques sectoriels et
  les six générations réelles restent ouverts.
- CI 41939271699 (a9547e3) : tous jobs réussis, Chromium et Edge compris. Les lots
  suivants nécessitent leur propre exécution CI. Captures 315.5 personnalisées
  ajoutées à la prochaine CI pour une vraie comparaison de référence.

Suite locale après recette : **344 tests Python réussis, 1 ignoré sur Linux** ;
13 tests Node du parseur réussis, syntaxe des scripts touchés vérifiée.
La provenance publique est accessible depuis « Paramètres réels » sur les résultats
nouvellement tracés. Les mesures non disponibles restent nulles. La cookie privée
est une cookie de session de navigateur ; le serveur limite sa validité à 8 h.

## Reprise du 5 novembre 2026 — fiabilité, édition et validation technique

Point de départ vérifié : HEAD `9a2bbee9f9fcf667b8c5a158ef0ceb7321bda6a2`,
PR #65 toujours en brouillon, aucun changement local initial. CI 41942019758
réussie sur ce HEAD ; elle ne valide pas les corrections de ce nouveau lot.

Critères de ce lot : aucune tâche active oubliée après 1 000 demandes ; aucune
perte de reçus par écritures concurrentes ; un historique partiel ne vaut pas
succès ; les renommages/suppressions sont récupérables ; les fichiers privés
restent privés lors des soumissions concurrentes ; un média non vide n'est pas
certifié sans décodage. Aucun réglage de génération privé ou modèle modifié.

- **TERMINÉ ET TESTÉ localement — journal** : index SQLite des rendus, migration
  non destructive des anciens reçus, recherche des tâches actives sans limite
  des 1 000 dernières demandes, fusion sous transaction d'écriture, états finaux
  et dates de fin conservés. Tests de concurrence (20 rendus), anciennes données,
  requête obsolète et interruption WebSocket. Historique partiel non déclaré fini.
- **TERMINÉ ET TESTÉ localement — édition** : renommage et suppression dans le
  journal transactionnel existant ; arrêt réel d'un processus pendant renommage
  puis récupération ; suppression annulée si le commit disque échoue ; refus du
  renommage d'un secret en fichier public. Un remplacement sans fichier texte
  admissible ne peut plus effacer le site. Copies de médias toujours par blocs.
- **TERMINÉ ET TESTÉ localement — confidentialité** : marqueur durable distinct
  par soumission privée. La fin d'un worker ne supprime pas l'incertitude d'un
  autre ; anciens marqueurs interrompus conservés ; tiroir anonyme fermé pendant
  cette incertitude. PIN, modèles, workflows et politiques inchangés.
- **IMPLÉMENTÉ, VALIDATION MATÉRIELLE RESTANTE — médias publics** : le benchmark
  décode réellement images (Pillow) et vidéos (FFprobe + FFmpeg existants) ; outils
  absents, format inconnu, fichier vide/corrompu : validation non accordée. Reçus
  techniques détaillés, qualité artistique toujours `not_reviewed`. Tests exécutés
  sur des fichiers synthétiques, pas sur des sorties IA. Pas de téléchargement.
- Validation locale : **362 tests Python exécutés : 361 réussis, 1 ignoré Linux** ;
  **13 tests Node réussis** ; `git diff --check` réussi. Aucun JS navigateur modifié.
- Inspection Hunyuan T2V sans rendu : **indisponible**, connexion ComfyUI locale
  absente. Aucune génération ni mesure de vitesse GPU exécutée. NVIDIA et Codex
  CLI absents. Pas de navigateur local installé ; captures et QA Windows à vérifier
  sur la nouvelle CI. Aucun score artistique ou « 10/10 » attribué sans observation.

Prochaine action exacte : examiner la nouvelle CI de cette PR (EXE natif,
Chromium/Edge, preuves bureau/mobile), corriger ses échecs éventuels, puis poursuivre
D1/D3/O1/O5/O8 : qualification visible, contrats métier, édition et campagnes.
Les générations réelles des six briefs et la qualification RTX 3060 restent
bloquées par les moteurs/accès absents, et ne sont pas remplacées par des fixtures.
Voir `FINAL_REPORT.md` pour la portée et les validations restantes.
