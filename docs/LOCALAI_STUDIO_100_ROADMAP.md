# LocalAI Studio — feuille de route d'aboutissement à 100 %

Mis à jour : 2 novembre 2026 — audit du code et création de la branche 293.
**Les pourcentages ci-dessous sont des estimations de maturité produit, PAS des résultats de tests sur GPU et PAS une moyenne de réussite.** Ils servent à prioriser les travaux, et ne doivent pas être affichés comme une qualité visuelle mesurée. À 100 % seulement lorsqu'un test sur Windows/RTX 3060 confirme la totalité des critères.

## Vision produit (non négociable)
Un logiciel professionnel unique combinant **LocalAiWeb**, créateur de sites véritablement originaux, responsive, multi-pages, animés et commercialisables, et **LocalAiVision**, atelier local de photos, retouches, publicités et vidéos de qualité photographique, avec modèles et LoRA adaptés. Depuis la découverte d'un petit commerce jusqu'à une maquette de site vérifiée, publiée puis une proposition commerciale et ses publicités, le parcours doit être cohérent, fluide, rapidement exploitable, avec projets persistants et deux univers séparés. RTX 3060 12 Go, utilisation PC prioritaire. Les fonctions doivent agir réellement et ne pas se résumer à des boutons.

## Avancement initial estimé
| Domaine / capacité | Maturité estimée | Critère concret avant 100 % |
|---|---:|---|
| Lanceur / navigation entre 2 univers | 85 % | Rendu vérifié sur écran Windows, mobile, clavier, thèmes et liens |
| Animations d'accueil / logos pro | 70 % | Validation esthétique manuelle + performance/reduced-motion |
| Conversations IA locales | 65 % | Tests sur installation Qwen, streaming, interruption/reprise |
| Photo T2I (RealVisXL et HunyuanImage 2.1) | 60 % | Galerie étalon et absence de défauts sur 3060 |
| Vidéo T2V HunyuanVideo 1.5 | 45 % | Inférence réelle, VRAM, débit, rendu 10 s et continuité |
| Vidéo I2V HunyuanVideo 1.5 | 43 % | Vidéos à partir d'une vraie image, fidélité du sujet |
| Retouche image / inpainting | 28 % | UI complète de masque, génération, avant/après |
| Gestion LoRA / compatibilité | 55 % | Vérifier insertion sur modèles disponibles et refus propre des incompatibles |
| Styles graphiques / préférences | 60 % | Chaque réglage testé et relié aux nœuds ComfyUI réels |
| Réglages vidéo fps / durée / dimensions | 64 % | Contrôles round-trip / métadonnées sortie sur machine réelle |
| Progression réelle et aperçu intermédiaire | 72 % | Comparaison à événements ComfyUI pendant un rendu |
| Historique / bibliothèque de créations | 78 % | Persistance lors de redémarrage / mise à jour / interruption |
| Espace adulte avec code/session et galerie isolée | 63 % | UX, isolation, contrôle d'accès réel serveur si nécessaire |
| Publicité photo / vidéo liée à la marque | 62 % | Formats 9:16/1:1/16:9, logo vérifié, export, campagne liée |
| Création de sites avec Codex | 60 % | Connexion stable, génération conforme, code/fichiers livrés |
| Direction artistique et animations sites Codex | 48 % | Exemples concrets variés, contrôle navigateur, qualité visuelle par métier |
| Sites multipages et navigation réelle | 70 % | Parcours testé sur sites e-commerce/services, navigateur PC/mobile |
| Aperçu site desktop/tablette/téléphone | 75 % | Playwright actif sur Windows, captures + corrections |
| 3D/WebGL/qualité cinématique de sites | 40 % | Three.js/WebGL réel, performances mobiles, vrais assets |
| Photos produites automatiquement pour les sites | 50 % | Textures adaptées au secteur, licence, galerie injectée au code |
| Carte interactive France / source publique | 65 % | Grande couverture réelle, stabilité, pas de faux « sans site » |
| Google Maps officiel / fiches Places | 45 % | Compte facturable + clés valides, test réel carte native, attributions |
| Sélection ciblée entreprise et démarrage projet Pro | 65 % | Fiche choisie, brouillon isolé, autorisations/attributions correctes |
| 5 prospects recommandés chaque jour | 58 % | Choix fondé sur critères explicites, pertinentes et vérifiables |
| Publication Vercel/GitHub | 70 % | Déploiement réel en production et liens fonctionnels, rôle/consentement |
| Devis / factures / CRM après publication | 55 % | Flux commercial de bout en bout, prix/montants validés et pertinents |
| Tâches préservées lorsque l'on change d'écran | 72 % | Relance et rétablissement après crash/déconnexion |
| Mises à jour Windows automatiques | 85 % | Mises à jour réelles d'un PC de test avec données conservées |
| Support mobile iPhone (priorité différée) | 40 % | Tests iPhone sur carte, édition et accès distant lorsque PC allumé |
| Diagnostic autonome / connexions / résilience | 60 % | Tests de panne Codex/ComfyUI, reprise sans perdre de projet |

**Attention :** l'approbation CI Windows garantit seulement compilation, tests unitaires et fumée de l'exécutable. Elle ne garantit ni vitesse de rendu, ni réalisme photo/vidéo, ni qualité créative Codex.

## Critères de réception généraux
1. **Fonctionnel :** aucun bouton inerte, chaque option modifie réellement son pipeline ; tests de sortie.
2. **Qualité :** pour chaque type de contenu, galerie de cas représentatifs, sans artefacts, déformations, erreurs de langue ou de marque ; validation humaine de référence.
3. **Performance :** profil RTX 3060 12 Go, mémoire mesurée, aucun redémarrage forcé/plantage en production normale. Ne pas promettre des durées irréalistes sans mesure.
4. **Design :** interface cohérente, micro-interactions cinématiques maîtrisées, réduit-motion, accès clavier, responsive, pas d'images externes fragiles.
5. **Fiabilité :** génération persistante, reprise après fermeture de page / panne, sauvegardes séparées, installation et update reproductibles.
6. **Professionnalisation :** vrais commerces et données attribuées ; Google Maps via APIs officielles avec facturation et règles d'affichage, jamais une copie illégitime de la fiche.
7. **Commercial :** lancement des outils devis/publicité après publication vérifiée ; statut réel et usage conforme pour les brouillons Pro.
8. **Déploiement :** GitHub Actions vert + build Windows vérifié + test manuel métier avant tout « 100 % ».

## Priorité du prochain cycle après 293
1. **Mesurer sur RTX 3060** les pipelines HunyuanPhoto/HunyuanVideo T2V/I2V à partir de vrais fichiers et journaliser VRAM, étapes, FPS, temps et artefacts.
2. **Codex** : gabarits de composants originaux et non-copiés, contrôle navigateur Playwright sur les premières maquettes, réparation ciblée des défauts constatés.
3. **Google Maps** : connecter les deux clés Google Maps Platform/Places avec facturation contrôlée ; vérifier les limites de conservation des données Google et le résultat des clics natifs.
4. **Retouche** : rendre l'inpainting et les masques aussi fiables que T2I, et ajouter un véritable avant/après.
5. **CRM/publicité** : enchaîner publication autorisée → publicité → devis lié au projet, avec prix justifiables et historique.
