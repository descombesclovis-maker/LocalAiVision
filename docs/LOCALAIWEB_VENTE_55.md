# LocalAiWeb · vendre et livrer un projet

Branche empilée sur la PR 53. Ouvrir un projet Pro, attendre la fin de sa génération puis choisir **Préparer l’appel et la vente**. Le chat, l’aperçu et l’édition restent dans l’éditeur. Le projet Libre conserve son parcours de publication indépendant.

## La feuille d’appel

Le premier écran et son PDF présentent la même feuille. Les repères distinguent les renseignements de la fiche publique, la date d’import dans le dossier, les éventuelles correspondances du registre français et les faits professionnels confirmés par le vendeur. Le vendeur peut actualiser le rapprochement au registre. Une identité ambiguë reste à confirmer. Le champ de site absent n’établit jamais l’absence d’un site.

L’ouverture, les questions métier, les pages à présenter et la conclusion reprennent les données de ce projet. Les exemples de liens internes pointent vers des fichiers effectivement présents. Un formulaire détecté nécessite encore un essai de réception. Une priorité rapportée par le client peut être ajoutée avec sa source et sa date, corrigée ou retirée. Au-delà de 90 jours, la feuille propose de la revalider. Le vendeur doit corriger une information devenue inexacte avant ce délai. Codex peut classer les pages existantes pour la démonstration. Sa réponse est validée comme une liste de chemins autorisés. Le texte libre du modèle ne devient pas une affirmation commerciale.

Le clic sur un lien téléphonique est manuel. Il nécessite un numéro professionnel vérifié par le vendeur. Une opposition supprime les rappels concernés et bloque la feuille d’appel et le nouvel envoi pour signature. Le registre et son journal sont privés. L’import d’une fiche ne constitue pas une autorisation de démarcher.

[Exemple PDF sur un commerce fictif](qa55/feuille-appel-exemple.pdf) · [Démonstration du parcours](qa55/parcours.webm) · [Captures navigateur](qa55)

## Prestataires et preuves

| Étape | Action et preuve |
|---|---|
| Site prêt | L’état de génération, l’aperçu construit et le contrôle qualité doivent être compatibles. Le fichier d’accueil initial ne déclenche pas la vente. |
| Proposition | Estimation des prestations depuis les fichiers, remise éditable, TVA issue des informations du vendeur, périmètre et coûts récurrents distincts. Le vendeur confirme le PDF numéroté. L’émission ne prouve pas son envoi. |
| Acceptation | Sur confirmation distincte, Dropbox Sign reçoit le PDF exact et le destinataire du devis. La demande réserve le numéro avant envoi. La vérification rapproche la référence, l’empreinte du PDF, le mode, la signature du destinataire et sa date de validité. |
| Règlement | Stripe Checkout propose le règlement intégral TTC du devis signé. La session conserve la même clé d’idempotence. Le client choisit de payer sur la page hébergée. Les paiements confirmés, en attente, échoués et les remboursements partiels ou complets sont rapprochés par webhook signé. Le retour du navigateur n’est pas une preuve de paiement. Les acomptes fractionnés ne sont pas gérés. |
| Domaine | Recherche publique de disponibilité et de prix d’enregistrement et de renouvellement en USD. Une acquisition exige un mandat local exact, une offre revalidée et un accord opérateur distinct. Aucun renouvellement automatique. Un ordre incertain reste réservé jusqu’au rapprochement, sans nouvelle commande. Un domaine déjà possédé conserve son parcours de rattachement. |
| Services | La lecture des fichiers signale formulaires, paiements et références à Supabase. Un site vitrine peut rester sans base de données. Les migrations existantes passent par une simulation CLI et une confirmation du même jeu de fichiers, pour le même projet lié. Les droits RLS et les parcours réels demandent un test sur l’environnement du client. |
| Publication | Le vendeur enregistre la recette, atteste le mandat puis confirme la publication. Le serveur exige une version revue, un accord et un règlement réels associés au devis retenu, un projet Vercel lié et des contrôles techniques réussis. |
| Remise | La vérification rapproche l’organisation, le déploiement Vercel de production, le domaine s’il est configuré et la réponse HTTPS du site. Le vendeur confirme la remise effective. Le CRM passe alors à « livré ». Le ZIP exporte le projet. Une facture seule n’entraîne plus ce changement de statut. |

## Activation sur Windows

Les clés et les coordonnées du titulaire restent sur le serveur. Configurer les variables dans l’environnement du processus LocalAI Studio, puis le redémarrer. Les secrets commerciaux sont retirés de l’environnement transmis aux sous-processus du serveur. Le PDF et l’interface commerciale locale utilisent `ventes.localhost` sur le même port. Cette origine refuse les aperçus de sites générés. Les confirmations financières nécessitent le poste local et un code opérateur d’au moins 16 caractères.

