# LocalAI Studio — Cahier de recette final basé sur les 261 réponses

**Statut : spécification produit approuvée, non certificat de livraison.** Date de référence : 3 novembre 2026. Source inviolable : `docs/LOCALAI_STUDIO_QCM_V1_APPROVED.json`.

Objectif : permettre la correction et le peaufinage élément par élément, bouton par bouton. Un choix marqué « à réaliser » n'est pas déclaré prêt. L'interface NSFW reste inchangée. Les projets existants ne sont jamais effacés. Chaque bouton visible doit déclencher une action réelle ; sinon il reste absent.

## Recette de la branche 296

Le dossier `docs/qa296` contient les captures comparatives du Build 295 et de cette branche aux cinq dimensions demandées, ainsi que l’aperçu public Vision. La préférence de réduction des animations persiste après rechargement dans Chromium. Les boutons de conversation existants sont accessibles dans le menu Vision. Le bouton + ouvre le sélecteur de fichier I2V. À 1365 × 768, les deux cartes de même hauteur se terminent au-dessus du dock aux facteurs Chromium 1, 1,25 et 1,5. La suite Python couvre les commerces avec site, sans site renseigné et avec URL non exploitable, ainsi que la sélection quotidienne indépendante du filtre d’affichage.

La revue #54 ajoute le scénario reproductible de la carte, la trace de mouvement et les comparaisons UHD dans [le rapport de recette](qa296/REVUE_54.md).

Les 261 réponses originales sont conservées. Le contrôle visuel Windows aux différents DPI, la cadence sur RTX 3060, la génération avec ComfyUI, la session Codex locale et les API Google configurées restent à vérifier sur une installation équipée.

## Contrat partagé de tout composant
- **Placement :** choix QCM ci-dessous ; sur ordinateur, tablette et mobile, sans chevauchement avec chat, clavier virtuel, carte, navigateur et dock.
- **État :** normal, survol, focus, sélectionné, désactivé, chargement, erreur, terminé ; tooltips accessibles ; animations allégées sur mobile et supprimables via reduced-motion.
- **Action :** route, API ou processus réel ; aucune réponse simulée, aucun bouton « bientôt » présenté comme fonctionnel.
- **Erreurs :** préserver les saisies, fichiers, projets et paramètres ; proposer reprise ou correction ; ne jamais annoncer un succès sans résultat vérifié.
- **Validation :** tests automatiques Python/Node et scénarios navigateur + captures 1440×900, 1280×720, 390×844, navigation clavier, VRAM/qualité RTX 3060 pour médias ; pas de 100 % avant validation réelle.
- **Protection :** ne pas déplacer/afficher ni modifier l'espace NSFW en dehors de ses règles existantes ; pas de projet Vision confondu avec Web.

## Précisions sur les fonctionnalités futures
LocalAI Intelligence : agents direction artistique → code → inspection navigateur → réparation, avec budgets et arrêt contrôlé. Vision Engine : choix modèle selon licence, VRAM et rendu réel. Cinema : storyboards avec vrais plans et timeline montable. Brand DNA : dossier marque par client. Prospect : points et fiche officielle avec attribution, filtre du site fiable seulement sur données qualifiées. Autopilot : démarrage encadré après validation. Les intégrations payantes Google/Vercel/modèles nécessitent permissions/configuration ; aucune souscription implicite.

## 01 · Identité générale

