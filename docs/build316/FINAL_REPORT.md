# Build 316 — bilan de reprise, livraison encore en cours

**Statut : EN COURS.** L'implémentation globale n'est pas terminée. Les corrections
ci-dessous sont testées localement ; ni la qualité artistique, ni les moteurs IA,
ni les performances RTX 3060 ne sont certifiés. Le point de départ de cette reprise
est `9a2bbee`, PR #65 en brouillon. Aucune fusion, release ou publication.

## Corrections de cette reprise

1. Reprise de tous les rendus actifs, même antérieurs aux 1 000 dernières demandes.
2. Conservation des identifiants et des fins de rendu sous écritures concurrentes.
3. Persistance des interruptions WebSocket ; historique incomplet jamais transformé
   en succès. Aucune inférence relancée automatiquement après interruption.
4. Renommages et suppressions récupérables après interruption, avec snapshots.
5. Un fichier secret ne peut pas être renommé en ressource publique par l'éditeur.
6. Un remplacement composé uniquement de formats non modifiables ne vide plus le site.
7. Marqueur privé indépendant pour chaque soumission concurrente ; anciens marqueurs
   conservés jusqu'à résolution explicite, sans modification des politiques privées.
8. États de rendu finaux stables malgré les événements tardifs ; attente de la
   fin ComfyUI avant ajout des sorties à la bibliothèque.
9. Suivi Web par phases réelles, retrait des pourcentages fixes ; messages lisibles
   avec de vrais retours à la ligne.
10. Rejet des dossiers traités comme fichiers avant journalisation, pour préserver
    la réouverture du stockage après une requête invalide.
11. Décodage technique des sorties du benchmark public, au lieu du seul contrôle
   « fichier non vide ». L'absence de décodeur laisse la validation non accordée.

Fichiers principaux : `local_app/media_journal.py`, `private_access.py`, `server.py`,
`web_builder.py`, `media_validation.py`, `scripts/benchmark_public_engine.py`.
Tests ciblés dans `tests/test_media_journal.py`, `test_private_access.py`,
`test_transactional_projects.py` et `test_media_validation.py`.

## Preuves et limites

- Python : 364 tests exécutés, 363 réussis, 1 ignoré sous Linux.
- Node : 17 tests réussis (prompts, suivi Web, messages et fin réelle des médias).
- Renommage interrompu : vrai processus tué après copie du nouveau fichier,
  récupération de l'original sans doublon à la réouverture.
- Concurrence : 20 rendus acceptés puis terminés sur plusieurs connexions SQLite.
- Médias : PNG et petit MP4 synthétiques réellement décodés, corruption rejetée.
  Ce sont des tests de décodeur, pas des preuves de génération IA.
- Inspection Hunyuan T2V : ComfyUI indisponible, aucun rendu soumis.
- Les tests HTTP privés existants et nouveaux tests de marqueurs passent.
- Aucun benchmark GPU, temps d'inférence, gain VRAM ou note visuelle annoncé.

## Écart avec le Build 315.5

Les 47 fichiers personnalisés ont déjà été intégrés et documentés par les lots
précédents. Cette reprise préserve les logos, les styles et les animations ; elle corrige
le suivi textuel des générations et masque sa barre de pourcentage non mesurable.
Elle renforce les mécanismes serveur de conservation et l'éditeur. Les médias et
les données utilisateurs n'ont pas été importés dans l'environnement de travail.
Le manifeste d'import reste la preuve de la référence 315.5, pas une promesse que
les fichiers de code corrigés ont conservé leurs anciens octets.

## Travaux toujours ouverts

| Domaine | État exact |
|---|---|
| Fiabilité, stockage, confidentialité | Corrections testées ; validation dans l'EXE Windows requise |
| Photo HunyuanImage 2.1 | Décodage du benchmark prêt ; rendu, anatomie et texture non qualifiés |
| Vidéo HunyuanVideo 1.5 | Reprise améliorée ; T2V/I2V, continuité, storyboard et durées à qualifier réellement |
| RTX 3060 12 Go | Matériel absent ; cible 10 s en moins de 5 min non mesurée |
| LocalAiWeb | Correctifs transactionnels testés ; six briefs, édition réelle et recette métier encore ouverts |
| Carte | Pas de nouvelle collecte ni de qualification des milliers d'établissements dans ce lot |
| Publicité | Campagnes éditables et fidélité visuelle encore à compléter/valider |
| Interface | Préservée ; revue artistique et captures de la nouvelle CI requises |
| Windows | Run 42031666050 : EXE, icône, démarrage et mise à jour réussis sur ef37888 ; dernier garde-fou dossier à recompiler |

## Validation sur le PC cible

Suivre `VALIDATION_PROTOCOL.md` avec ComfyUI et modèles existants. Exécuter les
benchmarks publics un par un, sur les trois seeds, en conservant les reçus et
originaux. Utiliser un FFmpeg/FFprobe déjà disponible pour le décodage des vidéos ;
sans lui, le benchmark ne certifie plus une vidéo seulement parce qu'elle existe.
Ne pas modifier un profil qualité sur la seule base des tests synthétiques.

Tester les reprises après fermeture, les exports/restaurations et les écrans
390/820/1440 sur une copie des données. Vérifier l'absence de fuite des médias
privés. Les anciens médias conservés uniquement dans le navigateur doivent encore
être indexés après déverrouillage sur leur navigateur d'origine.

Les six briefs Web exigent un Codex CLI authentifié. Vérifier les formulaires,
réservations et paniers sur des backends de test réellement configurés ; aucun
paiement réel ni publication autorisés dans cette mission.

Ce bilan sera actualisé avec les nouveaux commits et les résultats CI. Il ne
constitue pas un certificat de finalisation du Build 316.
