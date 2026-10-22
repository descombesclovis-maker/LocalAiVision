# LocalAiVision sur iPhone et Android — première version PWA

Cette version fournit un manifeste web, une icône, un service worker **pour les assets statiques seulement**, des interfaces adaptées aux écrans étroits et un bouton **Installer**. Elle n'est pas encore une application native App Store/Play Store.

## Où s'exécutent les générations ?

Le PC Windows reste le serveur LocalAiVision et exécute ComfyUI, Qwen et les agents de code. Le téléphone ne lance pas les modèles de plusieurs gigaoctets. Les dossiers de projets restent sur le PC.

## Important : accès réseau et sécurité

Le serveur écoute actuellement seulement sur `127.0.0.1:3000` **par sécurité**. Une URL `http://127.0.0.1:3000` ouverte sur l'iPhone désigne l'iPhone, **pas** le PC : elle ne peut pas fonctionner telle quelle.

Pour accéder au PC depuis l'extérieur, utiliser un tunnel privé avec authentification et HTTPS (ex. Tailscale Serve), qui pointe vers le serveur local. Installer/configurer ce tunnel **sur le PC** est une étape distincte non automatisée par cette branche. Ne jamais remplacer `HOST = "127.0.0.1"` par `0.0.0.0` ni ouvrir le port 3000 vers Internet sans authentification.

Sur iPhone, ouvrir l'adresse HTTPS privée dans **Safari → Partager → Sur l'écran d'accueil**. Sur Android Chrome, ouvrir l'adresse HTTPS privée et choisir **Installer l'application**. La possibilité d'installation dépend du navigateur et du contexte sécurisé.

Cette branche n'a pas accès à ton téléphone ou à tes réseaux privés : l'installation et la connexion du tunnel doivent être vérifiées sur tes appareils. L'utilisation réelle de la GPU requiert que le PC reste allumé.

## Confidentialité

Ne pas activer le cache des endpoints `/api/`, `/web-preview/` ou des documents privés. Un PWA installé sur un appareil partagé doit être protégé par un verrouillage de l'appareil. Le cadenas NSFW dans l'interface est une séparation UX, pas une authentification robuste pour un accès public.

## Si l'icône ne s'affiche pas

Le manifeste utilise une icône SVG. Selon Safari/iOS, une icône PNG dédiée pourrait être nécessaire pour obtenir une vignette système optimale.