**Page/zone :** Accueil. **Points d'implémentation :** `localai-studio.html · studio-qcm-v1.css`. **Dépendance :** route /studio.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `ui_univers` | Mix premium et technologique | Appliquer « Mix premium et technologique » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_palette` | Noir profond + violet + cyan | Appliquer « Noir profond + violet + cyan » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Intégré partiellement — QA requise |
| `ui_palette_split` | Oui, Web violet et Vision cyan | Appliquer « Oui, Web violet et Vision cyan » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Intégré partiellement — QA requise |
| `ui_theme` | Automatique selon Windows + manuel | Appliquer « Automatique selon Windows + manuel » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | À développer / connecter au moteur |
| `ui_contrast` | Équilibré et lisible | Appliquer « Équilibré et lisible » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_density` | Équilibrée | Appliquer « Équilibrée » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_shape` | Mix selon le type de composant | Appliquer « Mix selon le type de composant » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_typography` | Sans-serif géométrique | Appliquer « Sans-serif géométrique » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Intégré partiellement — QA requise |
| `ui_type_scale` | Adaptative selon l’écran | Appliquer « Adaptative selon l’écran » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_logo` | Marque commune + deux emblèmes spécifiques | Appliquer « Marque commune + deux emblèmes spécifiques » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_logo_motion` | Rotation ou profondeur 3D | Appliquer « Rotation ou profondeur 3D » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_surfaces` | Métal brossé / mat | Appliquer « Métal brossé / mat » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_background` | Dégradés atmosphériques animés | Appliquer « Dégradés atmosphériques animés » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Intégré partiellement — QA requise |
| `ui_shadows` | Profondeur cinématique | Appliquer « Profondeur cinématique » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Intégré partiellement — QA requise |
| `ui_icons` | Icônes personnalisées par univers | Appliquer « Icônes personnalisées par univers » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |
| `ui_graphic_library` | Design system strict identique | Appliquer « Design system strict identique » dans le design system global, sans variation aléatoire selon la page ; vérifier contraste, lisibilité, composants et réduction des mouvements. | Conservé ou planifié — non certifié |

**Échec et reprise prévus :** Police système indisponible → sans-serif locale ; erreur de thème → conserver contraste et focus.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 02 · Accueil LocalAI Studio

**Page/zone :** Accueil. **Points d'implémentation :** `localai-studio.html · studio-qcm-home.js`. **Dépendance :** route /studio.

**Précision validée :** Accueil intuitif pour les nouveaux utilisateurs, spectaculaire, beaucoup d'animations maîtrisées.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `home_macro` | Menu radial / orbites | Issue #52 : deux cartes sans noyau orbital, Web puis Vision sur mobile. | Vérifié dans Chromium aux cinq résolutions demandées |
| `home_first` | LocalAiWeb | Construire le composant fonctionnel selon « LocalAiWeb », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_title` | Centré au-dessus des cartes | Construire le composant fonctionnel selon « Centré au-dessus des cartes », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_art` | Mini interface 3D animée | Construire le composant fonctionnel selon « Mini interface 3D animée », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_size` | Adaptative à l’écran | Construire le composant fonctionnel selon « Adaptative à l’écran », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_click` | Carte entière cliquable | Construire le composant fonctionnel selon « Carte entière cliquable », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_buttons` | Bas centre | Construire le composant fonctionnel selon « Bas centre », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_labels` | Logo et nom en haut | Construire le composant fonctionnel selon « Logo et nom en haut », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_card_animate` | Flottement subtil permanent | Construire le composant fonctionnel selon « Flottement subtil permanent », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_entry` | Zoom cinématique | Construire le composant fonctionnel selon « Zoom cinématique », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_quick_links` | Projets récents seulement | Construire le composant fonctionnel selon « Projets récents seulement », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_status` | Carte d’activité dédiée | Véritable carte d'activités serveur, progression et accès aux tâches en cours. Jamais d'activité factice ni de pourcentage inventé. | À développer / connecter au moteur |
| `home_brand` | Menu « Outils » | Construire le composant fonctionnel selon « Menu « Outils » », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `home_update` | Menu paramètres global | Construire le composant fonctionnel selon « Menu paramètres global », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `home_guidance` | Accueil direct | Construire le composant fonctionnel selon « Accueil direct », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |

**Échec et reprise prévus :** API projets indisponible → accueil utilisable avec liens directs ; animations désactivables.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 03 · Navigation & commandes communes

**Page/zone :** Navigation. **Points d'implémentation :** `studio-qcm-shell.js`. **Dépendance :** Ctrl+K ; routes Studio/Web/Vision/Carte.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `nav_primary` | Barre flottante inférieure | Dock flottant inférieur, lien vers Studio, Projets Web, Carte, Vision et palette Actions, aucune navigation cachée lors de l'usage mobile. | Intégré partiellement — QA requise |
| `nav_width` | Toujours ouverte | Construire le composant fonctionnel selon « Toujours ouverte », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `nav_home_btn` | Logo en haut gauche | Construire le composant fonctionnel selon « Logo en haut gauche », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `nav_switch` | Barre latérale | Construire le composant fonctionnel selon « Barre latérale », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `nav_back` | Flèche en haut à gauche | Construire le composant fonctionnel selon « Flèche en haut à gauche », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `nav_search` | Palette de commandes Ctrl+K | Ctrl+K ouvre la palette ; filtrage insensible aux accents ; ↑/↓, Entrée, Échap et focus visibles ; aucun raccourci appliqué dans NSFW. | Intégré partiellement — QA requise |
| `nav_settings` | Menu du profil | Construire le composant fonctionnel selon « Menu du profil », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `nav_projects` | Barre latérale | Construire le composant fonctionnel selon « Barre latérale », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `nav_notifications` | Cloche en haut droite | Construire le composant fonctionnel selon « Cloche en haut droite », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `nav_shortcuts` | Essentiels seulement | Construire le composant fonctionnel selon « Essentiels seulement », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `nav_tooltips` | Adaptatif selon l’espace | Construire le composant fonctionnel selon « Adaptatif selon l’espace », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `nav_undo` | Boutons contextuels uniquement | Construire le composant fonctionnel selon « Boutons contextuels uniquement », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |

**Échec et reprise prévus :** Navigation interrompue → routes toujours utilisables sans JavaScript ; pas de piège de focus.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 04 · LocalAiWeb — création par conversation

**Page/zone :** Création Web. **Points d'implémentation :** `localaiweb.html · studio-qcm-editor.js`. **Dépendance :** projet Web existant.

**Précision validée :** Ne pas ajouter de bouton « Améliorer mon prompt ». Un QCM esthétique est souhaité, aperçu seulement si qualitatif.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `web_split` | Chat à gauche / aperçu à droite | Construire le composant fonctionnel selon « Chat à gauche / aperçu à droite », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_chat_width` | Redimensionnable, départ 32 % | Poignée clavier/souris de 25 à 55 %, valeur initiale 32 %, largeur conservée localement ; libérer le pointeur après drag. | Intégré partiellement — QA requise |
| `web_prompt` | Fixé en bas à gauche | Construire le composant fonctionnel selon « Fixé en bas à gauche », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_send` | À droite dans le champ | Construire le composant fonctionnel selon « À droite dans le champ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_attach` | + à gauche de saisie | Construire le composant fonctionnel selon « + à gauche de saisie », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `web_refine` | Tu proposes le meilleur compromis | Construire le composant fonctionnel selon « Tu proposes le meilleur compromis », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `web_project_title` | Titre éditable en haut de l’aperçu | Double clic ou Entrée dans le titre → modification réelle via /api/web/project/rename ; gérer erreurs et annulation. | Intégré partiellement — QA requise |
| `web_new` | Dans le sélecteur de projets | Construire le composant fonctionnel selon « Dans le sélecteur de projets », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `web_agent_status` | Un indicateur seulement si problème | Construire le composant fonctionnel selon « Un indicateur seulement si problème », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `web_coding_state` | Aperçu conservé + progression | Construire le composant fonctionnel selon « Aperçu conservé + progression », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_source` | Icône </> en haut droit | Icône </> ouvre le code source réel via /api/web/project, avec fichiers au choix, sans montrer de faux exemple. | Intégré partiellement — QA requise |
| `web_history` | Choix conversation / actions | Construire le composant fonctionnel selon « Choix conversation / actions », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_message_edit` | Icône crayon au survol | Construire le composant fonctionnel selon « Icône crayon au survol », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `web_sections` | Panneau ouvrable « Processus » | Construire le composant fonctionnel selon « Panneau ouvrable « Processus » », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `web_creation_options` | QCM dédié avec aperçu visuel | Construire le composant fonctionnel selon « QCM dédié avec aperçu visuel », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |

