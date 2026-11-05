# Audit humain 1 — poursuite après compilation 394

Base : 19362bce8ae3fbe33f19825944584133c144fb2b, PR #65 en brouillon.

Critères d'acceptation avant compilation :
- Une sortie publique n'entre dans la galerie et le résultat réussi qu'après décodage navigateur.
- La vérification vidéo couvre dimensions, durée et première image décodée ; elle ne prétend pas vérifier toutes les frames ni la qualité artistique.
- Un fichier manquant, corrompu ou lent reste récupérable par une nouvelle vérification, sans soumettre un nouveau rendu.
- Les publicités conservent leur contexte de marque lors de cette récupération.
- Une panne réseau ou un quota Codex n'est pas présenté comme une perte d'authentification ou une autorisation de fichiers manquante.
- Aucun second appel automatique de génération Codex pour une erreur réseau/quota confirmée sans sortie utilisable.
- Aucune modification des paramètres ou workflows privés.
- Suite Python, tests Node, contrôle du navigateur et compilation Windows réels ; pas de qualification RTX 3060 sans rendus réels.


Implémentation :
- `studio-media-validation.js` utilise les décodeurs du navigateur et libère les éléments de contrôle après vérification.
- Les reçus de vérification et les sorties à revérifier sont sauvegardés avec les conversations publiques ; le rechargement conserve l'action de récupération.
- Les exports publicitaires passent également par ce contrôle avant d'être annoncés prêts. Leur contexte de marque n'est pas remplacé par celui d'une autre conversation.
- Les pannes réseau, quotas et demandes de connexion Codex reçoivent des messages distincts. Les fichiers existants sont préservés ; les chemins de récupération d'écriture Windows restent disponibles pour les refus de sandbox et les sorties vides.

Limites : aucune session Codex utilisateur ni aucun moteur GPU ne sont disponibles ici. La lecture d'une première frame ne garantit pas la stabilité des suivantes. Les tests de fixture sont des contrôles logiciels, pas des rendus réels. Les mesures et comparaisons photo/vidéo sur RTX 3060 restent à faire sur le PC cible.
