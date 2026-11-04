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
| D1 | P0 | Installation confondue avec qualification | setup, workflows | À faire | État vérifiable, benchmark RTX 3060 réel ouvert |
| D2 | P0 | 315.5 sans recompilation native, métadonnées anciennes | web, workflow Windows | 47 fichiers intégrés ; manifeste SHA-256 | Compilation native et retour arrière à vérifier |
| D3 | P1 | Fonctionnalités Web sans preuve métier | web_hybrid, browser_qa | À faire | Contrats, statuts et six briefs à tester réellement |
| D4 | P0 | Dates locales comparées à UTC | web_crm, web_sales_orders | À faire | Minuit, échéances et DST |
| D5 | P1 | Profils HunyuanImage non qualifiés | workflows | Non testé matériel | Ne pas appliquer un profil prétendument qualifié |
| D6 | P0 | Écritures et snapshots incomplets | web_builder | À faire | Atomicité, médias et récupération |
| D7 | P1 | Revue visuelle non bloquante | web_hybrid | À faire | Gate de livraison, preuves navigateur |
| D8 | P1 | CSS/DOM fragiles | web/*.css, *.js | À faire | Refactor seulement après captures comparables |
| D9 | P0 | Négation humaine interprétée comme sujet | app.js | À faire | Régression parser et images réelles ouvertes |
| D10 | P0 | PIN client insuffisant | server, private routes | À faire | Sessions/API/médias, génération privée inchangée |

## Dix opportunités suivies

| ID | Priorité | Chantier | État / dépendance vérifiable |
|---|---|---|---|
| O1 | P1 | Contrat de projet vérifiable | À faire |
| O2 | P1 | Profils GPU qualifiés | RTX 3060, modèles et ComfyUI nécessaires |
| O3 | P0/P1 | Journal durable et reprise | À faire ; reprise d'inférence non garantie |
| O4 | P2 | Identité de marque commune | À faire ; conserver catalogue actuel |
| O5 | P1 | Édition Web transactionnelle | À faire |
| O6 | P1 | Banc permanent de six briefs | À préparer ; Codex authentifié nécessaire pour générations |
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
