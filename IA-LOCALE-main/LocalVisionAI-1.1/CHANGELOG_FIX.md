# Correctifs 1.1

- Interface disponible avant l’installation des moteurs ; ping indépendant, progression, reprise, journaux, mode navigateur de secours.
- Lanceur direct ComfyUI via son Python embarqué ; aucune relance récursive de l’EXE ; un seul démarrage moteur à la fois.
- Chat réel via llama.cpp avec historique, budget de contexte, erreurs lisibles, mode CPU par défaut et libération du processus géré avant les médias.
- Routage des demandes corrigé ; choix manuel Discussion / Image / Vidéo / Retouche.
- Imports stockés durablement, listés et rechargeables ; noms distincts en cas de doublon.
- Réglages du workflow conservés par défaut, presets différenciés, seed zéro et température zéro utilisables.
- Réparation du décalage des widgets liés ; exclusion des nœuds désactivés ; traitement des reroutes ; explication pour les sous-graphes nécessitant Export API.
- Contrôle des modèles manquants avant la soumission ; affichage des sorties vidéo et des erreurs, fin d’attente sur tâche disparue.
- Workflow de retouche SDXL avec masque peint et recomposition de la zone non masquée.
- Workflow Wan texte vers vidéo ; choix automatique de Wan image lorsqu’une image est jointe.
- Galerie de six styles, choix automatique des workflows disponibles, aperçu remplaçable par un résultat local.
- Téléchargements SDXL et Wan depuis l’interface ; aucun changement aux protections internes des modèles.
- Tests et notice d’installation inclus. Livraison des sources et BAT, sans nouveau binaire Windows compilé.

## Correctif 2026-10-05 — llama.cpp / Wan
- L'installateur llama.cpp ne dépend plus uniquement de `releases/latest` : il parcourt aussi les versions récentes/préversions, où les binaires Windows x64 sont effectivement publiés.
- Le chat indique maintenant explicitement si `llama-server.exe` ou le GGUF manque.
- Les gros téléchargements (dont Wan) affichent immédiatement « connexion au serveur… » avant le premier bloc reçu.


## 1.2.0 — rapidité et retour visuel
- Le chat s’affiche désormais mot par mot au lieu d’attendre la réponse complète.
- llama.cpp préfère automatiquement CUDA 12.4 sur Windows x64, puis Vulkan, puis CPU.
- Les anciennes installations CPU sont mises à niveau automatiquement au prochain démarrage.
- Qwen3 utilise toutes les couches GPU disponibles avec un backend CUDA/Vulkan.
- Le chargement du chat affiche explicitement « Préparation du modèle local… ».
- Les téléchargements affichent maintenant aussi la durée écoulée, même avant le premier octet.

## 1.3.0 — conversation naturelle, mémoire et typographie
- Le champ de saisie perd le focus après l’envoi afin de fermer le clavier tactile.
- Pendant l’attente, un indicateur discret affiche « LocalAiVision vous répond… ».
- L’historique textuel complet de la conversation est renvoyé au modèle ; les anciens messages ne sont écartés que lorsque la fenêtre de contexte l’exige.
- La fenêtre de contexte par défaut passe de 8 192 à 16 384 tokens pour mieux conserver le fil des échanges.
- Nouveau prompt système : ton plus naturel, réponses moins scolaires, solutions concrètes proposées spontanément, continuité conversationnelle, prudence factuelle et émojis modérés.
- Rendu typographique du Markdown local : titres, listes, `code` et **gras** s’affichent réellement au lieu de montrer les marqueurs bruts.
- Le rendu progressif de la réponse est regroupé par image d’animation afin d’éviter de reconstruire le texte à chaque token.
- Les instructions personnalisées déjà modifiées par l’utilisateur sont conservées ; seule l’ancienne instruction système par défaut est migrée.

## 1.4.0 — chat réparé, réponse visible et arrêt manuel

- Correction du flux du chat : la bulle de réponse est créée dès le premier fragment reçu, au lieu de rester invisible pendant que Qwen génère côté serveur.
- Pendant une réponse, la zone de saisie se masque et affiche discrètement « LocalAiVision vous répond » ; le champ perd le focus pour fermer le clavier tactile.
- Les trois points animés restent visibles dans le fil avec une petite croix discrète juste dessous pour interrompre la réponse.
- Ajout d’un arrêt côté serveur (`/api/chat/stop`) pour fermer proprement le flux llama.cpp, en plus de l’annulation côté navigateur.
- Le texte est affiché immédiatement en flux brut puis remis en forme à la fin (gras, titres, listes), ce qui évite les coupures dues au rendu Markdown pendant la génération.
- La limite de réponse par défaut passe à 2 048 tokens pour réduire les réponses coupées lors des demandes détaillées.


