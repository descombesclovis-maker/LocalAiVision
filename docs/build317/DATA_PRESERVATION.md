# Conservation des anciennes données

Build 317 retire l’interface et les routes de l’ancien espace. Il ne supprime ni ses conversations, ni ses fichiers, ni son index historique. Les anciens profils restent exclus des listes publiques, même après rechargement. Les fichiers ComfyUI sans classification restent inaccessibles depuis Studio : aucune conversion automatique en média public.

Un index SQLite indépendant dans `retired-records/access.sqlite` conserve les décisions d’accès. Une classification retirée est prioritaire sur une classification publique. Un inventaire historique illisible bloque l’accès ; il ne permet jamais de contourner la protection. L’ancien déverrouillage, même avec un ancien cookie, renvoie HTTP 410.

## Sauvegarde hors ligne avant installation

1. Fermer Studio, ComfyUI et le navigateur pour obtenir une copie cohérente.
2. Copier l’intégralité du dossier de données réellement utilisé (`LOCALVISIONAI_DATA`, par défaut `%LOCALAPPDATA%\LocalVisionAI`), les dossiers ComfyUI `input`, `output` et le profil du navigateur utilisé. Les conversations sont encore dans le stockage local de ce navigateur : sauvegarder uniquement le dossier Studio ne suffit pas.
3. Le script optionnel `python scripts/backup_local_data.py --source "CHEMIN_DES_DONNEES" --source "CHEMIN_COMFY_OUTPUT" --destination "CHEMIN_EXTERNE\sauvegarde.zip"` crée une archive sans modifier les sources et refuse d’écraser une archive existante. Ajouter les autres sources nécessaires explicitement. Aucun modèle n’est téléchargé.
4. Conserver la sauvegarde sur un support chiffré et privé : elle peut contenir des conversations, images et identifiants. La restauration doit être effectuée application fermée, dans une copie distincte avant toute substitution.

Ce lot ne propose plus d’affichage des médias retirés. Leur conservation n’est pas une promesse de restauration de l’ancien module.
