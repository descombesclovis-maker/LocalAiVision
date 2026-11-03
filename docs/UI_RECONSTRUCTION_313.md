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

- [ ] Accueil Studio sans navigation ajoutée, deux cartes équilibrées.
- [ ] En-tête Web : menu gauche, retour Studio en texte, commandes techniques rangées.
- [ ] Deux choix de création, aucun bouton Nouveau projet ou Actualiser redondant.
- [ ] Rail transparent et onglet 🗒️ vers le CRM existant.
- [ ] Chat neutre et aucune ouverture automatique du questionnaire.
- [ ] Trois SVG de supports avec handlers et dimensions conservés.
- [ ] Action commerciale unique, dernier bouton de l’en-tête, liée au projet.
- [ ] Google officiel ; erreur visible sans clé ; fiche officielle sans modification interne.
- [ ] Action entreprise liée à la sélection courante, aucun résultat fictif.
- [ ] Import public Vision SVG centré, espace réservé inchangé.
- [ ] Suite Python, syntaxe JS, tests navigateur et captures aux six résolutions.
- [ ] Compilation Windows en PR, sans création de release.

## Limites de certification

Les captures ne démontrent pas une génération Codex/ComfyUI, un paiement, une
signature ou une publication. Leur validation nécessite les services configurés.
Les DPI Windows et WebView2 exigent une exécution Windows réelle. Aucun succès
ne sera attribué à ces parcours sur la seule base des tests structurels.