## v1.5 — rendu emoji
- Les réponses utilisent les glyphes Apple Color Emoji quand ils sont réellement présents sur le système.
- Sous Windows/Linux, les emoji du texte final sont remplacés par un rendu 3D cohérent au lieu du style Windows natif, avec repli local si l’asset réseau n’est pas disponible.
- Le texte, le gras, les listes et le streaming restent inchangés.


## 1.6.0 — générateur photo auto-réparé
- SDXL est vérifié et installé automatiquement au démarrage si le checkpoint manque.
- Une génération photo/retouche/vidéo répare automatiquement un modèle média absent avant d’échouer.
- Une demande envoyée pendant l’installation attend la fin au lieu d’obliger à renvoyer le prompt.
- Le statut distingue maintenant photo prête / à préparer et vidéo prête / à préparer.
- La progression du téléchargement apparaît directement dans la bulle de génération.
- Le cache ComfyUI des modèles est invalidé après installation et l’instance gérée par LocalVisionAI peut être redémarrée une fois pour forcer la détection.

## v1.7 — routage création visuelle naturel

- Les demandes visuelles n’ont plus besoin de contenir explicitement « photo » ou « image ».
- « Génère-moi une femme… », « dessine un chat… » ou « fais un portrait… » partent directement vers SDXL.
- Les demandes textuelles (« génère un résumé », « crée une liste ») restent dans le chat.
- Le moteur image n’est plus remplacé par un refus du modèle conversationnel quand l’intention visuelle est claire.

## 1.8.0 — fidélité du prompt photo
- Un médium explicitement demandé dans le texte (photo, aquarelle, BD, 3D, illustration, cinéma) prend désormais le dessus sur un ancien style graphique encore sélectionné dans l'interface.
- Une demande contenant « photo » ne peut plus hériter silencieusement du style Aquarelle d'une génération précédente.
- Pour une demande de nudité adulte sans cadrage précisé, le prompt de travail précise adulte 25+ et plein pied afin d'éviter le faux résultat portrait/épaules.
- En mode photo, un négatif automatique écarte aquarelle, dessin, illustration et cadrages coupés lorsque l'utilisateur n'a pas fourni son propre négatif.


## 1.9.0
- Remplace SDXL Base pour la photo par RealVisXL V5.0 FP16.
- Réglages photo: DPM++ SDE Karras, 35 étapes, CFG 5.5.
- Renforce les contraintes de cadrage (de face/de dos/grand-angle) et l'anatomie des mains.
- Le style Photoréaliste choisit en priorité le workflow RealVisXL.


## v2.0 — Modèles réservés
- Section rouge « Modèles réservés » dans le menu de gauche.
- Profil Companion Réaliste basé sur RealVisXL V5.
- Profil Companion Anime basé sur Animagine XL 4.0, téléchargé seulement à la première sélection.
- GLM-4.6 Derestricted v3 référencé comme modèle texte expérimental, avec avertissement matériel (357B).
- L'interface ne prétend pas utiliser le checkpoint propriétaire exact de Candy.ai : ses pages publiques décrivent des modes Realistic/Anime sans publier le nom du modèle sous-jacent.

## v2.1 — Sélection automatique, conversations par modèle et mouvement vidéo

- Le thème rouge des profils a été supprimé.
- Le chatbot Qwen est conservé.
- Cliquer un profil du menu Modèles crée une nouvelle conversation dédiée.
- Les workflows peuvent être remplacés dans Paramètres sans changer de conversation.
- Le mode Automatique choisit RealVisXL, Animagine, Wan ou VACE selon la demande et les pièces jointes.
- Les prompts utilisateur restent intacts ; seules les indications techniques de qualité et les styles explicitement choisis peuvent être ajoutés séparément.
- Aucun classificateur NSFW ni safety checker n'a été ajouté au pipeline de génération.
- Ajout de Wan VACE 1.3B pour vidéo → vidéo guidée par une vidéo de mouvement et une image de référence.
- Ajout du bouton de pièce jointe vidéo.
- Ajout de la suppression discrète et du renommage des conversations et des éléments de bibliothèque.
- Ajout du renommage local des profils et workflows.
- Les téléchargements `.part` existants continuent d'être repris avec requêtes HTTP Range.
