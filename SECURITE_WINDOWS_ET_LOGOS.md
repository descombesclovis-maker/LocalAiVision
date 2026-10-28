# LocalAiVision — Identité Windows, mise à jour et sécurité

## Logos intégrés
- Logo 1 : l'étoile violette envoyée par l'utilisateur est utilisée pour LocalAiVision (navigation, écran d'accueil, favicon du studio).
- Logo 2 : l'identité visuelle complète avec slogan est visible sur l'accueil et la bibliothèque ; son étoile violette constitue le pictogramme carré du `LocalVisionAI.exe` Windows et de l'icône PWA générale.
- Logo 3 : l'étoile WWW est utilisée dans LocalAiWeb (bibliothèque, éditeur, carte et favicon de ce studio).
- Les trois visuels sont des images embarquées localement dans les SVG : aucun téléchargement tiers n'est nécessaire à leur affichage.

## Mise à jour
Le bouton vérifie la dernière publication GitHub, contrôle la taille, le SHA-256 de l'archive lorsque disponible et le contenu du ZIP. Un programme PowerShell local attend l'arrêt de l'ancienne instance et la libération du port 3000, puis échange l'exécutable, redémarre et valide le numéro de build depuis `/api/ping`. En cas d'échec, il restaure le précédent exécutable et signale le motif dans `%LOCALAPPDATA%\LocalVisionAI\logs\update.log`.

Si l'emplacement de l'EXE actuel est bloqué, le processus installe la nouvelle version vérifiée sous `%LOCALAPPDATA%\LocalVisionAI\app\LocalVisionAI.exe` et redirige ou crée un raccourci de bureau `LocalAiVision.lnk`. Aucun élévation administrateur, désactivation de Defender ou modification d'une politique de sécurité n'est demandée.

Le fichier `LocalVisionAI.exe.failed` est un **exécutable PE** conservé après restauration, **pas un journal d'erreurs**. La vraie cause apparaît dans `update.log`. Les téléchargements manuels se trouvent dans les Releases du dépôt et chaque release publie le hash SHA-256 du ZIP. Le dossier de projets et modèles n'est jamais remplacé par le script de mise à jour.

## Signature, réputation et éditeur vérifié
- Le build embarque une icône personnalisée et des métadonnées PE (product name, version, company), qui ne constituent **pas une signature cryptographique**.
- Si un certificat Authenticode légitime est disponible, renseigner dans les secrets GitHub Actions `WINDOWS_SIGN_CERT_B64` (PFX encodé en base64) et `WINDOWS_SIGN_CERT_PASSWORD`. L'action signe après les tests, vérifie la signature, et n'envoie jamais la clé privée dans les Releases.
- Sans certificat valide, l'EXE demeure **non signé**. Windows Defender et SmartScreen peuvent légitimement le bloquer ou avertir l'utilisateur ; aucune promesse de reconnaissance ou de sécurité absolue n'est possible.
- Un programme signé peut encore déclencher des contrôles en raison de la réputation, de comportements observés ou d'alertes d'antivirus. Publier les hashes, ne pas contourner les protections, soumettre les faux positifs aux éditeurs et diffuser une version reproductible sont les moyens transparents d'améliorer la confiance.
- Le script de mise à jour refuse la substitution d'une version déjà signée par un EXE non signé ou signé avec un certificat différent.
- Le serveur doit rester sur `127.0.0.1`; ne jamais exposer sans authentification les moteurs de génération ou les secrets.

## Contrôles du pipeline
Le workflow Windows exécute les tests Python, produit les assets branding, compile l'EXE Windows, le lance et interroge `/api/ping`, puis teste un vrai changement d'exécutable dans un répertoire temporaire avant de publier l'archive. Les tests de remplacement ne constituent pas une garantie de fonctionnement sur chaque PC : politiques de sécurité, permissions, antivirus et chemins Windows diffèrent d'une machine à l'autre.
