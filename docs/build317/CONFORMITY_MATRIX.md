# Matrice de conformité — constat initial

HEAD examiné : `e86d228f246c1010fa792de095807b87458553f0`. QCM disponible : 261 décisions / 83 essentielles. Les décisions récentes priment : suppression de l’espace privé et moteur Web intégré prioritaire.

Suite de référence locale : 395 tests exécutés, 2 ignorés. Un test de logique ne prouve ni le résultat GPU ni une connexion à un prestataire. Aucun module n’est certifié commercialisable par sa seule présence.

| Univers | Fonction | État | Preuve / limite |
|---|---|---|---|
| Studio | Accueil et navigation | Partiellement fonctionnel | Pages et navigation testées au Build 316 ; consolidation et suppression des accès retirés à vérifier. |
| Studio | Marques et connexions | Partiellement fonctionnel | Bibliothèque persistante et sélection par projet ; Google DPAPI ajouté au HEAD ; accès réels non vérifiés. |
| Studio | Ressources, historique, sauvegardes | Partiellement fonctionnel | Journaux SQLite/écritures atomiques et tests existants ; récupération complète sur PC réel non vérifiée. |
| Studio | Mise à jour Windows | Partiellement fonctionnel | Recettes EXE précédentes disponibles ; recompilation Build 317 requise. |
| Vision | Chat | Partiellement fonctionnel | Backend llama.cpp existant ; pas de modèle local chargé dans cet environnement. |
| Vision | Photo / vidéo | Non testé | Workflows ComfyUI et provenance présents ; aucun rendu matériel ni benchmark RTX 3060 effectué ici. |
| Vision | Retouche | Partiellement fonctionnel | Masque et copie de variantes présents ; génératif réel dépend du workflow installé. |
| Vision | Publicités | Partiellement fonctionnel | Marque, compositions et variantes présentes ; rendus IA réels à qualifier. |
| Vision | LoRA / modèles | Partiellement fonctionnel | Catalogue et installation existants ; compatibilité modèle et licences à vérifier. |
| Vision | Galerie / historique / aperçu / export | Partiellement fonctionnel | Décodeurs et récupération testés ; confidentialité des données retirées à renforcer. |
| Vision | Ancien espace privé | Défectueux | Décision du 06/11 : retrait complet des accès et mécanismes de génération, sans effacement de données. |
| Web | Projets libres / entreprises | Partiellement fonctionnel | Projets séparés et persistants, architecture métier ; qualité des six projets réels non démontrée. |
| Web | Générateur intégré autonome | Défectueux | Génération locale ancienne présente, mais défaut Codex obligatoire et absence de pipeline intégré qualifié. |
| Web | Codex et Claude optionnels | Partiellement fonctionnel | Connecteurs présents ; choix et défauts à changer selon la consigne Build 317. |
| Web | Éditeur / aperçu / versions / ZIP | Partiellement fonctionnel | Vrais fichiers, isolation de l’aperçu, snapshots ; nouvelle recette Windows requise. |
| Web | Carte nationale Sirene | Absent | Recherche et fournisseurs existants ne constituent pas un stock national importé et indexé. |
| Web | Fiches et recommandations | Partiellement fonctionnel | Modules métier/prospects présents ; couverture et informations vérifiables à mesurer. |
| Web | Publication | Non testé | Intégrations CLI présentes ; pas de publication réelle autorisée pour cette mission. |
| Livraison | Devis / règlements / factures / avoirs / ZIP | Partiellement fonctionnel | Chaîne locale Build 316 testée ; aucun compte réel de paiement ou plateforme agréée raccordé ici. |
| Commercial | Installateur / désinstallation | Absent | EXE portable existant ; installateur professionnel et désinstallation préservant les données à construire. |
| Commercial | Licences et conformité | Non testé | Inventaire de redistribution et validation juridique complète absents ; pas de qualification commerciale possible actuellement. |

## Documents examinés et manquants

Disponibles : QCM V1 approuvé, contrat AGENTS, rapports 315/316, contrats de contenu/architecture/direction artistique, contrôle navigateur, sources et tests. Les échanges historiques complets et les guides juridiques de la bibliothèque ne sont pas des sources consultées à ce stade ; ne pas leur attribuer de conclusions. Les rapports historiques ne remplacent pas les tests sur la nouvelle branche.