**Échec et reprise prévus :** Codex/API absent → erreur compréhensible, saisie conservée et bouton Réessayer.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 05 · LocalAiWeb — carte de prospection

**Page/zone :** Carte. **Points d'implémentation :** `localaiweb-map.html · localaiweb-map.js`. **Dépendance :** Google Maps/Places officiel si configuré.

**Précision validée :** Google Maps sombre et épuré, légendes utiles, aucun champ de recherche, points avec trois états et bouton Cibler animé sous la fiche officielle ; animations ludiques.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `map_canvas` | Carte plein écran | Construire le composant fonctionnel selon « Carte plein écran », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_provider` | Carte Google simplifiée avec légendes utiles | Carte Google Maps officielle sombre lorsque les clés API Maps + Places fonctionnent. Sinon carte publique avec identification explicite du fournisseur. | Conservé ou planifié — non certifié |
| `map_camera` | France entière | Construire le composant fonctionnel selon « France entière », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_controls` | Contrôles Google natifs | Construire le composant fonctionnel selon « Contrôles Google natifs », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_pins` | Icônes natives Google | Construire le composant fonctionnel selon « Icônes natives Google », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_pins_size` | Moyens | Construire le composant fonctionnel selon « Moyens », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `map_clustering` | Affichage progressif par zoom | Construire le composant fonctionnel selon « Affichage progressif par zoom », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_filter` | Aucun filtre | Construire le composant fonctionnel selon « Aucun filtre », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `map_trade` | Tu proposes le meilleur compromis | Construire le composant fonctionnel selon « Tu proposes le meilleur compromis », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `map_search` | Pas de recherche, déplacement carte | Construire le composant fonctionnel selon « Pas de recherche, déplacement carte », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `map_no_website` | Filtre à trois états | Sur annuaire public : filtre Tous / Non renseigné / Renseigné, à ne jamais présenter comme vérification d'absence. Sur POI Google natifs : désactivé et raison affichée, aucun faux résultat. | Intégré partiellement — QA requise |
| `map_click` | Fiche Google puis action « Cibler » | Cliquer établissement → fiche issue du fournisseur → informations et bouton Cibler basé sur jeton de sélection valide. Conserver la carte exploitable. | Intégré partiellement — QA requise |
| `map_hover` | Nom + métier | Construire le composant fonctionnel selon « Nom + métier », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `map_recommend` | 5 cartes dans un tiroir inférieur | Cinq prospects réels depuis /api/web/map/prospects/today, dans un tiroir inférieur repliable. Pas de noms, scores ou coordonnées inventés. | Intégré partiellement — QA requise |
| `map_coverage` | Nombre d’entreprises affichées | Construire le composant fonctionnel selon « Nombre d’entreprises affichées », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_loading` | Animation de points | Construire le composant fonctionnel selon « Animation de points », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `map_actions` | Zoom + recentrer + filtres | Construire le composant fonctionnel selon « Zoom + recentrer + filtres », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `map_mobile` | Plein écran + fiche bottom sheet | Construire le composant fonctionnel selon « Plein écran + fiche bottom sheet », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |

**Échec et reprise prévus :** Clé Google/Places absente → carte publique de secours clairement désignée ; ne jamais simuler des POI Google.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 06 · Fiche entreprise & prospection

**Page/zone :** Fiche entreprise. **Points d'implémentation :** `localaiweb-map.html · localaiweb-map.js`. **Dépendance :** fiche et jeton de sélection.

**Précision validée :** Après création, expliquer dans le chat les choix de conception et les éléments qui les fondent ; prévisualiser les pages pertinentes.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `business_sheet` | Fiche Google native + bouton Studio | La fiche Google conserve l'affichage et les attributions officielles ; bouton Studio distinct sans recopier l'interface propriétaire. | Conservé ou planifié — non certifié |
| `business_header` | Nom très visible + métier | Construire le composant fonctionnel selon « Nom très visible + métier », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `business_photo` | Selon disponibilité et droits | Construire le composant fonctionnel selon « Selon disponibilité et droits », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `business_info` | Structure Google officielle | Construire le composant fonctionnel selon « Structure Google officielle », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `business_website` | Badge Oui / Non / Inconnu | Construire le composant fonctionnel selon « Badge Oui / Non / Inconnu », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `business_primary` | Bas de fiche collé | Construire le composant fonctionnel selon « Bas de fiche collé », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `business_secondary` | Icône favori | Construire le composant fonctionnel selon « Icône favori », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `business_original` | Sous l’adresse | Construire le composant fonctionnel selon « Sous l’adresse », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `business_score` | Niveau faible/moyen/fort explicable | Score explicable avec critères documentés et date de vérification, aucun jugement basé sur informations manquantes. | À développer / connecter au moteur |
| `business_actions` | Ajouter au CRM + notes | Construire le composant fonctionnel selon « Ajouter au CRM + notes », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `business_plan` | Choix projet Pro + style | Après Cibler, créer un projet Pro avec brief métiers, QCM esthétique et aperçu des pages ; l'IA expose ses hypothèses, sans inventer des faits. | À développer / connecter au moteur |
| `business_close` | Croix + Échap | Construire le composant fonctionnel selon « Croix + Échap », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `business_mobile` | Bottom sheet coulissante | Construire le composant fonctionnel selon « Bottom sheet coulissante », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |

