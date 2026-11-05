# Build 316 — Audit humain 1 : bilan technique

Date : 5 novembre 2026. Sources de départ : `8a3ea1704e571779a313fc88cc9b96505e28df61`.
Branche : `codex/studio-316-professional-overhaul`, PR #65 en brouillon.

## Défauts établis et corrections

| Constat dans les sources | Correction | Limite de validation |
|---|---|---|
| `intent.task` passait avant le choix Chat dans `sendMessage` | Le mode Chat donne une tâche nulle dès l’ouverture, avant la fin du diagnostic moteur ; accueil et accès Chat distincts ; historique conservé | Recette navigateur avec réponse explicitement simulée, pas preuve du modèle conversationnel |
| Le conditionnement public ajoutait systématiquement `accurate hands` et des instructions anatomiques | Suppression de ces ajouts positifs et négatifs génériques dans la branche publique uniquement | Cause plausible d'un biais de composition ; causalité dans les trois images non prouvée |
| La vidéo publique pouvait revenir silencieusement au workflow Wan si Hunyuan n'était pas déclaré prêt | Hunyuan est le choix public par défaut ; un autre workflow reste possible par sélection explicite | Le workflow réellement exécuté chez l'utilisateur reste à retrouver dans la provenance et les journaux |
| Le planificateur sélectionnait 12 FPS sans recalculer les 49 images du workflow en l'absence de durée | Base publique Hunyuan à 16 FPS / 3 secondes ; nombre d'images calculé avec contrainte `4n+1` | 49 / 16 = 3,0625 secondes ; une contrainte de frames peut ajouter jusqu'à quelques images à la durée demandée |
| Tous les échecs de `login status` devenaient `ready=false` sans cause | États séparés : absent, authentifié, reconnexion requise, délai dépassé, lancement impossible, vérification échouée ; sortie CLI brute non exposée | Une session utilisateur réelle, ses expirations et le réseau ne sont pas reproduits dans CI |
| Le statut de l'agent attendait l'inventaire de plusieurs services et modèles | Endpoint limité à l'agent choisi ; revérification sans effacer la session ; pas de changement de fournisseur | Le contrôle local de session ne garantit pas la disponibilité réseau d'une génération longue |
| La disparition des tâches pouvait afficher « terminé » | Invitation à vérifier le résultat ; composant commun plafonné avant validation du fichier ; état indéterminé sans faux compteur | Un pourcentage ComfyUI décrit l'étape de calcul courante, pas toute la chaîne |
| Les marques nécessitaient des accès et saisies peu visibles | Carte centrale persistante, sélection explicite dans Publicité et Web ; anciens projets inchangés par la sélection globale | Aucun service, tarif, produit ou caractère typographique absent de la fiche n'est inventé |
| L'upload du logo ne conservait qu'une version PNG normalisée | Conservation en plus des octets source, identifiés par SHA-256 ; aperçu/composition existants conservés | Les anciens uploads antérieurs ne peuvent pas être reconstruits à l'identique |

## Interface et continuité

- Logo au-dessus du texte dans un en-tête centré indépendamment des éléments latéraux ; activité dans l'en-tête public, menu natif conservé.
- Photo, Vidéo, Publicité et Chat gardent leurs accueils ; les changements n'effacent aucune discussion sauvegardée.
- Cercle SVG commun pour galerie, aperçu, activité et projets Web. Les phases Web donnent une estimation marquée « estimé » ; aucun minuteur ne simule une progression.
- L'aperçu Web peut être consulté pendant les finitions ; un aperçu compilé remplace l'animation. Les tâches continuent côté serveur lors de la navigation.
- Les marqueurs de génération enregistrent leurs identifiants pour que l'aperçu ne reprenne pas le pourcentage d'une autre conversation.
- L'accès complet aux marques passe par la carte Studio ; sélecteurs dans les outils et anciennes URL conservés.
- La marque globale est une préférence d'accueil. Les projets Web utilisent leur `brand_id` ; une publicité conserve son identifiant et une copie des informations sélectionnées dans sa conversation.
- Le pipeline Web existant transmet déjà la fiche et les couleurs à l'agent et copie le fichier de logo ; la publicité réutilise le compositeur existant pour superposer le vrai logo à une sortie distincte de l'original.

## Audit des moteurs

L'analyse porte sur les sources versionnées et leurs paramètres déclarés. Elle ne prouve pas que le PC a effectivement chargé les mêmes fichiers.

