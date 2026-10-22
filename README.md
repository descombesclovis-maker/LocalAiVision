# LocalAiVision 3.1 — Photo/Vidéo, NSFW et LocalAiWeb

Une seule application Windows, avec des espaces de création séparés :

- **Photo/Vidéo** : chat local Qwen, ComfyUI, génération d’images et de vidéos, styles et workflows.
- **NSFW** : espace de conversation et bibliothèque distincts, profils Hunyuan et paramètres isolés.
- **LocalAiWeb** : projets Libre et Pro, chat de développement avec Codex prioritaire, prévisualisation responsive, génération 3D via de vrais composants lorsqu’elle est demandée, export et publication explicite.

## Accès aux fonctionnalités

Sous Windows, lancer `START_LOCAL_AI.bat` depuis le projet source ou l’EXE distribué. Le bouton LocalAiWeb ouvre `/localaiweb`. Dans le chat de l’éditeur, le bouton **planète** ouvre la carte pour choisir une entreprise ; la première maquette Pro est ensuite générée automatiquement si un agent Code authentifié est présent.

La carte gratuite OpenStreetMap est disponible sans clé. Le mode Google Maps, avec sélection de fiches directement dans Google, est **optionnel et potentiellement facturé** par Google. Il nécessite deux clés Google API configurées manuellement. Voir [README_LOCALAIWEB_PRO_MAP.md](README_LOCALAIWEB_PRO_MAP.md).

Pour installer une **application web progressive sur téléphone**, voir [MOBILE_SETUP.md](MOBILE_SETUP.md) et le script `ACTIVER_ACCES_TELEPHONE.bat`. Une connexion privée HTTPS/Tailscale et le PC allumé sont nécessaires ; aucune application native App Store n’est promise.

Les consignes permanentes des agents et les règles de sécurité se trouvent dans [AGENTS.md](AGENTS.md). Les exigences de génération et le protocole de test figurent dans [README_LOCALAIWEB_HYBRID.md](README_LOCALAIWEB_HYBRID.md) et les tests de `tests/`.

## Tests

```
python -m unittest discover -s tests -v
node --check local_app/web/app.js
node --check local_app/web/localaiweb.js
node --check local_app/web/localaiweb-map.js
node --check local_app/web/pwa-install.js
node --check local_app/web/service-worker.js
```

Le passage des tests ne garantit pas le fonctionnement réel des modèles sur RTX 3060, ni la qualité esthétique de tous les sites. Des tests sur le PC et le téléphone sont indispensables.