**Échec et reprise prévus :** Fiche absente ou jeton expiré → action de création désactivée avec explication, jamais de données inventées.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 07 · LocalAiWeb — éditeur & prévisualisation

**Page/zone :** Éditeur. **Points d'implémentation :** `studio-qcm-editor.js · studio-qcm-editor-rail.js`. **Dépendance :** projet et ses vrais fichiers.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `editor_main` | Panneaux redimensionnables | Construire le composant fonctionnel selon « Panneaux redimensionnables », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_top` | Toujours visible | Construire le composant fonctionnel selon « Toujours visible », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_device` | 3 icônes côte à côte en haut | Construire le composant fonctionnel selon « 3 icônes côte à côte en haut », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_eye` | Près des formats | Construire le composant fonctionnel selon « Près des formats », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_cursor` | Barre flottante sur site | Construire le composant fonctionnel selon « Barre flottante sur site », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_select` | Sélection type Figma | Construire le composant fonctionnel selon « Sélection type Figma », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `editor_double` | Texte directement éditable | Construire le composant fonctionnel selon « Texte directement éditable », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `editor_history` | Timeline de versions | Liste des snapshots backend datés ; restauration sur confirmation, snapshot de sécurité automatique, rafraîchir après réussite. | Intégré partiellement — QA requise |
| `editor_save` | Snapshots automatiques + bouton version | Versionnage sur sauvegarde réelle du projet ; bouton Version connecté à l'API existante, erreurs visibles. | Intégré partiellement — QA requise |
| `editor_zip` | Menu ⋯ | Construire le composant fonctionnel selon « Menu ⋯ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_publish` | Haut droite très visible | Publier reste désactivé tant que les conditions internes réelles ne sont pas validées ; préflight, autorisation et URL finale. | Intégré partiellement — QA requise |
| `editor_3d` | Aucun outil 3D visible sans objet | Construire le composant fonctionnel selon « Aucun outil 3D visible sans objet », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `editor_assets` | Onglet Médias dans le rail | Lister les vrais médias du projet via project.assets, signaler vide si aucun actif ; aucun média simulé. | À développer / connecter au moteur |
| `editor_colors` | Panneau Design à droite | Construire le composant fonctionnel selon « Panneau Design à droite », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `editor_elements` | Panneau Pages + Sections | Construire le composant fonctionnel selon « Panneau Pages + Sections », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `editor_pages` | Arborescence latérale | Afficher les vrais fichiers HTML du projet et leur nom, sélection de la source correspondante ; la vraie navigation de l'iframe reste indépendante. | À développer / connecter au moteur |
| `editor_mask` | Aperçu grisé + pourcentage | Construire le composant fonctionnel selon « Aperçu grisé + pourcentage », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `editor_qa` | Inspections invisibles sauf problème | Construire le composant fonctionnel selon « Inspections invisibles sauf problème », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |

**Échec et reprise prévus :** Fichier/version introuvable → aucun remplacement silencieux, conserver le site, afficher erreur.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 08 · LocalAiWeb — projets & historique

**Page/zone :** Projets Web. **Points d'implémentation :** `localaiweb-projects.js · studio-qcm-projects.js`. **Dépendance :** API /api/web/projects.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `projects_entry` | Dossiers Pro / Libres | Construire le composant fonctionnel selon « Dossiers Pro / Libres », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `projects_tabs` | Deux onglets | Pro/Libres exclusifs, aucune perte de sélection pendant recherche ; rétablissement de l'onglet précédent au retour. | Intégré partiellement — QA requise |
| `projects_new` | Carte + dans la grille | Une carte + par catégorie : Libre déclenche création existante, Pro ouvre directement la carte réelle. | Intégré partiellement — QA requise |
| `projects_card` | Capture + statut + dernier changement | Construire le composant fonctionnel selon « Capture + statut + dernier changement », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `projects_filter` | Barre de recherche + filtres | Construire le composant fonctionnel selon « Barre de recherche + filtres », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `projects_version` | Timeline projet | Construire le composant fonctionnel selon « Timeline projet », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `projects_delete` | Menu ⋯ + confirmation | Construire le composant fonctionnel selon « Menu ⋯ + confirmation », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `projects_archive` | Archiver depuis menu ⋯ | Construire le composant fonctionnel selon « Archiver depuis menu ⋯ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `projects_resume` | Notification globale cliquable | Construire le composant fonctionnel selon « Notification globale cliquable », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `projects_client` | Bibliothèque centrale de marques | Construire le composant fonctionnel selon « Bibliothèque centrale de marques », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `projects_activity` | Pourcentage sur chaque carte | Construire le composant fonctionnel selon « Pourcentage sur chaque carte », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |

**Échec et reprise prévus :** Projet indisponible → aucune suppression, affichage de l'erreur et rechargement.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 09 · Publication, publicité, devis et CRM

**Page/zone :** Commercial. **Points d'implémentation :** `web_crm.py · API Vercel`. **Dépendance :** après publication consentie.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `publish_gate` | Après Publier uniquement | Publicité, devis, facturation et CRM du projet apparaissent après publication vérifiée, jamais avant ; vérifier en API. | Intégré partiellement — QA requise |
| `publish_dialog` | Assistant en 3 étapes | Réaliser « Assistant en 3 étapes » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `publish_checks` | Résumé + détails dépliables | Réaliser « Résumé + détails dépliables » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `publish_status` | Carte de confirmation | Réaliser « Carte de confirmation » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `publish_ad` | Automatiquement proposé | Réaliser « Automatiquement proposé » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | Intégré partiellement — QA requise |
| `publish_quote` | À la fin du parcours publication | Réaliser « À la fin du parcours publication » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | Intégré partiellement — QA requise |
| `publish_invoice` | Dossier client | Réaliser « Dossier client » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_home` | Dossiers clients | Réaliser « Dossiers clients » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_pipeline` | Kanban | Réaliser « Kanban » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_contact` | Dans le dossier client | Réaliser « Dans le dossier client » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_preview` | Tu proposes le meilleur compromis | Réaliser « Tu proposes le meilleur compromis » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_pricing` | Généré puis validé manuellement | Réaliser « Généré puis validé manuellement » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |
| `crm_delivery` | Tous selon sélection | Réaliser « Tous selon sélection » dans le cycle de publication/CRM, déclenché après publication réellement réussie et confirmation appropriée. | À développer / connecter au moteur |

