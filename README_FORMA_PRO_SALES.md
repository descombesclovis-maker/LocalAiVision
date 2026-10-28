# LocalAiWeb Pro — Carte, sites métier et espace commercial FORMA

## 1. Sélection d'une entreprise sur la carte

L'accueil LocalAiWeb garde sa création Pro depuis une carte ; l'éditeur garde
l'icône planète. La carte prend maintenant toute la surface utile. La recherche
facultative et le menu de **tous les corps de métier** sont placés **en haut** ;
les résultats et la fiche choisie se trouvent dans une **barre latérale à
droite**. En zoomant ou déplaçant la carte sur une ville (niveau >= 12), les
établissements de la zone se chargent après un délai anti-saturation. Un bouton
« Actualiser la zone » est également disponible. Les recherches sont
limitées géographiquement, mises en cache et tempérées pour respecter les
services communautaires OpenStreetMap. Une carte mondiale ne peut pas afficher
l'intégralité des entreprises de la planète simultanément ni garantir
l'exhaustivité.

En cliquant sur un établissement, le bouton **« Créer un site pour cette
entreprise »** apparaît. Il crée un projet Pro avec la dénomination, les
coordonnées professionnelles, l'activité et les données publiques disponibles,
puis ouvre l'éditeur et déclenche la première génération avec l'agent
Claude Code ou Codex connecté. Le projet demeure modifiable par le chat,
l'inspecteur visuel et les versions sauvegardées.

Les vrais logos, photographies et autres actifs de la marque sont employés
uniquement si leur origine et les droits sont vérifiés (par exemple fichiers
fournis par l'entreprise). Sinon, photos sous licence adaptée ou
illustrations IA signalées ; jamais de faux témoignage ou fausse image officielle.

## 2. Une architecture adaptée au métier

- Coiffeur/barbier : accueil et chemin court de rendez-vous
  (typiquement deux pages, sauf demande différente).
- Savonnerie et vendeur de produits : accueil, catalogue, fiches
  produits et informations/contact (typiquement quatre pages).
- Les autres métiers suivent le cahier des charges, pas un nombre fixe
  de pages. Des pages supplémentaires sont créées seulement pour des
  parcours et fonctions pertinents.

Le générateur doit distinguer une vraie intégration de réservation/paiement
d'un simple formulaire local. Aucune vente, réservation ou traitement
de paiement n'est réellement garanti sans serveur et fournisseur connecté.

## 3. Espace de vente FORMA

Dans l'éditeur, l'icône document ouvre l'espace **Vente & facturation**
du projet. Après génération, une estimation HT **non engageante** est calculée
à partir des fichiers existants. Le catalogue affiche des tarifs indicatifs
de prestations web 2026 et une **réduction de 30 % par fonctionnalité**.
L'émetteur peut retirer les lignes non livrées. Les coûts d'achat du domaine
et de l'hébergement ne sont pas compris.

**Important** : un prix estimatif ou une maquette ne donne pas le droit
d'adresser automatiquement une facture de vente à une entreprise prospectée.
La facture définitive PDF n'est créée que lorsque la prestation est
effectivement livrée, le client identifié, les mentions fiscales et
juridiques complètes, les prix vérifiés et l'émetteur donne son
consentement explicite. Elle reçoit alors un numéro FORMA annuel
chronologique et reste archivée localement.

Les informations personnelles de facturation restent dans le répertoire de
l'application sur la machine. Aucun email n'est envoyé automatiquement.

Mentions légales et exigences à vérifier :
- https://entreprendre.service-public.gouv.fr/vosdroits/F31808
- https://entreprendre.service-public.gouv.fr/vosdroits/F23208

En 2026, la réception de factures électroniques est obligatoire pour les
entreprises françaises assujetties ; l'émission structurée devient exigible
progressivement (PME/microentreprises au 1er septembre 2027). Un
simple PDF n'est pas une facture structurée transmise par plateforme agréée.
Avant d'utiliser le système pour facturer des clients, faire valider le
paramétrage fiscal et la conformité par un professionnel.

Comparatifs tarifaires 2026 utilisés comme références d'**ordre de grandeur**
pour établir le catalogue, pas comme tarif officiel du marché :
- https://onweb24.com/fr/guide/prix-site-internet
- https://dgtl.fr/tarif-creation-site-internet-professionnel/

## 4. Nom de domaine existant

Le panneau Domaine permet d'indiquer un **domaine acheté** et le **nom
du projet Vercel** déjà connecté. LocalAiWeb exécute la commande officielle
Vercel CLI pour l'attacher, puis affiche les informations de configuration
DNS à effectuer chez le registrar. Ce bouton n'achète pas de domaine, ne
modifie pas les enregistrements DNS à ton insu, et ne certifie pas un SSL
actif avant contrôle.

Source : https://vercel.com/docs/domains/set-up-custom-domain

Un projet Pro reste une maquette privée avant autorisation explicite de
représenter ou publier le site au nom de la société.

## 5. Vente rapide : contrôles non automatisables

Une checklist de validation accompagne la livraison : navigation, responsive,
parcours réels, autorisation et qualité des médias, mentions légales,
confidentialité, conformité facturation, domaine et HTTPS.

**Aucune garantie de vente ou de déploiement en moins de 30 minutes** : les
approbations, DNS, fourniture des visuels, systèmes de paiement, configuration
du domaine et obligations administratives peuvent demander davantage de temps.
La génération initiale et le chiffrage sont automatisés pour accélérer ce
travail, pas pour simuler sa complétude.
