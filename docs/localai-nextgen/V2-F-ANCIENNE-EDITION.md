# V2-F — Neutralisation de l'ancienne édition : plan non exécuté

Périmètre concerné : `%LOCALAPPDATA%\LocalAiStudio-Editions\NextGen-Avant-Fusion`. **Ne pas exécuter ces actions sans autorisation explicite du propriétaire.** L'édition historique et ses bases n'ont pas été modifiées pendant V2-F.

## Risques constatés

- `tunnel-preview.bat` de cette édition lance des tunnels publics non authentifiés vers Ollama et ComfyUI. La même procédure reste présentée dans son interface et sa documentation. Aucun processus `cloudflared` n'était actif lors du contrôle ; cela ne garantit pas qu'il ne sera jamais lancé.
- Son backend sur 8001 n'a pas de middleware d'authentification et son CORS est `*`. Une requête sans cookie à `/api/kit/info` répond 200. L'écoute réseau était limitée à `127.0.0.1` lors du contrôle ; un site web local ou distant reste néanmoins une menace selon les capacités du navigateur et du proxy.
- Renommer uniquement le fichier de tunnel **ne sécurise pas** ce backend et ne retire pas les commandes de l'interface. Modifier seulement le CORS ne remplace pas une authentification.

## Plan à soumettre avant intervention

1. Confirmer l'absence de génération en cours et identifier les processus et leurs chemins exacts ; ne pas arrêter ComfyUI ou Ollama partagés. Demander une autorisation spécifique avant l'arrêt des services de l'ancienne édition (8001/3000).
2. Sauvegarder `tunnel-preview.bat` **hors de l'édition** sous une extension non exécutable, relever SHA-256 de la source et de la sauvegarde et vérifier qu'ils concordent. Préserver les droits, la configuration et la base de données.
3. Avec autorisation, renommer uniquement l'ancien `tunnel-preview.bat` en `tunnel-preview.bat.disabled` ; conserver le fichier original et sa sauvegarde. Vérifier que l'ancien nom n'existe plus et qu'aucun tunnel n'a démarré. Un éventuel raccourci de tunnel ne fonctionnerait plus.
4. Pour neutraliser réellement l'API non authentifiée, arrêter **après accord** les seuls processus de l'ancienne édition ; réidentifier PID et chemins au moment de l'action. Ne pas redémarrer le backend sur une base utilisateur sans autorisation : son démarrage peut modifier les statuts de travaux interrompus.
5. Après décision séparée, adopter une édition corrigée et indépendante. Ne pas écraser l'ancienne installation, migrer de base ou changer une configuration utilisateur sans accord et sauvegarde vérifiée.

## Retour arrière

Avec autorisation, renommer le fichier `.disabled` à son nom d'origine ; comparer sa somme SHA-256 à celle relevée avant intervention. Ce retour arrière réactive un script dangereux : ne pas le lancer. La sauvegarde est distincte de toute sauvegarde de base de données.