**Échec et reprise prévus :** Publication échouée → ne pas afficher « publié », conserver le brouillon et les métadonnées.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 10 · LocalAiVision — accueil, chat et commandes

**Page/zone :** LocalAiVision. **Points d'implémentation :** `index.html · app.js · studio-qcm-vision.js`. **Dépendance :** mode public uniquement.

**Précision validée :** Ne pas modifier l'interface actuelle de l'espace NSFW ; améliorer les performances générales sans changer sa disposition.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `vision_layout` | Panneaux redimensionnables | En mode public, chat/aperçu côte à côte, poignée persistante, mobile onglets. En NSFW, ne pas changer le layout original. | Intégré partiellement — QA requise |
| `vision_welcome` | Carte des modes Photo, Vidéo, Retouche, Publicité | Carte Photo/Vidéo/Retouche/Publicité basée sur les vrais modes implémentés, gris si non disponibles et raisons compréhensibles. | Conservé ou planifié — non certifié |
| `vision_field` | Bas du chat gauche | Construire le composant fonctionnel selon « Bas du chat gauche », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_send` | Bouton dépendant du mode | Construire le composant fonctionnel selon « Bouton dépendant du mode », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_mode` | Détection automatique + bouton changer | Construire le composant fonctionnel selon « Détection automatique + bouton changer », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_tool_gear` | Bas gauche du champ | Construire le composant fonctionnel selon « Bas gauche du champ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_add` | Bas gauche du champ | Construire le composant fonctionnel selon « Bas gauche du champ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_models` | Dans réglages experts | Construire le composant fonctionnel selon « Dans réglages experts », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_advanced` | Pop-up flottante | Construire le composant fonctionnel selon « Pop-up flottante », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_gallery` | Tiroir fermable | Construire le composant fonctionnel selon « Tiroir fermable », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_history` | Bouton haut droit | Construire le composant fonctionnel selon « Bouton haut droit », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_nsfw_btn` | Page réservée distincte | Construire le composant fonctionnel selon « Page réservée distincte », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_brand` | Dans mode Publicité | Construire le composant fonctionnel selon « Dans mode Publicité », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `vision_preview` | Grande carte à droite | Montrer uniquement le média réellement retourné par la dernière génération du chat, même origine autorisée, sans miniature générique prétendue générée. | Intégré partiellement — QA requise |
| `vision_actions` | Au survol en overlay | Construire le composant fonctionnel selon « Au survol en overlay », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |

**Échec et reprise prévus :** ComfyUI déconnecté → ne pas perdre le chat, afficher statut, proposer réparation.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 11 · LocalAiVision — génération photo

**Page/zone :** Photo. **Points d'implémentation :** `app.js · media_director.py · workflows.py`. **Dépendance :** workflow ComfyUI image.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `photo_comp` | Viewer à droite + réglages dans chat | Implémenter réellement « Viewer à droite + réglages dans chat » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `photo_styles` | Tuiles avec véritables exemples | Implémenter réellement « Tuiles avec véritables exemples » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_ratio` | Icônes illustrées | Implémenter réellement « Icônes illustrées » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_quality` | Choix automatique de profil VRAM | Implémenter réellement « Choix automatique de profil VRAM » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_seed` | Dans paramètres avancés | Implémenter réellement « Dans paramètres avancés » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `photo_batch` | 1 image et variantes sur demande | Implémenter réellement « 1 image et variantes sur demande » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_ref` | Bouton + Image dans le champ | Implémenter réellement « Bouton + Image dans le champ » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `photo_compare` | Grille 2×2 | Implémenter réellement « Grille 2×2 » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_prompt` | Choix technique / créatif | Implémenter réellement « Choix technique / créatif » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_detail` | Automatique avec validation | Correction de mains/visages/textures seulement avec modèle compatible ; comparaison avant/après et validation avant remplacement. | À développer / connecter au moteur |
| `photo_upscale` | Sous le résultat | Implémenter réellement « Sous le résultat » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `photo_export` | Fenêtre Export avancé | Implémenter réellement « Fenêtre Export avancé » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |

**Échec et reprise prévus :** Rendu échoué → conserver prompt, paramètres, fichiers et rapport de diagnostic.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 12 · LocalAiVision — T2V / I2V et cinéma

**Page/zone :** Vidéo. **Points d'implémentation :** `app.js · media_director.py · workflows.py`. **Dépendance :** workflow ComfyUI vidéo.

