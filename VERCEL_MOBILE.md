# LocalAiVision — interface Vercel (mobile)

L'application Windows originale sous `local_app/` reste inchangée. 
Ce déploiement compile et sert les pages web existantes avec leur interface responsive : 
`/` (Photo/Vidéo, NSFW), `/localaiweb`, `/localaiweb/editor` et `/localaiweb/map`.

**Important : ceci n'est pas une migration GPU.** Il n'y a pas de moteur ComfyUI / Qwen / Codex sur Vercel.
Les appels `/api/*` retournent volontairement une erreur explicite 503 tant qu'il n'existe pas de vrai backend.
La bannière dans l'interface signale ce mode aperçu. Aucun résultat généré n'est simulé.

## Architecture requise pour accéder à toutes les fonctions depuis un iPhone

1. Déployer un backend Windows GPU ou un serveur GPU cloud toujours accessible (ComfyUI, Qwen, Codex, projets et fichiers persistants).
2. Ajouter une authentification forte côté serveur, un contrôle d'accès par utilisateur, des limites de requêtes et une séparation des opérations sensibles. Les endpoints locaux actuels autorisent la création et la modification de projets et ne doivent pas être publiés directement.
3. Connecter la façade Vercel au backend via une passerelle authentifiée, comprenant des transferts de fichiers volumineux hors des limites de Vercel Functions, ainsi que des tâches asynchrones pour les vidéos.
4. Prévoir des stockages persistants pour modèles, médias, conversations et projets, et ajouter des tests iPhone / GPU.

Ne jamais exposer le port `3000`, changer `HOST=127.0.0.1` pour `0.0.0.0`, ni utiliser Tailscale Funnel pour contourner l'authentification.

Pour un accès **immédiat** avec toutes les fonctions présentes sur le PC, utiliser le tunnel privé Tailscale Serve documenté dans `MOBILE_SETUP.md` : le PC doit être allumé et le tunnel configuré depuis celui-ci, ou via un accès distant déjà installé.
