# IDENTITÉS OFFICIELLES APPROUVÉES — LocalAI Studio / Web / Vision

**Statut : VERROUILLÉ PAR L’UTILISATEUR — 3 novembre 2026.** Cette charte constitue la référence graphique des trois univers. Ne pas redessiner un autre logo, changer le symbole, inverser les couleurs, modifier la typographie ni créer de variantes sans autorisation explicite du propriétaire.

## Fichiers maîtres (PNG de référence, à préserver)

- `Official_Three_Logos_Original_Unmodified.png` : image d’origine 2172 × 724, sans aucune modification. Trois cases carrées adjacentes dans l’ordre Studio, Web, Vision.
- `LocalAIStudio_Official_Original.png` : carré complet 724 × 724 extrait *sans retouche interne* de la partie gauche de l’image maître. Engrenage « AI », violet + cyan, libellé « LocalAI » et sous-titre « Studio », bordure complète et traînées lumineuses.
- `LocalAIWeb_Official_Original.png` : carré complet 724 × 724 extrait sans retouche interne de la partie centrale. Nuage électronique à circuits, violet uniquement, libellé « LocalAI » et sous-titre « Web », bordure complète et traînées lumineuses.
- `LocalAIVision_Official_Original.png` : carré complet 724 × 724 extrait sans retouche interne de la partie droite. Anneau/bouton lecture, cyan uniquement, libellé « LocalAI » et sous-titre « Vision », bordure complète et traînées lumineuses.

**Origines des choix :** Studio = proposition n°17 de la deuxième planche ; Web = symbole n°18 de la deuxième planche, devenu violet ; Vision = symbole n°15 de la première planche, devenu cyan. Les trois logos définitifs sont ceux de l’image maître actuelle ; ils prévalent sur les anciennes planches.

## Règles obligatoires

1. Garder les trois logos originaux intacts. Les extractions en fichiers individuels comprennent chaque carte entière avec bordure, symbole, typographie et sous-titre. Les versions source ci-dessus ne doivent jamais être écrasées par un export optimisé.
2. **Icône Windows EXE :** utiliser le logo complet **LocalAI Studio tel quel**, avec sa bordure, son engrenage et son nom, **sans recadrage intérieur, suppression d’élément, retouche, reconstruction ni substitution par le seul symbole**. Seule une mise à l’échelle isotrope et la conversion techniquement indispensable au format ICO sont autorisées. Générer un ICO multi-résolutions à partir du carré complet, comparer visuellement avec la référence. Accepter que le texte devienne petit à 16 px plutôt que retirer le texte.
3. Pour le frontend : reproduire fidèlement chaque logo en **véritable SVG vectoriel** (formes/trajectoires/gradients ; **pas** d’image bitmap embarquée sous extension `.svg`). Séparer le SVG statique de l’animation, utiliser un rendu net à toutes dimensions, exporter également des PNG carrés **4096 × 4096** 4K, sans découper le cadre ni déformer les proportions. Si un détail n’est pas reconstructible fidèlement, signaler la limite et conserver le PNG maître comme référence, sans fausse affirmation « identique ».
4. Effets lumineux / animations : traînées de lumière animées comme celles au pied des logos, balayages de reflets, légère brillance sur les contours et gradients doux. Réduire ou désactiver avec `prefers-reduced-motion`, quand onglet invisible ou en génération GPU ; éviter consommation VRAM excessive, stroboscopie et halos qui nuisent à la lisibilité.
5. Palettes distinctes : **Studio = violet + cyan**, **Web = violet**, **Vision = cyan**. Les arrière-plans, menus, boutons, bordures et lumières des interfaces doivent reprendre ces couleurs de façon cohérente ; ne pas rendre Web cyan ou Vision violet. Le noir/bleu nuit est une base neutre, pas une nouvelle couleur identitaire.
6. **Accueil Studio :** deux grandes cartes d’accès avec de **véritables photos photoréalistes** représentant respectivement des sites Web professionnels et de la création photo/vidéo, colorisées dans leurs univers violet et cyan. Ce sont des médias de présentation, pas de faux résultats de génération. Fichiers locaux autorisés/licenciés ; pas de promesses erronées sur les productions IA. Aucun menu latéral à l’accueil Studio.
7. Conserver logos, identifiants visuels et sauvegardes précédentes pendant la mise à jour ; ne pas modifier l’espace réservé NSFW ; conserver les fonctions existantes. Faire un audit visuel et des tests Windows sur les DPI et résolutions prévues.

## Comportement à la demande « mets les nouveaux logos respectifs en SVG, en animation de lumière brillante et en 4K »

Codex doit utiliser **ces fichiers précis comme références maîtres verrouillées**, produire pour chaque univers : (a) un SVG statique fidèle, (b) une variante animée lumineuse intégrée au frontend, (c) un export PNG 4096 px, (d) pour Studio un `.ico` multirésolution à partir du **logo complet sans recadrage**, et (e) des captures de comparaison côte à côte ainsi qu’une vérification visuelle Windows. Ne pas « inventer » une autre version graphique pour gagner du temps.

Les PNG 724 × 724 sont des images de référence (rasterisées) et **ne sont pas encore des SVG 4K** ; ce travail est une mission distincte pour Codex.
## Où retrouver les fichiers maîtres

Les PNG approuvés et le collage original ont été conservés dans la **Bibliothèque ChatGPT** de l’utilisateur :
`/LocalAIStudio/Identites_officielles_2026_11_03/`.

Archive transférable à Codex : `LocalAIStudio_Identites_Officielles_Verrouillees.zip` (contient la planche originale, les trois carrés intacts, les sommes SHA-256 et cette charte).

**IMPORTANT :** les images binaires ne sont **pas encore présentes dans le dépôt GitHub** à la seule lecture de cette charte. Lorsque Codex travaille, **joindre l’archive ZIP à sa tâche** et lui demander de copier les maîtres dans `local_app/web/assets/brand-reference/` ou un emplacement équivalent versionné, puis de les vérifier avec `SHA256SUMS.txt`. Ne pas remplacer les originaux par des reconstructions SVG approximatives.

SHA-256 PNG de la planche : `742a94a3711f4c58724364855e6757e62df61353140153c0b9192d0361de700e`.
