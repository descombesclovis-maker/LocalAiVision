# LocalAiWeb — Codex avec ChatGPT Plus et Signature 3D

## Ce qui est intégré
- **Codex CLI devient le moteur de génération par défaut**, pour tous les nouveaux projets Pro/Libre.
- Les projets antérieurs qui avaient reçu Claude **par défaut** basculent vers Codex lors de leur prochaine génération. Aucun fichier de site n'est remplacé par la migration. Claude reste disponible si choisi explicitement dans le sélecteur de l'éditeur.
- **Sélecteur d'agent** en haut de l'éditeur : Codex · ChatGPT Plus ou Claude Code (facultatif).
- **Bouton de connexion** de l'agent choisi en haut du studio et sur la bibliothèque des projets. Il vérifie si le CLI est installé et connecté ; il ouvre la connexion, sans installer ni acheter automatiquement.
- **✦ Signature 3D** en bas à gauche du champ de création, à côté du statut du chat : active/désactive une direction artistique immersive enregistrée dans les réglages du projet. Cela modifie les instructions effectivement envoyées à Codex et à Claude. Les modèles GLB fournis sont conservés. Si aucun modèle 3D n'est fourni, le brief autorise des géométries procédurales réellement calculées en WebGL.
- Les tests existants analysent le code, compilent le projet et, si un navigateur est disponible, réalisent des captures desktop, tablette et mobile ; l'agent peut réviser les fichiers sur la base de ces captures. Une inspection indisponible reste signalée, jamais comptée comme réussie.

## Pour rendre Codex opérationnel sur Windows

La connexion passe par le **CLI local** et le navigateur. ChatGPT Plus inclut l'utilisation de Codex dans les limites du forfait ; **ce n'est pas une clé API OpenAI**.

1. Installer Node.js LTS (si absent) : ouvrir PowerShell et exécuter
   `winget install OpenJS.NodeJS.LTS`
2. Fermer et rouvrir PowerShell pour rafraîchir le PATH.
3. Installer Codex CLI :
   `npm.cmd install -g @openai/codex`
4. Confirmer :
   `codex.cmd --version`
5. Authentifier le compte qui possède ChatGPT Plus :
   `codex.cmd login`
   puis terminer la connexion dans le navigateur.
6. Contrôler :
   `codex.cmd login status`
7. Mettre à jour LocalAiVision avec la dernière archive Windows depuis les releases GitHub, fermer l'ancienne application et lancer la nouvelle version.
8. Ouvrir **LocalAiWeb**, puis ton projet. En haut sélectionner **Codex · ChatGPT Plus**. Le bouton d'agent doit afficher **● Codex connecté**. Sinon, clique dessus pour refaire la connexion. Si le CLI vient d'être installé, redémarre LocalAiVision afin de mettre à jour son environnement.
9. Pour une démonstration immersive : activer **✦ Signature 3D** puis envoyer un brief concret contenant le métier, la cible, les couleurs, le style, les pages nécessaires, les animations attendues, les éventuels fichiers 3D/visuels autorisés et la contrainte mobile.
10. Le résultat s'affiche dans l'aperçu. Corrige par messages successifs en indiquant précisément les anomalies visuelles. L'audit depuis la fiche client peut contrôler la structure et des règles techniques, pas certifier la beauté visuelle.

### Exemple de premier brief
« Crée un site premium de parfumerie artisanale, en français, avec une direction artistique sombre et cuivrée, une bouteille 3D interactive construite avec une géométrie procédurale si aucun GLB réel n'existe, une ouverture cinématique avec éclairages crédibles, transitions GSAP/scroll, pages accueil, collection, histoire et contact. La navigation doit fonctionner, le rendu mobile rester fluide, et prefers-reduced-motion doit être respecté. Si une réservation ou un paiement n'a pas de backend réellement connecté, indique-le clairement plutôt que de simuler sa réussite. »

### Dépannage
- **« Installer Codex »** : installer Node et Codex CLI comme ci-dessus. Le bouton n'exécute aucun installateur à ta place.
- **« Connecter Codex »** : exécuter `codex.cmd login` et vérifier `codex.cmd login status`. Aucun paiement API séparé requis pour l'authentification avec ChatGPT.
- **Installation reconnue dans PowerShell mais pas dans LocalAiWeb** : fermer intégralement l'app et la rouvrir. Vérifier le même compte Windows.
- **Limite d'utilisation atteinte** : le forfait ChatGPT Plus a des quotas. Attendre leur rétablissement ou choisir volontairement un autre agent disposant de ses propres droits.
- **Le site manque de qualité** : fournir une direction plus précise, de vrais visuels (et modèles GLB si nécessaires), activer Signature 3D uniquement lorsque la 3D apporte quelque chose, corriger avec le chat et consulter les vérifications visuelles. Aucun modèle ne garantit la qualité exacte d'une vidéo de référence dès le premier rendu.
- **Qwen et ComfyUI** : moteurs indépendants, localement installés pour le texte, les photos et vidéos. Connecter Codex ne les démarre pas.
- **Confidentialité** : les prompts et extraits de code transmis par Codex peuvent être traités sur les serveurs d'OpenAI. Ne pas placer de secrets/API keys dans le code du site ni demander au CLI de les afficher.

Ne jamais activer une facturation API ou installer un abonnement Claude implicitement. Les projets, les devis, les clients et les fichiers déjà enregistrés sont conservés.
