# Build 316 — en-tête Web et livraison client

Branche : codex/studio-316-professional-overhaul — PR #65, brouillon.
Base examinée : 5a3c226 (les corrections Vision de 04a90d6 à be76123 sont préservées).

## Critères de recette

- Vision : retour Studio sans flèche, six chevrons cyan, alignement droit, clavier, historique accessible par le chat, rail conservé.
- Web : en-tête indépendant du découpage chat/aperçu, menu à gauche de la fenêtre, logo au-dessus du nom au centre, retour Studio à droite, contrôles existants et séparateur conservés.
- Livraison : bibliothèque de dossiers, devis librement éditable avant émission, paiements déclarés ou rapprochement Stripe en lecture seule, facture numérotée figée, avoir intégral, fiches techniques, contrôle du paquet et ZIP conditionné au règlement.
- Aucun moteur de génération, paramètre NSFW, déploiement, transfert, transaction, envoi client, release ou fusion n'est modifié/déclenché.

## Implémentation

Les routes visibles `/localaiweb/clients` et `/localaiweb/vente` ouvrent désormais Livraison client sur l'origine locale dédiée `ventes.localhost`. Les anciens registres et documents restent conservés ; les devis/factures antérieurs du projet sont consultables en lecture seule. Aucun Kanban ni pipeline commercial n'est ajouté.

Les nouvelles données sont stockées dans `localaiweb/deliveries/deliveries.sqlite`, séparément des sources, de l'ancien registre et des créations Vision. Un commit SQLite enregistre ensemble le numéro, le PDF, son instantané et l'événement. Une réception partielle sur un site déjà réalisé peut créer la facture totale avec mention du paiement reçu ; les réceptions suivantes conservent le PDF d'origine et actualisent le journal des règlements. L'avoir annule intégralement la facture sans la réécrire. Le devis émis est figé ; le brouillon permet d'ajouter/supprimer les lignes et de modifier les montants.

Les paiements manuels et remboursements sont explicitement des déclarations, sans vérification bancaire. Stripe : vérification serveur de la session, du projet, du devis, de l'intention de paiement et de l'absence de remboursement ; le mode test ne contribue jamais au montant reçu réel. Les sessions doivent fournir `client_reference_id=project_id`, `metadata.project_id` et `metadata.delivery_quote`. Aucun compte ni Checkout n'est créé automatiquement. Le serveur revérifie les règlements Stripe réels avant l'export.

L'inventaire exclut les fichiers privés, `.env*`, dumps/seed SQL, données tabulaires, bases locales, credentials, clés privées et dépendances ; les liens symboliques et secrets potentiels bloquent le paquet. Les scripts du site ne sont jamais exécutés pour préparer l'archive. Les migrations et fonctions existantes sont copiées après contrôle ; aucune base distante ou donnée utilisateur n'est exportée. Les dépendances restent décrites par les manifestes/lockfiles, à installer dans l'environnement du client.

Le paquet est lié à l'empreinte des sources et à la version du dossier. Toute modification impose une nouvelle préparation. Les validations de design, fonctions, droits et services sont des attestations explicites de l'opérateur, pas des preuves d'accès à des comptes distants. La livraison effectuée est une déclaration, sans envoi automatique.

## Cadre fiscal et services

Les identités réelles sont obligatoires. Aucun SIRET/TVA/statut n'est inventé. Le circuit de facture électronique via une plateforme agréée n'est pas implémenté ; l'interface et les PDF le précisent, avec les sources officielles :

- https://entreprendre.service-public.gouv.fr/vosdroits/F31808
- https://www.impots.gouv.fr/facturation-electronique-et-plateformes-agreees
- https://vercel.com/docs/projects/transferring-projects
- https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore

Génération des PDF gratuite en local avec ReportLab. Le prestataire d'encaissement conserve ses propres frais. Configuration manuelle requise : identités, fiscalité, compte bancaire, clé Stripe locale pour le rapprochement connecté, compte final du client, domaines et renouvellements, Auth/Storage/RLS, migrations, webhooks, procédure de transfert approuvée. Un export de données personnelles exige un autre parcours explicitement autorisé et sécurisé.

## Validation et reprise

392 tests Python réussis (2 ignorés selon plateforme), dont 16 scénarios dédiés dans `tests/test_client_delivery.py` ; 33 tests Node ciblés réussis. Test natif `scripts/smoke_delivery_native.py` : HTTP de l’EXE, SQLite, devis et facture PDF, paiement fictif déclaré et ZIP. Aucune transaction réelle. Recette navigateur : recette navigateur dédiée `scripts/qa_client_delivery.cjs` : en-tête sur trois tailles, devis PDF, réception partielle puis complète, facture, téléchargement du ZIP, persistance et isolation d'origine. Fixtures locales uniquement ; aucun paiement réel.

Recette Vision validée dans Windows : six chevrons cyan, clavier, alignement et réduction des animations. Les recettes navigateur Web/Livraison et la compilation de la dernière révision restent à examiner.

Chromium indisponible dans le conteneur : téléchargement renvoyant un contenu non ZIP. Les recettes réelles sont donc exécutées par GitHub Actions Windows. Attendre et examiner leurs résultats et captures avant validation visuelle finale. Compilation Windows native et EXE de cette révision : à récupérer après réussite de CI ; ne pas confondre avec les compilations précédentes.

En cas d'interruption : examiner la tête distante avant modification, reprendre le résultat du dernier run GitHub Actions associé au commit, corriger tout échec, inspecter les captures ordinateur/mobile et les PDF, récupérer l'archive bureau, vérifier EXE/manifestes/empreintes, puis fournir le paquet. Ne pas fusionner ni publier.
