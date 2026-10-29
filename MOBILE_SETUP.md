# LocalAiWeb sur iPhone — installation unique et mises à jour automatiques

## Fonctionnement

LocalAiWeb est une application web installable (PWA), avec sa propre icône et sa page d'accueil. Les projets, le CRM et les données restent sur le PC. Les interfaces web affichées sur le téléphone se rafraîchissent automatiquement à la réouverture, sans installer d'autre application iPhone. Le moteur de génération (Codex, ComfyUI, GPU) continue de tourner sur le PC Windows : le téléphone ne fait qu'afficher l'interface et envoyer les commandes.

**Conditions :** PC allumé, sortie de veille désactivée, connexion Internet, LocalVisionAI.exe en fonctionnement, tunnel Tailscale privé sur les deux appareils. Pas de connexion avec le PC éteint. Ne pas confondre mise à jour de l'interface web et mise à jour du programme Windows : les nouveautés GitHub ne sont visibles sur iPhone qu'une fois la version Windows mise à jour sur le PC.

## Installation une seule fois

1. Sur le PC, installer la version Windows récente à partir de https://github.com/descombesclovis-maker/LocalAiVision/releases/latest. Extraire l'archive ZIP : elle inclut LocalVisionAI.exe, ACTIVER_ACCES_TELEPHONE.bat et MOBILE_SETUP.md.
2. Démarrer **LocalVisionAI.exe**, laisser sa fenêtre ouverte et vérifier sur Windows : http://127.0.0.1:3000/localaiweb
3. Installer Tailscale pour Windows : https://tailscale.com/download/windows ; ouvrir l'application et se connecter avec un compte privé.
4. Installer Tailscale sur l'iPhone via l'App Store ; se connecter avec le même réseau privé (tailnet), puis activer Tailscale dans l'application.
5. Sur le PC, double-cliquer **ACTIVER_ACCES_TELEPHONE.bat**, confirmer l'activation. Il appelle `tailscale serve --bg 3000`, **jamais** `tailscale funnel`. Si Tailscale demande d'activer HTTPS, suivre le lien de configuration officiel affiché.
6. Lire l'adresse HTTPS privée indiquée par `tailscale serve status`, en forme `https://nom-du-pc.nom-du-tailnet.ts.net`. Depuis **Safari sur l'iPhone**, ouvrir **cette adresse suivie de `/localaiweb`**. L'URL http://127.0.0.1:3000 ne fonctionne que sur le PC.
7. Safari → **Partager** → **Sur l'écran d'accueil** → activer « Ouvrir comme app web » si cette option est proposée → **Ajouter**. Ouvrir ensuite l'icône LocalAiWeb.

## Mises à jour

L'icône reste installée : chaque ouverture de l'app va chercher les pages et scripts récents sur le PC. Les caches obsolètes sont retirés, les informations de projets ne sont jamais mises dans le cache hors ligne. En cas de nouvelle version du serveur pendant une session, l'application recharge à la réouverture/au retour au premier plan ; si un champ de saisie est actif, elle propose d'actualiser après la saisie.

Pour bénéficier des changements que nous publions sur GitHub, **mettre à jour LocalAiVision sur le PC** avec son mécanisme existant. Le téléphone charge ensuite la nouvelle version sans réinstallation. Il n'y a pas d'app native ni de synchronisation indépendante des fichiers depuis un serveur cloud.

## Fluidité et limites honnêtes

L'interface mobile propose un affichage plein écran basculant entre chat et aperçu, afin d'éviter deux panneaux minuscules superposés. La génération utilise la GPU du PC, pas celle du téléphone. Une scène WebGL/3D dans l'aperçu peut cependant utiliser le processeur graphique de l'iPhone : ses performances dépendront du site généré, de la qualité du réseau et du modèle d'iPhone. Les prévisualisations restent les vraies pages générées et ne sont pas remplacées par des captures.

Une connexion privée Tailscale ne doit être partagée qu'avec des appareils de confiance : LocalAiVision possède des opérations de gestion de projets et de fichiers sensibles. En cas de perte de l'iPhone ou de partage du compte Tailscale, révoquer l'accès dans l'administration Tailscale. Pour fermer l'accès, sur le PC exécuter `tailscale serve reset`.

## Dépannage rapide

- L'adresse ne fonctionne pas : vérifier que LocalVisionAI.exe est ouvert, que `/api/ping` fonctionne depuis le PC, que Tailscale indique « connecté » sur les deux appareils, et que le PC n'est pas en veille.
- La PWA reste ancienne : mettre à jour le logiciel PC, fermer puis rouvrir l'icône sur iPhone ; vérifier l'identifiant build retourné par `/api/ping`.
- Une page 3D saccade : réduire les effets/chargements **dans le site généré**, sans affecter la résolution des fichiers ou les réglages de génération PC.