| Workflow | Paramètres présents dans les sources |
|---|---|
| RealVisXL V5 SDXL | 1024² natif ; KSampler 35 étapes, CFG 5,5, dpmpp_sde / karras ; VAE du checkpoint ; preset qualité public conservé |
| HunyuanImage 2.1 | Checkpoint distilled FP8 ; Qwen 2.5 VL + ByT5 ; VAE HunyuanImage ; 8 étapes, CFG 1, euler / simple ; résolution publique équilibrée planifiée à 1280² |
| HunyuanVideo 1.5 T2V | Checkpoint 480p CFG distilled FP8 ; VAE HunyuanVideo15 ; Qwen VL + ByT5 ; 50 étapes, CFG 1, shift 5, euler / simple ; latent 832×480 |
| HunyuanVideo 1.5 I2V | Checkpoint 480p step distilled FP8 ; VAE HunyuanVideo15 ; encodeur SigCLIP ; 12 étapes dans le graphe, CFG 1, shift 7 ; latent 832×480 |
| Wan 2.1 T2V | Variante 1.3B FP16, UMT5, VAE Wan ; workflow à 20 étapes, CFG 6, uni_pc / simple ; option explicite conservée |

La distinction CFG-distilled / step-distilled est cohérente avec les [configurations publiées par Tencent](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5#optimal-inference-configurations). Les workflows privés partagés ne sont pas modifiés pour accélérer un rendu public.

Aucun ajout de bokeh ou de profondeur de champ n'a été trouvé dans les enrichissements publics examinés. La mollesse des images peut également venir du modèle, de l'encodage du texte, du workflow sélectionné ou de traitements en aval : aucune attribution exclusive n'est établie.

La provenance existante enregistre le graphe soumis, les noms des modèles, les prompts et les paramètres. Les empreintes des poids, pics VRAM, temps d'inférence séparé du décodage et qualité temporelle exigent des mesures sur le PC. Un nom de fichier ne prouve pas son contenu.

## Validation disponible

- Linux : **372 tests Python exécutés, 2 ignorés** (tests Windows natifs) ; aucune erreur au dernier passage local.
- Node : tests des enrichissements photo, des états de progression et du suivi Web. Les contrôles navigateur sont réalisés séparément sous Windows dans GitHub Actions.
- Diagnostic de disponibilité ComfyUI exécuté ici : **indisponible, connexion refusée**, `executed=false`, `success=false`. Aucun rendu n'a été réalisé ni remplacé par une image illustrative.
- Pas de RTX 3060 dans cet environnement. Aucun gain de vitesse, de VRAM ou de qualité n'est revendiqué.
- Tests Windows préparés : lancement réel d'un `.cmd` de recette pour les états authentifié/expiré, compilation native, démarrage EXE, contrôles d'icône et de mise à jour, interactions Chromium/Edge et captures.
- Les réponses IA et événements de progression injectés pendant les tests d'interface sont identifiés comme fixtures dans leurs rapports ; ils ne valident pas une connexion Codex réelle ni un moteur GPU.

Le numéro technique et le commit du paquet proviennent de GitHub Actions. Consulter `build_info.json`, le manifeste embarqué et l'exécution correspondante. Produit 316 / version 3.1.6 et numéro d'exécution CI sont des identifiants distincts. Aucun ancien EXE n'est réutilisé.

## Reste à valider sur le PC cible

1. `codex login status`, diagnostic local, génération Web réelle, redémarrage, interruption réseau et reprise ; ne pas réinstaller l'agent pour un simple état indéterminé.
2. Les trois prompts photo exacts, mêmes seeds et réglages, comparaison des résultats et des provenances.
3. Le prompt vidéo exact en T2V à 3 puis 5 secondes. Essai 10 secondes seulement si les premiers rendus et la mémoire sont acceptables.
4. I2V avec une référence fixe conservée ; comparer identité, retournement, sourire, vêtements, anatomie et décor.
5. Décodage des sorties, FPS, durée, résolution, temps total et mesures mémoire. Ne pas confondre amélioration de minutage et amélioration visuelle.
6. Publicité avec logo réel : vérifier la composition finale et le téléchargement ; site Web avec marque : génération, compilation et export réels.
7. Fluidité avec la RTX 3060 réellement sollicitée ; la CI sans cette carte ne peut pas la certifier.

Voir `HUMAN_AUDIT_1_VALIDATION.md` pour les commandes. P0 Codex durable et qualité vidéo restent ouverts jusqu'à ces vérifications. Pas de fusion, de release ni de déploiement autorisé dans cette mission.
