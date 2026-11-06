# Build 317 — reprise

HEAD de départ : `e86d228f246c1010fa792de095807b87458553f0`. Branche : `codex/studio-317-commercial-ready`.

Réalisé : examen du HEAD, matrice initiale fondée sur les sources, récupération du QCM 261/83, suite de référence 395 tests / 2 ignorés.

En cours : lot 1, retrait des accès et génération privés sans effacer les données ; extraction d’un garde de compatibilité sans session ni déverrouillage.

Prochaines opérations : valider les anciennes données et accès directs ; recetter les interfaces bureau/mobile ; implémenter le générateur intégré, puis le stock Sirene. Mettre à jour ce fichier après chaque commit significatif.

Dernier commit : consulter `git log -1` (le hash du commit contenant ce fichier n’est pas auto-référencé). PR brouillon à créer après le premier commit. Aucun modèle GPU, rendu, compte connecté, import national ni conformité commerciale validé.

## Point de contrôle — retrait de l’espace réservé

Implémenté : suppression des entrées et panneaux HTML, handlers et modules exclusifs ; routes retirées HTTP 410 ; index d’accès indépendant, exclusion des anciennes conversations des listes publiques, rejet des anciens profils avant lancement du moteur, sauvegarde hors ligne non destructive documentée. Tous les médias personnels restent en place.

Validation : 393 tests Python exécutés, succès, 2 ignorés (baseline 395 ; tests de l’ancien déverrouillage remplacés par des régressions du retrait). Test DOM jsdom : aucune exception pour les scripts Vision chargés, aucune entrée réservée, conversation historique inchangée et non affichée. Syntaxe JS vérifiée. Chromium présent mais lancement refusé par le système (`socket() Operation not permitted`) : aucune capture ni recette visuelle desktop/mobile validée ici. Windows pas encore compilé à ce point.

Étape suivante exacte : modifier le routage Web (projets existants et nouveaux, lancement direct et différé, sélection et statut UI) pour rendre le moteur local explicite et ne jamais télécharger implicitement de modèle. Ensuite vérifier génération réelle si un modèle est installé, puis développer l’import Sirene.

## Point de contrôle — moteur local prioritaire

Routage direct et différé, statut, sélection du moteur, valeur par défaut des projets et affichages de progression mis à jour. Connecteur local aux modèles déjà installés dans llama.cpp ou Ollama ; aucune installation implicite. Plan multi-pages et direction artistique appliqués aussi à la génération locale. Tests de confidentialité conservés ; recettes navigateur historiques adaptées au retrait demandé, sans supprimer leurs autres assertions.

398 tests Python réussis, 2 ignorés. Syntaxe des scripts touchés vérifiée ; test DOM toujours réussi. Modèle local réellement absent ici : première génération réelle, six sites métiers et benchmarks RTX 3060 restent non testés. Voir `LOCAL_ENGINE.md`.

GitHub Actions 475 du premier point de contrôle : compilation native Windows et smoke tests EXE réussis ; recette visuelle échouée car elle cherchait encore l’entrée retirée. Assertion corrigée pour cinq modes publics dans ce lot ; nouveau passage nécessaire. Aucun EXE déclaré commercialisable.

Étape suivante exacte : import Sirene réel avec identification SIRET, diffusion totale uniquement, stockage SQLite spatial, statistiques et requêtes bornées au viewport. Puis recette visuelle Windows et téléchargement de l’EXE du dernier commit validé.
