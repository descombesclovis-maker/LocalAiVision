# LocalAiWeb pour iPhone — séparation de l'application Windows

## Livré dans cette branche

- Manifeste PWA distinct **LocalAiWeb**, page de départ `/localaiweb`, sans afficher LocalAiVision comme application d'accueil.
- Vue mobile **Conversation / Aperçu** plein écran pour utiliser l'éditeur, la sélection d'éléments et les vues ordinateur/tablette/iPhone.
- Ouvrir le site généré dans Safari plutôt que demander au serveur Windows d'ouvrir un navigateur sur le PC.
- Recherche Pro / Libre et carte d'entreprise inchangées ; accès rapide aux champs de recherche mobile.
- Compatibilité avec l'application Windows existante ; aucune migration ou suppression de données.
- Tests de contrat sur les routes et le manifeste.

## Important — ne constitue pas encore un service cloud autonome

L'interface actuelle utilise `/api/web/*`, des fichiers et des agents exécutés par le serveur Windows.
Déployer seulement le HTML/CSS/JS sur Vercel ferait échouer la génération, la carte Pro, la
publication et la récupération des projets. **Ne pas présenter cette branche comme une solution
complète PC éteint.** Les médias et les sauvegardes ne sont pas copiés depuis le PC inaccessible.

### Conditions indispensables pour une version 100 % iPhone / PC éteint

1. Héberger les pages, l'authentification et le routage sur HTTPS (Vercel ou équivalent).
2. Déployer une API compatible `/api/web/*` avec une file de tâches, logs et annulation.
3. Mettre en place Supabase Auth + RLS et stockage privé pour séparer projets Libre / Pro,
   utilisateurs, historiques, images et versions. Faire une migration testée avant toute écriture.
4. Exécuter Codex/Claude **dans un moteur cloud autorisé**, ou une API de modèle cloud
   explicitement configurée ; ne pas déduire d'un abonnement ChatGPT l'accès à une API payante.
5. Héberger les builds npm et tests de navigateur dans un worker isolé avec limites, aucun secret
   dans le code produit, et revues avant publication Vercel.
6. Pour les photos créées automatiquement, ajouter un moteur d'image cloud (API ou GPU),
   ou maintenir une option sans génération tant qu'il n'est pas provisionné.
7. Protéger les prévisualisations de sites non fiables sous un domaine isolé, et ne pas servir
   des scripts produits sur le même origin que les sessions/authentifications.
8. Vérifier coûts et conditions d'usage avant toute création de services facturables.

## Installation, quand un backend compatible fonctionne

Ouvrir l'URL HTTPS depuis Safari sur iPhone : Partager > Sur l'écran d'accueil.
Le lancement affiche uniquement la bibliothèque **LocalAiWeb**.

## Tests

`python -m unittest tests.test_localaiweb_iphone -v`
`node --check local_app/web/localaiweb-mobile.js`
`python -m unittest discover -s tests -v`
L'absence d'accès à un navigateur iPhone réel et au GPU distant empêche encore les tests de bout en bout.
