# Finalisation du 3 novembre 2026

Branche : `codex/studio-297-sales-autopilot`, empilée sur la PR #53 au commit `78936c6`. Base examinée : `75ad6cf`. Aucun modèle, sauvegarde ou espace NSFW modifié. Aucune fusion, release, communication client, transaction, commande de domaine ou migration distante.

## Corrections et critères vérifiés

- Une demande Dropbox Sign conserve ses états envoyé, en attente, refusé, demande expirée chez le fournisseur, devis expiré, erreur fournisseur et accord vérifié dans SQLite. Historique consultable et date de dernière vérification affichée. Un refus, un délai réseau ou un PDF différent ne crée aucun accord. « Devis expiré » est une échéance locale distincte du statut fournisseur `expired` (référence officielle : https://developers.hellosign.com/api/manual-reference-pages/expiration).
- Les paiements échoués ne peuvent pas devenir payés à partir d'un événement d'échec incohérent. Montants de remboursement entiers, bornés, cumulatifs et non régressifs ; intention de paiement stable ; événements refusés annulés atomiquement.
- La remise Pro exige le règlement non remboursé du devis lié à la publication. Un autre devis payé ne le remplace pas. Un remboursement reste visible même après une publication.
- Les API contrôlent l'origine complète, port et protocole compris. La recette hostile comprend lectures CRM/projet/facture, accès parent, lectures d'autres projets, écritures avec prévol CORS et écritures simples sans prévol. Inspecteur réel conservé.
- Le mandat par défaut est relu depuis son emplacement privé après redémarrage, sans dépendre d'une variable en mémoire. Aucun achat dans ce test.
- Le premier workflow Windows de cette passe a révélé une écriture du mandat dans l'encodage Windows par défaut. Les noms accentués échouaient à la relecture UTF-8. L'écriture et la lecture utilisent désormais explicitement UTF-8 ; le test du mandat contient un nom accentué.
- Accroches complémentaires raccourcies, questions métier naturelles, sources et correction manuelle conservées. Contrôles de l'écran accord/paiement harmonisés, champs lisibles sur mobile.
- Réglages LoRA publics adaptés aux petits écrans : grille pouvant rétrécir, champs bornés, commandes repliables. Les règles excluent explicitement le mode NSFW ; le scénario supplémentaire vérifie aussi les contrôles coupés par un conteneur.
- Version source alignée sur `3.1.0`. Les métadonnées Windows restent écrites par le workflow. ZIP contrôlé pour les trois fichiers requis, contenus non vides et en-tête MZ de l'EXE. Empreinte SHA-256 désormais jointe à l'artefact de PR.
- Le parcours Windows Edge du Studio est aussi exécuté sur la branche commerciale, après inclusion des changements de la PR #53. Release toujours limitée à `main`.

## Vérifications locales

- Python : 284 tests exécutés, **283 réussis, 1 ignoré** (PowerShell Windows). Journal : `python-tests.log`.
- JavaScript : 45 fichiers vérifiés par `node --check`, aucun échec. 9 tests/sous-programmes Node réussis (qualité adaptative, actions de prompts, routage d'intention, masque et sélection de workflow).
- Chromium Linux 153 : parcours Pro/Libre, génération par adaptateur déterministe, suggestion de vente, aperçu hostile, inspecteur, feuille sourcée/PDF, rappel, devis avant publication, signature simulée envoyée → attente → refus, puis rechargement du dossier sans accord. Le refus est conservé et consultable.
- Navigateur : écrans commerciaux aux formats 390×844, 1365×768, 1920×1080, 3840×2160 ; vérification de débordement. Accord/paiement contrôlé séparément en mobile.
- Studio : accueil aux cinq dimensions, animation active/arrêtée, préférence persistante, commandes Vision/I2V/fichier, navigation clavier, filtres Leaflet avec fiches contrôlées, fiche mobile/zoom et contrat de limite des POI Google. Trace dans `browser-report.json`. Cadence Linux sans GPU : environ 35,6 rappels/s en UHD ; aucune promesse de performance sur RTX 3060.
- Inspection visuelle des captures mobile et desktop, dont accueil UHD et nouvel écran accord/paiement. Scénario reproductible `scripts/review_studio_extra.cjs` : contrôle complémentaire des projets, CRM, marques, réglages LoRA et bibliothèque publique vide aux quatre dimensions ; ce contrôle ne certifie pas tous les contenus possibles de ces écrans.

## Matrice de validation

| Fonctionnalité | État | Test effectué | Résultat | Configuration nécessaire | Problème restant |
|---|---|---|---|---|---|
| Accueil/navigation/Studio UHD | Vérifié en navigateur Linux | Scénario #54, 5 dimensions, animation et arrêt | Réussi | Windows Edge en CI | WebView2 natif/DPI réel et GPU utilisateur à vérifier |
| Vision, pièces jointes, modes | Interface vérifiée | Scénario #54 et tests média | Réussi sans génération GPU | ComfyUI, modèles, RTX 3060 | Qualité/vitesse photo et vidéo non mesurées ici |
| Carte et filtre | Leaflet/contrat vérifiés | Fiches déterministes, compteur, fiche et zoom mobile | Réussi | Clés Google Maps/Places réelles | Google authentifié et données réelles non certifiés |
| Génération Web | Parcours applicatif vérifié | Adaptateur déterministe et tests pipeline | Réussi | Codex CLI authentifié sur Windows | Pas de génération de bout en bout avec compte utilisateur |
| Projets/éditeur/inspecteur | Vérifié | Pro/Libre, reprise, sélection réelle | Réussi | Aucune pour le test local | Validation visuelle exhaustive de toutes bibliothèques/paramètres non revendiquée |
| Aperçus et CRM privé | Sécurité vérifiée pour scénarios testés | Script hostile, HTTP 403, origine/port, accès interprojets | Réussi | Origines locales du logiciel | Ce contrôle n'est pas une certification de sécurité exhaustive |
| Appels/feuille/sources/opposition | Vérifié localement | Plusieurs prospects, sources datées, correction, rappel, PDF, opposition | Réussi | Coordonnées professionnelles vérifiées | Aucun appel réel effectué |
| Devis/facture | Vérifié localement | PDF, lien devis, montants, numérotation et répétition | Réussi | Identités réelles, TVA et conditions vérifiées | Facturation électronique structurée externe non fournie |
| Dropbox Sign | Code et scénario simulé vérifiés | Identité/PDF/mode/dates, refus/attente/expiration locale, historique/reprise | Réussi avec doubles uniquement | DROPBOX_SIGN_API_KEY et destinataire de test autorisé | Aucun envoi ou test sandbox authentifié |
| Stripe | Code vérifié par simulation | HMAC, montant/devise, répétition, ordre, échec, remboursement et persistance SQLite | Réussi avec doubles uniquement | STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, URL HTTPS de retour, relais webhook autorisé | Aucun Checkout sandbox ni webhook fournisseur réel |
| Domaine/mandat | Code vérifié par simulation | Coût exact, changement de prix, paiement, titulaire, ordre incertain, reprise mandat | Réussi avec doubles uniquement | Jeton registrar, projet client lié, accord financier exact, taxes vérifiées | Aucun domaine acheté ; taxes supplémentaires bloquées ; disponibilité fournisseur non revalidée pendant cette passe |
| Vercel/DNS/HTTPS/livraison | Contrôles et garde-fous testés | Refus réseau privé, devis publié exact, contrôles de liaison | Réussi pour scénarios locaux | Projet Vercel client, jeton lecture, domaine et DNS | Aucun déploiement client réel ni propagation DNS observée |
| Supabase | Préparation testée | Même référence, empreinte SQL immuable, simulation CLI | Réussi avec doubles | CLI et compte autorisé, projet client lié | RLS effectif, restauration et migrations distantes non testés |
| SMTP/formulaires/réservation/e-commerce/auth | Incomplet selon site | Détection et recette guidée seulement | Pas de validation externe | Fournisseurs et besoins propres à chaque client | Provisionnement universel et tests métier réels non implémentés |
| Sauvegarde/monitoring/SEO/performance | Partiel | Tests existants, contrôles techniques et recette manuelle | Ne vaut pas activation externe | Cible et services du client | Restauration réelle, alertes et mesures du site final à réaliser |
| EXE Windows/mise à jour | À vérifier sur le nouveau commit | Workflows réels déclenchés à la mise à jour de la PR | Voir résultats Actions liés dans la PR | Runner Windows | Ne pas assimiler les anciens builds à ce nouveau code |

## Ordre de fusion préparé

La branche commerciale contient `78936c6` ; la PR #53 précède #56. À autorisation : fusionner #53, puis cibler `main` avec #56 et recontrôler la comparaison et les workflows. Ne rien fusionner automatiquement. Garder les releases précédentes pour retour arrière. Les scripts de mise à jour sont couverts par les tests existants et le workflow Windows ; aucun binaire officiel remplacé.

## Activation et verdict

Configuration détaillée et procédure de webhook : `../LOCALAIWEB_VENTE_55.md`. Les secrets commerciaux ne sont pas présents dans cet environnement. Les connexions éventuelles de ChatGPT ne constituent pas les identifiants du serveur Windows de l'utilisateur.

Le code local est candidat aux essais, sous réserve du nouveau build Windows. **Utilisation commerciale réelle non validée** : aucun test fournisseur authentifié, domaine/DNS/HTTPS client ni restauration n'a été exécuté. Le studio média demande toujours un essai sur la RTX 3060 12 Go. Les limites de services ci-dessus sont des travaux restants, pas seulement des clés manquantes.
