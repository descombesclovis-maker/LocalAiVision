# Moteur Web local — première intégration

Le moteur local est le défaut des nouveaux projets. Pour les anciens projets sans choix explicite d’agent, un ancien défaut Codex/Claude ne devient pas un consentement à utiliser un service distant. Un choix explicite existant est respecté.

Le connecteur utilise uniquement un GGUF/llama.cpp déjà installé, ou un modèle local déjà présent dans Ollama à `127.0.0.1:11434`. Les modèles Ollama marqués cloud sont exclus. Aucun appel `/pull`, téléchargement, installation, achat ou repli distant n’est lancé. Le sélecteur permet toujours de choisir explicitement Codex ou Claude. Le statut indique le moteur et le modèle réellement détectés.

Le pipeline existant produit de vrais fichiers modifiables : contexte du projet, direction artistique liée à la marque, plan multi-pages, contrat de contenu, génération JSON, contrôle du contrat et passe de réparation. Les snapshots, export ZIP et fichiers existants sont conservés. Cette intégration ne transforme pas un formulaire de démonstration en réservation opérationnelle et ne certifie pas un paiement ou une authentification sans backend.

## Vérification du 06/11/2026

398 tests Python réussis, 2 ignorés. Régressions ajoutées : choix local malgré agents distants disponibles, conservation du choix distant explicite, absence de modèle refusée avant acceptation d’une tâche, absence de téléchargement, adaptateurs llama.cpp et Ollama (réponses de test explicitement simulées).

Détection réelle de cet environnement : aucun modèle local, aucun exécutable NVIDIA détecté. **Aucune première génération réelle ni comparaison de qualité n’a été effectuée.** Les six projets de recette, leur backend métier et leur rendu restent à qualifier sur une machine équipée. Un test d’adaptateur n’est pas une preuve de capacité du modèle.

API Ollama consultée : https://github.com/ollama/ollama/blob/main/docs/api.md (`/api/tags`, `/api/chat`, `stream:false`).