**Précision validée :** Toute nouvelle fonction doit être opérationnelle à son introduction, pas seulement un bouton.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `video_split` | Espace création + montage séparés | Implémenter réellement « Espace création + montage séparés » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Conservé ou planifié — non certifié |
| `video_type` | Deux onglets bien visibles | Implémenter réellement « Deux onglets bien visibles » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_engine` | Moteur auto, nom visible | Implémenter réellement « Moteur auto, nom visible » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_reference` | Miniature jointe dans le champ | Implémenter réellement « Miniature jointe dans le champ » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_duration` | Boutons 3/5/10/20 s | Implémenter réellement « Boutons 3/5/10/20 s » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_fps` | Auto selon profil VRAM | Implémenter réellement « Auto selon profil VRAM » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_camera` | Galerie d’exemples animés | Implémenter réellement « Galerie d’exemples animés » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_motion` | Faible / Standard / Intense | Implémenter réellement « Faible / Standard / Intense » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_frame` | Formats TikTok/YouTube/Reels | Implémenter réellement « Formats TikTok/YouTube/Reels » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_story` | Mode Vidéo / Mode Film | Storyboard multi-plans = tâches vidéo réelles en séquence, montage et export, persistance de chaque plan et ressources VRAM mesurées. | À développer / connecter au moteur |
| `video_timeline` | Bas de fenêtre | Timeline non décorative : séquences ordonnables, durée mesurée, extrait réel, annuler/rétablir et export MP4. | À développer / connecter au moteur |
| `video_plan` | Mini boutons Edit / Relancer / Remplacer | Implémenter réellement « Mini boutons Edit / Relancer / Remplacer » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_preview` | Images clés pendant le rendu | Implémenter réellement « Images clés pendant le rendu » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `video_consistency` | Panneau Identité verrouillée | Implémenter réellement « Panneau Identité verrouillée » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_export` | MP4 + paramètres avancés | Implémenter réellement « MP4 + paramètres avancés » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `video_audio` | Piste audio séparée | Implémenter réellement « Piste audio séparée » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |

**Échec et reprise prévus :** VRAM insuffisante → expliquer les ressources requises, proposer profil compatible sans masquer l'échec.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 13 · Retouche & édition des images

**Page/zone :** Retouche. **Points d'implémentation :** `app.js · mask.js · media_director.py`. **Dépendance :** fichier original et masque.

**Précision validée :** NSFW isolé ; préserver le fonctionnement.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `retouch_layout` | Grande toile avec barres flottantes | Implémenter réellement « Grande toile avec barres flottantes » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_mask` | Combinaison de tous | Implémenter réellement « Combinaison de tous » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_brush` | Panneau latéral | Implémenter réellement « Panneau latéral » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_before` | Slider vertical | Implémenter réellement « Slider vertical » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_strength` | Slider 0–100 % | Implémenter réellement « Slider 0–100 % » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_layers` | Calques facultatifs experts | Implémenter réellement « Calques facultatifs experts » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_undo` | Ctrl+Z + historique | Implémenter réellement « Ctrl+Z + historique » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_prompt` | Panneau chat à gauche | Implémenter réellement « Panneau chat à gauche » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_export` | En haut droite | Implémenter réellement « En haut droite » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `retouch_preserve` | Toujours conserver l’original | Conserver toujours les octets de l'original et créer des versions retouchées, sans remplacer ni altérer la source. | À développer / connecter au moteur |

**Échec et reprise prévus :** Masque/modèle incompatible → préserver original et donner explication claire.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 14 · Espace réservé — interface distincte

**Page/zone :** NSFW. **Points d'implémentation :** `studio-adult-workspace.css · nsfw_profile.py`. **Dépendance :** espace existant inchangé.

