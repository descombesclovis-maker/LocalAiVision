# LocalAI Studio — mise en œuvre du QCM V1 approuvé
Date : 3 novembre 2026. Source de vérité : `docs/LOCALAI_STUDIO_QCM_V1_APPROVED.json`.
261 choix dans 19 sections, 83 essentiels. Ne jamais redemander un choix déjà fourni.
**Ces choix sont des spécifications, pas 261 fonctionnalités déjà implémentées.**

## Règles impératives
- Préserver les projets Pro/Libres, les données `LOCALAIWEB_DATA`, les conversations Vision, tous les modèles installés et le pipeline de mise à jour.
- Aucun changement visuel ni changement de raccourci dans l'espace NSFW ; jamais de fuite de miniatures dans le dock général.
- Aucun faux bouton : un nouvel élément agit sur le vrai workflow ou reste absent jusqu'à l'intégration backend.
- Les vues des entreprises ne doivent pas inventer l'absence de site. Avec POI Google natifs, impossible de filtrer globalement sans récupérer/qualifier les fiches ; désactiver ce filtre plutôt que simuler.
- Le mode 100 % est décidé après tests UI Windows sur desktop/mobile, mesures RTX 3060 et vrais processus de création/livraison ; CI seule ne garantit pas la qualité artistique.

## Surfaces réellement introduites dans la première itération (Build 295)
| QCM | État | Preuve concrète | À achever |
|---|---|---|---|
| 01 Identité globale | Partiel | Variables QCM violet/cyan, surfaces sombres, SVG existants | Thème clair/auto système, kit complet de composants |
| 02 Accueil | Intégré, QA visuelle restante | Orbites, deux destinations cliquables, mini scènes animées, vrais projets récents | Tests de composition sur tous formats, activité dédiée |
| 03 Navigation | Partiel | Dock bas, vraies routes, Ctrl+K, accessibilité, NSFW exclu | Panneaux latéraux, notifications et paramètres globaux |
| 04 LocalAiWeb chat | Partiel | Split redimensionnable 32 %, enregistrement, vrai renommage API, code via API | Pièce jointe, processus ouvrable, contrôles du prompt |
| 05 Carte de prospection | Partiel | Carte Google sombre si configurée, tiroir de prospects, recentrage et filtre documenté sur données publiques | Fiche native Google Places UI Kit, qualité filtres natifs |
| 06 Fiche entreprise | Partiel | Badge vrai statut, lien fiche d'origine, cible → brouillon existant | Favori/notes CRM, expérience Google officielle détaillée |
| 07 Éditeur du site | Partiel | Split, modes PC/tablette/mobile, source réelle, édition nom, rail Pages/Médias/Versions, restauration confirmée, menu ⋯ ZIP | Vérifier parcours Figma, édition directe, panneau Design, thumbnails des versions |
| 08 Projets Web | Partiel | Onglets Pro/Libres, vraie tuiles + via API, recherche existante | Timeline, archivage et nouvelles actions projet |
| 09 Commercial | Conservé | Parcours publier/CRM/devis existant | Assistant 3 étapes cohérent après publication |
| 10 Vision | Partiel | Aperçu du vrai rendu, chat/aperçu séparables, modes actifs, mobile | Diagnostiques UI, file d'attente, retouche fiable |
| 11 Photo | Conservé | Modèles et styles existants | Variantes, comparaison 2x2, upscale, correction guidée |
| 12 Vidéo / Cinéma | Conservé | Hunyuan 1.5 T2V/I2V, boutons existants | Storyboard, timeline réelle, contrôles physiques réels |
| 13 Retouche | Conservé | Pipeline et outils historiques | Vérifier masques/inpainting et historique non destructif |
| 14 Espace NSFW | **Ne pas modifier** | Aucun fichier adult/NSFW ni règles de génération modifiés dans la refonte | Uniquement correctifs généraux demandés ultérieurement |
| 15 Bibliothèque Vision | Conservé | Sauvegardes et affichage existants ; recherche locale, grille/liste et viewer public reliés aux fichiers | Tags/projets, export avancé et réutilisation des réglages (recherche et viewer public déjà ajoutés) |
| 16 Modèles/LoRA | Conservé | Réglages LoRA/import dans Vision existants | Vérification paramètres effectifs, statuts compatibles |
| 17 Chargements | Conservé | Progression vraie, code de reprise existants | Examen des montants estimés vs mesurés, erreurs, audio |
| 18 Mobile | Partiel | Dock bas, grille home, onglets Vision, carte responsive | Tests tactiles/rotation/clavier virtuel sur iPhone |
| 19 Agents/autopilot | **Non intégré** | Fonctionnalités futures absentes de l'UI | Orchestrateur stable, QA Codex, Client Portal, Brand DNA |

## Tests d'acceptation minimaux du Build 295
- [ ] Vue 1440×900 : orbites sans collision, liens/animations réels.
- [ ] Vue 390×844 : grille empilée, dock 48 px, tous les boutons accessibles.
- [ ] Web éditeur : drag + flèches redimensionnent durablement ; renommer → API persiste ; code → vrais fichiers.
- [ ] Projets : « Pro / Libres », recherche, création via la bonne action, dossiers intacts.
- [ ] Carte : France, zoom et recentrage ; clic métier, fiche, origine, création ; pas de filtre mensonger Google.
- [ ] Vision standard : photo/vidéo générées, preview reflète les vrais résultats ; navigation et retour.
- [ ] NSFW : aucune modification visuelle, aucune action ou miniature affichée hors de son espace.
- [ ] Exécutable Windows : build, smoke test, mise à jour, conservation données et workflows.

## Étapes suivantes, sans fausse promesse de 100 %
1. Rendre tous les écrans secondaires cohérents avec la direction artistique approuvée.
2. Ajouter uniquement les fonctions réellement opérationnelles : bibliothèque média, pages/sections, historique, retouche, cinéma.
3. Industrialiser QA navigateur et feedback visuel du site avant de valider Codex.
4. Régler et mesurer les modèles ComfyUI et LoRA sur RTX 3060 12 Go.
5. Installer le workflow CRM/Brand DNA/portail et publication validée.