| Variable | Utilisation |
|---|---|
| `LOCALAI_SALES_MODE` | Mode test par défaut. La valeur explicite `live` utilise les prestataires réels. Utiliser des devis distincts entre test et production. |
| `LOCALAI_SALES_APPROVAL_CODE` | Code opérateur privé, distinct des clés des prestataires. |
| `DROPBOX_SIGN_API_KEY` | Compte autorisé pour l’envoi et la lecture des demandes de signature. Même une demande en mode test peut envoyer un courriel : toujours vérifier le destinataire. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Clé Stripe du mode choisi et secret de signature de l’endpoint. |
| `LOCALAI_CHECKOUT_RETURN_URL` | URL HTTPS de retour contrôlée par le vendeur. Elle ne modifie aucun statut. |
| `LOCALAI_REGISTRAR_TOKEN`, `LOCALAI_REGISTRAR_MANDATES` | Jeton Vercel à privilèges limités, répertoire privé de mandats situé hors des dossiers de projets. |
| `LOCALAI_VERCEL_READ_TOKEN` | Accès en lecture au projet, aux domaines et aux déploiements Vercel utilisés pour la remise. |

Stripe doit transmettre les événements bruts à `/api/web/sales/stripe/webhook`. Sous Stripe CLI en bac à sable, utiliser le transfert local vers `http://127.0.0.1:3000/api/web/sales/stripe/webhook` avec le secret de cette session CLI. Événements pris en charge : `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired` et `charge.refunded`. La production exige un relais HTTPS autorisé et maintenu qui transmet le corps et l’en-tête Stripe **intacts**. Aucun relais public n’est déployé par cette PR. Ne pas exposer les autres routes de l’application à Internet.

### Mandat d’acquisition

Un administrateur autorisé prépare hors de l’application un fichier privé nommé `<id-projet>.json` dans `LOCALAI_REGISTRAR_MANDATES`. Le client et le payeur doivent avoir approuvé les conditions exactes. Les jetons n’ont pas leur place dans ce fichier. L’opérateur voit l’offre puis confirme juste avant l’achat. Schéma attendu :

| Champs | Contrôle |
|---|---|
| `project`, `quote`, `customer_name` | Projet Pro, devis signé et réglé intégralement en production, raison sociale exacte du devis. |
| `domain`, `teamId`, `projectId` | Nom exact et projet/organisation identiques au lien Vercel local. |
| `price_usd`, `all_in_usd`, `renewal_usd`, `years` | Prix numériques, durée et renouvellement à l’identique de la réponse fraîche du registrar. Seuls les comptes dont le coût total vérifié est égal au prix attendu sont pris en charge. |
| `billing_verified`, `billing_evidence`, `holder_consented`, `autoRenew` | Les deux validations sont vraies, la référence de preuve est obligatoire, le renouvellement automatique est faux. La preuve fiscale est contrôlée par le responsable financier, pas calculée par LocalAiWeb. |
| `expires_at`, `contactInformation` | Échéance Unix dans les prochaines 24 heures et coordonnées légales du titulaire client, y compris les attributs exigés par son TLD. L’adresse électronique correspond au signataire. |

Si une réponse est perdue après réservation, vérifier la console du prestataire et utiliser la référence existante dans **Rapprocher une opération interrompue**. Une réponse incertaine ne vaut ni paiement, ni signature, ni domaine acheté.

## Recette et limites

- `python -m unittest discover -s tests -v`, `node --test tests/*.mjs`, vérification de syntaxe des scripts modifiés.
- `python scripts/review_sales_55.py` lance un serveur isolé et le scénario Edge/Chromium avec Playwright Core. Il exerce les routes réelles de sélection du prospect, du projet Pro, du suivi de génération, de la feuille d’appel, du CRM et du devis PDF, ainsi que le parcours Libre. La fiche de sélection et le générateur de fichiers sont des adaptateurs de test. Le scénario ajoute une priorité datée à la feuille et vérifie le PDF. Aucun accès au compte Google Maps ou à la session Codex du vendeur n’est revendiqué. Les captures couvrent 390 × 844, 1365 × 768, 1920 × 1080 et 3840 × 2160.
- Les tests des signatures, de Stripe, du registrar et des migrations utilisent des doubles de prestataire, sans dépense ni communication. La recherche publique Vercel a été interrogée sans jeton. Les opérations authentifiées en sandbox et en production nécessitent les comptes du vendeur et du client ; elles n’ont pas été exécutées.
- Les besoins en SMTP, réservation, administration, sauvegarde/restauration et maintenance dépendent du projet. Leur détection et la recette manuelle ne constituent pas une installation universelle. Aucun compte payant, campagne, restauration ou contrat de maintenance n’est créé automatiquement. Le ZIP et les PDF ne remplacent pas une plateforme agréée de facturation électronique. Le vendeur peut renseigner un coût interne HT pour obtenir une estimation de marge sur la création. Un export comptable JSON est disponible pour la facture. Il ne constitue pas un dépôt sur une plateforme agréée.

Références : [CNIL — prospection téléphonique](https://www.cnil.fr/fr/prospection-commerciale-par-telephone-hors-automate-dappel-quelles-sont-les-regles), [Service Public — démarchage](https://entreprendre.service-public.gouv.fr/actualites/A19003), [mentions obligatoires](https://entreprendre.service-public.gouv.fr/vosdroits/F37351), [facturation électronique](https://www.economie.gouv.fr/actualites/facturation-electronique-entre-entreprises-coup-denvoi-de-la-reforme), [Dropbox Sign](https://developers.hellosign.com/api/signature-request/send/), [Stripe Checkout](https://docs.stripe.com/api/checkout/sessions/create), [webhooks Stripe](https://docs.stripe.com/webhooks/signature), [Vercel Registrar](https://vercel.com/docs/domains/registrar-api), [Supabase CLI](https://supabase.com/docs/reference/cli/supabase-db-push).