**Précision validée :** Préserver l'espace réservé actuel sans refonte dans ce cycle.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `adult_entry` | Panneau flouté + code | Préserver le comportement et la disposition actuelle (« Panneau flouté + code ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_theme` | Rouge profond + noir | Aucun changement CSS/UI du thème rouge existant dans cette refonte. Aucun média réservé affiché dans les autres univers. | UI existante à préserver |
| `adult_gate` | Déverrouillage par session | Préserver le comportement et la disposition actuelle (« Déverrouillage par session ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_layout` | Chat à gauche / créations à droite | Préserver le comportement et la disposition actuelle (« Chat à gauche / créations à droite ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_gallery` | Fermable avec croix | Préserver le comportement et la disposition actuelle (« Fermable avec croix ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_gear` | Bas gauche du champ | Préserver le comportement et la disposition actuelle (« Bas gauche du champ ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_source` | Menu déroulant | Préserver le comportement et la disposition actuelle (« Menu déroulant ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_progress` | Combinaison des trois | Préserver le comportement et la disposition actuelle (« Combinaison des trois ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_privacy` | Jamais affichées hors de l’espace | Ne jamais exposer médias/messages/projets réservés au dock global, notifications, aperçus et projets normaux. | UI existante à préserver |
| `adult_library` | Bibliothèque locale séparée | Préserver le comportement et la disposition actuelle (« Bibliothèque locale séparée ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_lock` | Icône cadenas dans l’en-tête | Préserver le comportement et la disposition actuelle (« Icône cadenas dans l’en-tête ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |
| `adult_fx` | Éclairage rouge doux | Préserver le comportement et la disposition actuelle (« Éclairage rouge doux ») sans changement de style ni d'accès réservé ; vérifier non-régression et isolation. | UI existante à préserver |

**Échec et reprise prévus :** Code d'accès/session périmé → verrouillage maintenu, aucune fuite dans les autres vues.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 15 · Mes créations (Photo / Vidéo / Autres)

**Page/zone :** Bibliothèque. **Points d'implémentation :** `app.js · stockage local Vision`. **Dépendance :** fichiers et médias réels.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `lib_view` | Grille / liste réglables | Construire le composant fonctionnel selon « Grille / liste réglables », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `lib_tabs` | Barre de filtres + recherche | Construire le composant fonctionnel selon « Barre de filtres + recherche », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `lib_search` | Champ en haut toujours visible | Construire le composant fonctionnel selon « Champ en haut toujours visible », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `lib_thumb` | Vignettes uniformes avec badge ratio | Construire le composant fonctionnel selon « Vignettes uniformes avec badge ratio », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `lib_hover` | Menu ⋯ | Construire le composant fonctionnel selon « Menu ⋯ », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Intégré partiellement — QA requise |
| `lib_open` | Viewer plein écran | Construire le composant fonctionnel selon « Viewer plein écran », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `lib_details` | Vue simplifiée + détails repliables | Construire le composant fonctionnel selon « Vue simplifiée + détails repliables », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `lib_reuse` | Dans barre de détail | Construire le composant fonctionnel selon « Dans barre de détail », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `lib_edit` | Deux actions visibles dans viewer | Construire le composant fonctionnel selon « Deux actions visibles dans viewer », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |
| `lib_bulk` | Aucune sélection multiple | Construire le composant fonctionnel selon « Aucune sélection multiple », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | Conservé ou planifié — non certifié |
| `lib_delete` | Suppression définitive après confirmation | Confirmation explicite, suppression du vrai fichier et du référencement local ; signaler si suppression fichier échoue. | Intégré partiellement — QA requise |
| `lib_folders` | Projets + tags | Construire le composant fonctionnel selon « Projets + tags », placer l'action dans son emplacement validé et préserver les routes/états de la page déjà existante. | À développer / connecter au moteur |

**Échec et reprise prévus :** Fichier absent → afficher indisponibilité et ne pas inventer de miniature.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 16 · Paramètres & gestion des modèles

**Page/zone :** Réglages. **Points d'implémentation :** `index.html · app.js · bootstrap_windows.py`. **Dépendance :** workflows et GPU réels.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `settings_entry` | Rouage bas gauche | Implémenter réellement « Rouage bas gauche » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_layout` | Fenêtre modale | Implémenter réellement « Fenêtre modale » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `settings_order` | Styles → LoRA → Simple → Expert | Implémenter réellement « Styles → LoRA → Simple → Expert » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_model` | Auto + choix expert en bas | Implémenter réellement « Auto + choix expert en bas » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_status` | Pastille + nom | Implémenter réellement « Pastille + nom » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_install` | Dans la carte du modèle | Implémenter réellement « Dans la carte du modèle » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `settings_loras` | Liste avec recherche | Implémenter réellement « Liste avec recherche » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_lora_strength` | Slider sur chaque LoRA | Implémenter réellement « Slider sur chaque LoRA » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_lora_apply` | Filtre modèles compatibles | Afficher seulement les LoRA compatibles avec le workflow ComfyUI choisi et fournir la raison lorsque incompatibles. | À développer / connecter au moteur |
| `settings_advanced` | Sections repliables | Implémenter réellement « Sections repliables » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_reset` | Question « Optimiser pour ma GPU » | Implémenter réellement « Question « Optimiser pour ma GPU » » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `settings_hardware` | Panneau diagnostic détaillé | Implémenter réellement « Panneau diagnostic détaillé » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `settings_presets` | Sauvegarder depuis chaque génération | Implémenter réellement « Sauvegarder depuis chaque génération » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | À développer / connecter au moteur |
| `settings_logs` | Bouton « Diagnostic » | Implémenter réellement « Bouton « Diagnostic » » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_update` | Dans paramètres généraux | Implémenter réellement « Dans paramètres généraux » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_import` | Bouton Importer | Implémenter réellement « Bouton Importer » dans le moteur et les réglages ComfyUI compatibles avec la tâche ; confirmer un changement de résultat, pas seulement un changement visuel. | Intégré partiellement — QA requise |
| `settings_validation` | Grisé + raison | Toute entrée sans effet sur le workflow est désactivée avec explication ; seule validation sur exécution GPU peut faire passer à 100 %. | À développer / connecter au moteur |

**Échec et reprise prévus :** Modèle/LoRA absent → désactiver le réglage incompatible et proposer réparation documentée.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 17 · Chargements, erreurs et animations

**Page/zone :** Progression. **Points d'implémentation :** `studio-activity.js · comfy_progress.py`. **Dépendance :** événements serveur réels.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `progress_place` | Panneau Activités flottant | Appliquer « Panneau Activités flottant » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_percent` | Étapes détaillées + pourcentage | Appliquer « Étapes détaillées + pourcentage » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_truth` | Estimation clairement signalée | Pourcentage réellement observé si l'API le fournit ; sinon statut « estimation » sans inventer une certitude. | Intégré partiellement — QA requise |
| `progress_preview` | Dès disponibilité technique | Appliquer « Dès disponibilité technique » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_overlay` | Panneau étapes en surimpression | Appliquer « Panneau étapes en surimpression » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_cancel` | Toujours à côté du pourcentage | Annuler agit sur le vrai job et confirme sa suppression/interruption côté moteur, ou indique l'impossibilité. | À développer / connecter au moteur |
| `progress_background` | Tâche continue + pastille | Appliquer « Tâche continue + pastille » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_error` | Message compréhensible + Réessayer | Appliquer « Message compréhensible + Réessayer » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_retry` | Silencieuse avec statut | Appliquer « Silencieuse avec statut » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Intégré partiellement — QA requise |
| `progress_success` | Ouvrir automatiquement le résultat | Appliquer « Ouvrir automatiquement le résultat » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | À développer / connecter au moteur |
| `progress_motion` | Ligne de progression brillante | Appliquer « Ligne de progression brillante » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | Conservé ou planifié — non certifié |
| `progress_sound` | Son discret à la fin | Appliquer « Son discret à la fin » uniquement aux événements de tâches réels, avec état, annulation/reprise et erreur vérifiables côté moteur. | À développer / connecter au moteur |

**Échec et reprise prévus :** Progrès indéterminé → annoncer estimation et non pourcentage mesuré.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 18 · Mobile, fenêtres et accessibilité

**Page/zone :** Mobile. **Points d'implémentation :** `localaiweb-mobile.css · studio-qcm-v1.css`. **Dépendance :** dimensions et gestes tactiles.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `mobile_nav` | Barre d’onglets basse | Respecter « Barre d’onglets basse » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `mobile_chat` | Onglets Chat / Aperçu | Respecter « Onglets Chat / Aperçu » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `mobile_map` | Tiroir depuis le bas | Respecter « Tiroir depuis le bas » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `mobile_buttons` | Actions majeures + menu ⋯ | Respecter « Actions majeures + menu ⋯ » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Conservé ou planifié — non certifié |
| `mobile_qcm` | Plein écran mobile | Respecter « Plein écran mobile » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Conservé ou planifié — non certifié |
| `mobile_orientation` | Deux modes soignés | Respecter « Deux modes soignés » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | À développer / connecter au moteur |
| `mobile_touch` | Minimum 48 px | Respecter « Minimum 48 px » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | À développer / connecter au moteur |
| `mobile_keyboard` | Champ toujours visible au-dessus | Respecter « Champ toujours visible au-dessus » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `mobile_motion` | Allégées automatiquement | Respecter « Allégées automatiquement » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `access_reduce` | Système + interrupteur | Respecter « Système + interrupteur » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `access_focus` | Contour lumineux visible | Respecter « Contour lumineux visible » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | Intégré partiellement — QA requise |
| `access_contrast` | Disponible comme option | Respecter « Disponible comme option » sur téléphone et desktop, vérifier dimensions tactiles, focus visible, clavier virtuel et zones sûres. | À développer / connecter au moteur |

**Échec et reprise prévus :** Taille insuffisante → navigation accessible, actions critiques dans menu ⋯.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## 19 · Agents, Autopilot et tableaux de bord futurs

**Page/zone :** Agents. **Points d'implémentation :** `web_hybrid.py · web_browser_qa.py`. **Dépendance :** agents et modèles disponibles uniquement.

**Précision validée :** Ne pas afficher de fonctions futures tant qu'elles ne sont pas opérationnelles.

| Choix stable | Valeur approuvée | Comportement / résultat contrôlable | État technique du premier cycle |
|---|---|---|---|
| `agents_hub` | Intégré à chaque création | Réaliser « Intégré à chaque création » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_state` | Badge dans le chat | Réaliser « Badge dans le chat » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | Intégré partiellement — QA requise |
| `agents_controls` | Mode auto / assisté | Réaliser « Mode auto / assisté » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_qa` | Rapport visuel comparatif | Réaliser « Rapport visuel comparatif » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | Intégré partiellement — QA requise |
| `agents_repair` | Mode auto / manuel | Réaliser « Mode auto / manuel » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_branddna` | Dans chaque dossier client | Réaliser « Dans chaque dossier client » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_compare` | Trois variantes côte à côte | Réaliser « Trois variantes côte à côte » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_prospect` | Bandeau de 5 prospects | Réaliser « Bandeau de 5 prospects » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_autopilot` | Assistant guidé en étapes | Réaliser « Assistant guidé en étapes » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_portal` | Onglet dans projet Pro | Réaliser « Onglet dans projet Pro » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_performance` | Page Diagnostic | Réaliser « Page Diagnostic » uniquement lorsque l'orchestrateur, le stockage d'état, les agents et le contrôle qualité sont réellement opérationnels ; sinon rester absent de l'interface. | À développer / connecter au moteur |
| `agents_rollout` | Afficher seulement si opérationnelles | N'exposer qu'une action dont le backend est opérationnel, testé et récupérable ; aucune carte « bientôt » prise pour un outil utilisable. | Intégré partiellement — QA requise |

**Échec et reprise prévus :** Agent IA absent → aucune génération fictive, proposer reprise du projet existant.

**Test de réception :** ouvrir la page indiquée, exercer chacune des commandes réelles et comparer sa position/animation à la valeur approuvée ; vérifier retour/annulation, données persistantes et variante mobile.

## État d'avancement initial et seuil de finition
Total des décisions traçables : **261/261**. Décisions traitées en partie par la première itération : **134**. Un choix « intégré partiellement » requiert toujours tests UI et comportement. Les autres décisions restent explicitement en attente.

À la livraison, remplacer chaque état par **testé Windows**, **testé mobile**, **testé RTX 3060** (quand applicable), **validé visuellement**, puis seulement **100 %**. Aucun build CI vert ne valide seul la qualité esthétique.

## Validation de chaque bouton (fiche de bug / de correction)
```text
Page :
Identifiant stable de la décision QCM :
Libellé exact / icône / tooltip :
Position ordinateur / tablette / téléphone :
État initial ; survol ; focus ; actif ; désactivé ; chargement ; échec ; réussite :
Animation ; durée ; réduction des mouvements :
Source de données / route / API / permissions :
Effet métier attendu :
Résultat réellement observé :
Erreurs reproductibles (journaux ou captures) :
Non-régression projets / Vision / Web / NSFW :
Tests automatisés et contrôle manuel :
Verdict : bloqué / partiel / 100 %
```
