# Reconstruction de l’interface — contrat de recette

Base auditée : `main` a470952af01ec5fd972f5565ed03c62594b5584e (Build 312).
Branche : `codex/studio-313-complete-ui-reconstruction`. Aucune publication ni fusion autorisée.

## Audit et architecture

Les 261 décisions de `LOCALAI_STUDIO_FINAL_QCM_ACCEPTANCE_261.md` restent conservées.
Les nouvelles consignes remplacent les choix incompatibles : dock sur l’accueil,
questionnaire imposé, navigation opaque et accès commerciaux dupliqués.

| Parcours | Structure cible | Contrats conservés |
|---|---|---|
| Studio | Deux destinations, aucun dock | Routes Web et Vision |
| Projets Web | Menu technique, deux entrées Pro/Libre, bibliothèques | Identifiants, stockage, création, recherche et reprise |
| Éditeur | Discussion, aperçu, outils contextuels, vente à droite | Viewports, inspection, export, versions, moteur Codex |
| Carte | Carte Google et composant officiel Places, action séparée dessous | Jeton serveur de sélection et création Pro |
| Commerce | Onglet dédié vers le CRM existant, dossier par projet | Devis, signature, paiement, domaine, livraison |
| Vision publique | Commandes précises, import SVG, graisse modérée | Sélecteur réel, modèles, LoRA, bibliothèques |

Causes relevées : `studio-qcm-shell.js` injectait son dock sur toutes les pages ;
`studio-suite.css` ajoutait le cadre violet et son halo au compositeur ;
`studio-qcm-editor.js` remplaçait les supports par ▣/▯/▵ ;
`localaiweb.js.initialize()` imposait le questionnaire aux projets Pro sans aperçu ;
`localaiweb-google-map.js` conservait la fiche Google tout en ouvrant la fiche maison.
Les feuilles suite/polish ne seront plus chargées par les pages Web reconstruites.

## Acceptation avant codage

- [x] Accueil Studio sans navigation ajoutée, deux cartes équilibrées.
- [x] En-tête Web : menu gauche, retour Studio en texte, commandes techniques rangées.
- [x] Deux choix de création, aucun bouton Nouveau projet ou Actualiser redondant.
- [x] Rail transparent et onglet 🗒️ vers le CRM existant.
- [x] Chat neutre et aucune ouverture automatique du questionnaire.
- [x] Trois SVG de supports avec handlers et dimensions conservés (820 / 390 px).
- [x] Action commerciale unique, dernier bouton de l’en-tête, liée au projet.
- [x] Adaptateur Google officiel et erreur visible sans clé ; intégration Google en direct non certifiée.
- [x] Tests de sélection : réponses inversées, fermeture, mauvais identifiant et erreur du composant.
- [x] Import public Vision SVG centré ; exclusion CSS de l’espace réservé contrôlée.
- [x] Suite Python, syntaxe JS, tests navigateur et captures aux six résolutions.
- [x] Compilation Windows vérifiée sur le workflow 315 ; contrôles du dernier commit consultables dans la PR. Aucune release autorisée.

## Résultats reproductibles

Recette locale sur le véritable serveur HTTP, `LOCALVISIONAI_SKIP_SETUP=1` et un
répertoire de données temporaire distinct de tout stockage utilisateur.

| Vérification | Résultat local |
|---|---|
| Suite Python | 294 exécutés : 293 réussis, 1 réservé à Windows ignoré |
| Actions sur les prompts et qualité 3D | 6 tests Node réussis |
| JavaScript | Contrôle de syntaxe des scripts de l’application et de recette |
| Écrans comparés | Studio, projets Pro et Libre, éditeur, carte, CRM, vente, Vision, marques |
| Résolutions | 3840×2160, 2560×1440, 1920×1080, 1365×768, 1280×720, 390×844 |
| Captures | 54 avant + 54 après, plus détails de menu, commandes, import et aperçu réel |
| Géométrie | Aucun débordement horizontal ; cartes Studio alignées ; compositeur accessible ; SVG + centré à moins d’un pixel |
| Menu | Ouverture clavier, fermeture Échap et retour du focus |
| Libre | Création par le vrai formulaire, persistance, renommage et formats |
| Aperçu et export | Véritable HTML de recette, consultation des sources, liste des versions et ZIP téléchargé |
| Pro | Référence de lieu de test, attente du brief, vente sur l’origine dédiée avec le bon identifiant |
| CRM | Navigation vers la véritable page, ouverture de la fiche client |
| Vision | Sélecteur natif, chargement d’un PNG de recette, bascule I2V et centrage |
| Espace réservé | Exclusion de la nouvelle présentation via classe de session ; aucune donnée réservée utilisée |

