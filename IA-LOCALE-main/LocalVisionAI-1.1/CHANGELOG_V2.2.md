# LocalVisionAI 2.2 — espace NSFW isolé

- Ajoute une section NSFW séparée dans le menu gauche.
- Ajoute une case d'activation locale avant d'ouvrir ce profil.
- Ajoute deux workflows indépendants : `NSFW Image.json` et `NSFW Video.json`.
- Ajoute `local_app/nsfw_profile.py` pour la configuration technique isolée du profil.
- Les modifications du profil NSFW ne changent pas les profils RealVisXL/Animagine/Wan normaux.
- Les créations issues de ce profil sont marquées avec leur profil d'origine dans la bibliothèque locale.
- Aucun mécanisme de contournement de protections ni réglage explicite de contenu n'est ajouté.
