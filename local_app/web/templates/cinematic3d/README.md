# LocalAiWeb — modèle Cinématique 3D

Ce modèle est un **point de départ adaptable à tous les produits** : photographie, technologie, automobile, mode, mobilier, cosmétique, jeux et autres secteurs.

## Créer un site

1. Dans LocalAiWeb, cliquez **✦ Site 3D**, puis donnez un nom au projet.
2. Une scène 3D procédurale apparaît immédiatement dans l'aperçu quand WebGL2 et Internet sont disponibles.
3. Dans **Assets**, importez un fichier **.glb** (GLB 2.0, 40 Mo maximum).
4. L'interface connecte automatiquement le GLB au `data-model-src` de `index.html`. L'objet remplace la sculpture générique.
5. Facultatif : importez un environnement lumineux **.hdr** (Radiance, 20 Mo maximum), relié automatiquement à `data-environment-src`. Cette lumière HDRI apporte des reflets réalistes aux matériaux du produit.
6. Dans la zone IA, demandez une direction graphique, des interactions, un storyboard de scroll, des textes, une palette de couleurs ou des sections.
7. Prévisualisez en desktop, tablette et mobile ; exportez ZIP ou déployez via Vercel quand configuré.

## Moteur graphique

- **Three.js 0.186.1** importé en modules ES depuis jsDelivr, version fixée. Aucune dépendance sur un backend vidéo.
- **GLTFLoader** pour importer vos propres modèles GLB.
- **WebGL2** avec rendu physiquement réaliste, plusieurs sources lumineuses, rendu transparent et colorimétrie ACES.
- **Scroll-linked** : rotation, zoom, cadrage et placement évoluent avec la progression du défilement.
- **Mobile** : limitation du `devicePixelRatio` et cadence de rendu ajustée.
- **Accessibilité** : navigation clavier, textes de remplacement, `prefers-reduced-motion` et fallback graphique sans WebGL.
- Le modèle procédural de démonstration est volontairement **abstrait** pour ne pas imposer de catégorie de produit.

## Limites techniques

- Le moteur WebGL utilise aujourd'hui un **CDN** : pour charger Three.js, il faut une connexion Internet. La version hors ligne complète sera une évolution distincte.
- Une image 2D ne se convertit pas automatiquement en véritable modèle 3D ; utilisez un GLB adapté (géométrie, matériaux et textures).
- Les animations intégrées aux fichiers GLB peuvent être jouées, mais la synchronisation précise de chaque animation avec une chronologie nécessite des personnalisations.
- Les options de publication GitHub/Vercel/Supabase nécessitent installation et authentification.
- Comme toute démo de design, ce modèle **n'est pas un site e-commerce autonome** tant que les fonctions nécessaires n'ont pas été ajoutées et vérifiées.

## Séparation des données

Chaque projet et chaque asset restent sous `LocalVisionAI/localaiweb/projects/<id>`. Les conversations, sauvegardes et paramètres de LocalAiVision ne sont pas partagés. Seuls les modèles et outils de génération sont réutilisés.

## Optimisation recommandée des modèles 3D

Export GLB, maillage raisonnable (éviter les millions de polygones), textures compressées avec budget mémoire mobile, LOD selon la cible et taille d'asset la plus réduite possible. Préférer des matériaux PBR standards. Éviter les textures énormes : un GLB de 40 Mo peut consommer bien plus en VRAM après chargement.

## Nouvelle qualité de rendu 3D

La scène embarque maintenant un moteur PBR avec **Image-Based Lighting** : environnement de studio généré par `RoomEnvironment` et filtré par `PMREMGenerator`, ou éclairage HDRI réel lorsque vous fournissez un fichier `.hdr`. Les surfaces utilisent des matériaux physiques (métal, vernis, céramique) et des ombres douces. Les modèles GLB gardent leurs matériaux et textures d'origine.

Le moteur essaie les décodeurs officiels **Draco, Meshopt et KTX2/Basis** lorsque les ressources réseau sont disponibles. En mode dégradé, il continue à charger les fichiers GLB non compressés.

L'expérience exportée propose quatre modes sélectionnables dans la page : **Auto**, **Photo premium**, **Équilibrée**, et **Performance**. En mode Auto, le profil est déterminé selon l'appareil et ses capacités. Un régulateur ajuste ensuite la résolution interne en fonction de la durée moyenne des images rendues, sans modifier les dimensions du site. Sur ordinateur, l'objectif est de viser 60 images/s ; sur mobile, 30 images/s. Ce sont des **objectifs**, pas des garanties : la fluidité réelle dépend de la puissance GPU, de l'appareil, du navigateur, de la complexité du GLB et de la taille de ses textures.

Les réglages de qualité sélectionnés dans l'aperçu sont enregistrés pour la session de cette page. Pour définir le profil de départ d'un site exporté, modifiez l'attribut `data-quality="auto"` de `index.html` (`quality`, `balanced` ou `performance`).

Pour personnaliser les reflets, importez un fichier HDRI choisi pour correspondre au produit : studio doux pour verre ou cosmétique, contrasté pour métal, intérieur chaud pour mobilier. Un matériau ou une géométrie de mauvaise qualité ne devient pas photoréaliste par simple augmentation des réglages.

**Compatibilité** : les améliorations sont incluses dans les **nouveaux** projets créés à partir du modèle 3D. Les fichiers de projets 3D déjà enregistrés ne sont pas écrasés automatiquement, pour préserver le travail de l'utilisateur. Les sites classiques restent inchangés.
