# LocalAI Studio — feuille de route maîtresse (Build 294 et suivants)
Date : 2 novembre 2026. Base : Build 293 publié ; aucun projet, moteur ni fichier de sauvegarde supprimé.

## Cap permanent
LocalAI Studio = atelier professionnel tout-en-un, regroupant LocalAiWeb, LocalAiVision et l'accompagnement commercial. Objectif : **un brief → une réalisation vérifiable → des variantes → une validation → une livraison**, avec très peu de manipulations techniques. Une interface spectaculaire et maîtrisée ne doit jamais prendre le pas sur les résultats, la stabilité ou les performances RTX 3060 12 Go.

**Règle des pourcentages :** l'aboutissement ne devient 100 % qu'après un scénario métier Windows réel, tests fonctionnels, sauvegardes, performances et validation visuelle. CI verte ≠ rendu de qualité garanti.

## Cycle 294 — Personnalisation complète de l'interface
- [x] Ajouter un questionnaire à choix multiples de 46 questions avec catégories Architecture, Direction artistique, Animations, Expérience.
- [x] Aperçu immédiat et persistance locale indépendamment des sauvegardes/projets.
- [x] Export/import JSON des choix, réinitialisation, réglages par catégorie, prise en compte de reduced-motion.
- [x] Contrôler les positions des cartes/boutons/logos, couleurs, typographies, ambiances, effets et rythmes de mouvement.
- [ ] Étendre la configuration aux sous-univers LocalAiWeb, LocalAiVision, carte, menu et éditeur de sites sans déplacer les commandes critiques.
- [ ] Vérifier visuellement au moins quatre profils sur Windows (compact, cinématique, minimal, mobile) et réparer les collisions.
- [ ] Ajouter prévisualisation des réglages de chaque bouton avec glisser-déposer, grilles d'alignement et annulation.

## Cycle 295 — LocalAI Intelligence (orchestration d'agents)
- [ ] Orchestrateur de tâches durable, états structurés et événements, reprise après redémarrage.
- [ ] Directeur artistique, architecte des pages, Codex développeur, expert interactions/3D, inspecteur navigateur, correcteur ciblé, contrôleur final.
- [ ] Code compilé et testable, aucune page décorative présentée comme fonctionnelle.
- [ ] Playwright toujours disponible ou défaut explicitement signalé ; tests responsive, navigation, interactions, accessibilité et performances.
- [ ] Captures comparées au brief, rapport de défauts précis et cycles de correction bornés.
- [ ] Bibliothèque de composants originaux par métier ; pas d'imitation de modèles ou de sites propriétaires.

## Cycle 296 — Vision Engine : routage de modèles intelligents
- [ ] Inventaire des moteurs réellement présents (taille, VRAM, licence, nœuds ComfyUI, disponibilité).
- [ ] Comparaison sur RTX 3060 12 Go : HunyuanVideo 1.5 T2V/I2V, Wan 2.1/2.2 selon quantification, Z-Image, FLUX.2 Klein, HunyuanImage 2.1.
- [ ] Gestion des LoRA : compatibilité réelle par moteur, catalogue, poids, intensité et validations visuelles.
- [ ] Gestion des licences, en particulier vérification du droit de distribution/usage commercial en France avant recommandation d'un modèle.
- [ ] Profils de rendu photo, retouche, publicité, vidéo, espaces réservés aux adultes autorisés ; aucun réglage affiché sans effet vérifié sur le workflow.
- [ ] Choix automatique du modèle, du quantifié, de l'offload VRAM et du ratio selon la tâche ; contrôle manuel toujours possible.
- [ ] Tests visuels d'une galerie étalon : visages, mains, produits, textures, éclairages, photoréalisme, stabilité temporelle.
- [ ] Contrôle qualité post-rendu, upscaling par tuiles, corrections ciblées et comparaison avant/après.

## Cycle 297 — LocalAI Cinema
- [ ] Décomposer un brief en storyboard et plans courts adaptés à la mémoire vidéo disponible.
- [ ] Timeline d'édition réelle, découpage, transitions, images de référence, continuité du personnage/produit.
- [ ] Caméra virtuelle avec mouvements contrôlables, interpolation, stabilization, montage et son lorsque disponible.
- [ ] Rendus par plans annulables/reprenables, progression véritable, historique des variantes, export aux bons formats.
- [ ] Benchmarks 5/10/20 secondes, VRAM, durée réelle et qualité subjective ; aucune promesse de délai non mesurée.

## Cycle 298 — Brand DNA et bibliothèque de projets
- [ ] Dossier client commun : briefs, style validé, logos, typographies, palette, visuels, vidéos, site et versions.
- [ ] Validations explicites des marques avant usage, contenu autorisé, provenance et licences.
- [ ] Mémoire de marque transversale, séparant les données des projets Vision et Web.
- [ ] Comparateur de versions et retours arrière, conservation après mises à jour.

## Cycle 299 — Prospect et Google Maps
- [ ] Carte officielle Google Maps Platform lorsque configurée avec facturation.
- [ ] Fiche native Google Places UI Kit / lien vers la fiche d'origine, pas de clonage d'interface propriétaire.
- [ ] Filtrage métiers, entreprises indépendantes ; absence de site non supposée en l'absence d'URL enregistrée.
- [ ] Cinq suggestions quotidiennes vérifiables, aucune recommandation inventée ; coûts Google plafonnables.
- [ ] Sélection → dossier Pro → site de démonstration non officiel → contrôle utilisateur.

## Cycle 300 — LocalAI Autopilot et production commerciale
- [ ] Préparer site multipages original, photographies autorisées/générées, responsive, vérifications de navigation.
- [ ] Portail client privé : commentaires, comparaison des versions, validation finale et droits d'accès.
- [ ] Publication explicite et autorisée, puis seulement publicité/devis/facture/CRM liés au projet.
- [ ] Intégration de déploiement GitHub/Vercel, statut réel, liens testés, conformité et dossiers archivés.
- [ ] Tableau de bord VRAM/temps/résolutions/erreurs, déconnexions Codex/ComfyUI avec reprise contrôlée.

## Tests transversaux pour chaque livraison
- [ ] Le questionnaire doit modifier visiblement la position/forme/animation du composant ciblé ; aucune option décorative sans effet.
- [ ] Fonctionnement sans JavaScript facultatif pour la navigation primaire ; clavier et réductions de mouvement.
- [ ] Aucune suppression ni migration destructive des projets existants.
- [ ] Tests unitaires + tests UX ciblés + Windows Actions vert + démarrage EXE, update et contrôle des assets.
- [ ] Tests métier manuels sur le véritable PC RTX 3060 avant de marquer à 100 %.

## État actuel : distinction entre réalisé et planifié
Build 294 : le configurateur de l'accueil est en cours de production. Les cycles 295–300 sont des **fonctionnalités planifiées**, pas des fonctionnalités déjà disponibles. Le générateur Vision/Codex et la carte existants sont préservés ; un redesign total risquant de perdre les projets est exclu.