Le site HTML de recette porte explicitement la mention « DONNÉES DE TEST » et
ne constitue pas un résultat de génération IA. Aucun commerce fictif n’est
affiché sur la carte. Les contrôles de versions vérifient leur consultation ;
la restauration destructive d’un projet utilisateur n’a pas été exercée.

Reproduction : `python -m unittest discover -s tests -v`,
`node --test tests/test_web_prompt_actions.mjs tests/test_3d_quality.mjs`,
puis `node scripts/qa_ui_313.cjs` avec Playwright et un navigateur installé.
Le script accepte `CHROMIUM_PATH` ou `UI_BROWSER_CHANNEL=msedge`.
Les workflows joignent captures, journaux, résultats JSON et vidéo comme artefacts.

## Conservation des fonctions et changements de parcours

Les modèles, workflows, serveurs de génération, routage LoRA, imports, données
existantes, sauvegardes et espaces réservés n’ont pas été remplacés.
Les routes Pro/Libre, API Codex, inspection, export, versions, CRM, devis,
signature, paiement, domaines et livraison conservent leurs contrôleurs.
Les commandes de connexion et de mise à jour restent dans les paramètres.
Les suggestions de prospection de l’annuaire indépendant restent accessibles
dans le menu Projets ; elles ne concurrencent plus les fiches Google sur la carte.

L’origine commerciale `ventes.localhost` autorise seulement trois assets
supplémentaires nommés pour la présentation commune. Les aperçus générés,
le service worker et les API de génération restent exclus de cette origine.
Les liens de navigation du dossier commercial reviennent explicitement sur
l’origine Studio ; ses autorisations financières restent inchangées.

### Google : composant officiel et données réutilisables

L’application intègre Maps JavaScript et `gmp-place-details` avec son contenu et
ses attributions officiels. Ce composant est fourni par Google ; il n’est pas
une reproduction de l’intégralité du site grand public maps.google.com.
Le bouton LocalAiWeb est un composant distinct sous la fiche, sans accès à son
DOM interne. La carte conserve les contrôles et la géographie Google ; seuls
les POI non professionnels sont masqués par les styles officiels disponibles.

Le clic crée un vrai dossier Pro associé au Place ID. Les coordonnées,
photos, horaires, avis et noms provenant de Places ne sont pas recopiés
durablement dans les fichiers du site ou le CRM. Le projet attend les faits
confirmés dans la conversation avant génération. L’annuaire indépendant
conserve son démarrage initial existant. Aucune migration des projets historiques.

Sources techniques consultées :
- [Places UI Kit — Place Details](https://developers.google.com/maps/documentation/javascript/places-ui-kit/place-details)
- [Politiques Places — stockage, identifiants, attributions et différences EEE](https://developers.google.com/maps/documentation/places/web-service/policies)

Clés navigateur et serveur, restrictions de clé, APIs autorisées, quotas et
facturation doivent être configurés pour le compte concerné. Aucune clé, offre
payante ni facturation n’a été ajoutée. Sans configuration, l’écran expose la
cause et une action Réessayer, sans imitation ni bascule implicite vers Leaflet.

## Limites de certification

Les captures ne démontrent pas une génération Codex/ComfyUI, un paiement, une
signature, un achat de domaine ou une publication. Ces parcours sont conservés
mais nécessitent leurs services configurés. Google en direct n’a pas été testé
sans clés ; les tests de l’adaptateur utilisent uniquement des identifiants
synthétiques, sans réseau et sans les présenter comme de vrais établissements.

Edge Windows fait l’objet d’un job séparé. Les DPI système à 125/150 %, la
validation graphique de la fenêtre native WebView2 et les performances RTX
3060 restent à vérifier sur l’installation équipée. Une compilation verte
et le smoke test de l’EXE ne suffisent pas à les certifier.

Cette PR reste en brouillon tant que ces critères externes ne sont pas vérifiés.
Elle ne doit être ni fusionnée ni publiée automatiquement.
