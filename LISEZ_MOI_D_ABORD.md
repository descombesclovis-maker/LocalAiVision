# LocalVisionAI 2.1 — démarrage et utilisation

Cette archive contient la version source/lanceur Windows de LocalVisionAI. Elle réutilise les moteurs et modèles stockés dans `%LOCALAPPDATA%\LocalVisionAI` : ne supprime pas ce dossier si tu veux conserver Qwen, Wan et les téléchargements partiels.

## Démarrer

1. Ferme toute ancienne instance de LocalVisionAI (le port 3000 ne peut être utilisé que par une version à la fois).
2. Extrais entièrement le ZIP.
3. Lance `START_LOCAL_AI.bat`.

L’interface s’ouvre pendant la préparation des moteurs. Les fichiers `.part` sont repris automatiquement lorsque le serveur de téléchargement accepte la reprise. Ainsi, un téléchargement RealVisXL interrompu n’est pas volontairement recommencé à zéro.

## Chat et conversations

Le chatbot Qwen/llama.cpp est conservé. Les réponses sont affichées progressivement. Chaque conversation garde son historique local.

Dans la colonne **MODÈLES**, cliquer sur **Automatique**, **Companion Réaliste**, **Companion Anime** ou **Wan VACE 1.3B** crée une **nouvelle conversation** avec ce profil. Changer ensuite un workflow dans ⚙ **Paramètres** modifie seulement la conversation courante : aucune nouvelle conversation n’est créée.

Les petites icônes `✎` et `×` à côté des conversations servent à les renommer ou supprimer. Elles restent volontairement discrètes jusqu’au survol. Les noms affichés des profils et des workflows peuvent aussi être renommés localement.

## Sélection automatique des moteurs

En mode **Automatique**, LocalVisionAI choisit la tâche et le workflow d’après la demande et les pièces jointes :

- texte général → Qwen ;
- photo/rendu réaliste → RealVisXL V5 ;
- demande anime/manga → Animagine XL 4.0 ;
- texte → vidéo → Wan 2.1 1.3B ;
- image → vidéo → workflow Wan image-to-video ;
- image + vidéo de référence / demande de transfert de mouvement → Wan VACE 1.3B ;
- retouche avec masque → RealVisXL.

Les listes **Workflow image / vidéo / mouvement / retouche** dans ⚙ permettent de remplacer le choix automatique sans quitter la conversation.

## Fidélité du prompt

Le texte de ta demande est conservé tel quel. LocalVisionAI ne lui ajoute plus d’hypothèses d’âge, de vêtements, de pudeur, de pose, de cadrage ou de contenu. L’option **Amélioration technique neutre** ajoute seulement des indications de rendu (netteté, anatomie cohérente, mains, artefacts). Décoche-la pour transmettre uniquement ton prompt et ton éventuel prompt négatif.

Un style graphique choisi explicitement dans ⚙ reste volontairement un ajout de style. Un médium écrit directement dans le prompt (par exemple `photo` ou `aquarelle`) est prioritaire sur un ancien style mémorisé.

## Modèles média

- **RealVisXL V5 FP16** : photo/retouche. Le bouton `Installer / reprendre RealVisXL` reprend un `.part` existant.
- **Animagine XL 4.0** : génération anime/manga, téléchargée à la demande.
- **Wan 2.1 T2V/I2V 1.3B** : génération vidéo générale.
- **Wan VACE 1.3B** : vidéo guidée par une vidéo source et une image de référence. Le workflow inclus extrait les images de la vidéo puis applique un contrôle Canny pour reprendre sa structure et son mouvement avec des nœuds ComfyUI standards.

Pour **Mouvement vidéo**, joins une image du sujet avec `+`, joins la vidéo de référence avec `▶`, puis décris le résultat voulu. VACE 1.3B est réglé sur une voie 480p adaptée aux GPU grand public ; commence par des clips courts.

## Bibliothèque

Les bibliothèques Photos, Vidéos et Retouches affichent les résultats enregistrés. Une petite croix apparaît au survol d’une création : elle retire l’entrée de la bibliothèque et demande au serveur local de supprimer aussi le fichier dans `ComfyUI/output` lorsqu’il lui appartient.

## Mémoire GPU

Avant une génération média, LocalVisionAI arrête uniquement le serveur texte qu’il a lui-même lancé afin de libérer la VRAM. Il ne termine pas un processus externe. À la prochaine question de chat, Qwen redémarre à la demande.

## Journaux

Le bouton **Voir le journal** regroupe les dernières lignes de `startup.log`, `comfy.log` et `llm.log` dans `%LOCALAPPDATA%\LocalVisionAI\logs`.

## Construction EXE

`BUILD_LOCALVISIONAI.bat` permet de reconstruire l’EXE sous Windows. L’archive fournie ici contient surtout le code source et le lanceur ; `START_LOCAL_AI.bat` est la voie de test recommandée pour cette version.
