# Forma × LocalAiStudio — suivi LocalAiWeb

## 18 novembre 2026 · Phase 0

### Versions de référence

Inventaire des références distantes des deux dépôts, comparaison des historiques avec git rev-list --left-right --count et inspection des différences entre arbres. Le premier nombre ci-dessous compte les commits propres à main, le second ceux propres à la branche.

| Produit | Branche examinée | main | Tête | Écart | Décision |
|---|---|---|---|---|---|
| LocalAiStudio | feature/v2ag-phase-a et nextgen/figma-v3 | ac83d5e | 05a3c03 | 0 / 55 | Même commit. Retenir cette version NextGen pour l’audit courant. Elle inclut les changements de nextgen/claude-code (da63420), puis deux commits fonctionnels sur la navigation, les presets et SANA. |
| Studio Build 317 | codex/studio-317-commercial-ready | ac83d5e | 79201b9 | 1 / 216 | Lignée distincte à conserver pour ses fonctions Web et commerciales. Entre 317 et NextGen, respectivement 216 et 56 commits propres depuis a470952. Une fusion globale nécessiterait une analyse de compatibilité, notamment des données existantes. |
| Forma | forma/finitions-responsive-20261113 | 2e6a99c | a206f1a | 0 / 18 | Inclut refonte-contact-portfolio, puis 12 commits. main et vitrine-evolution-2 désignent la même révision. Les ajouts comprennent les démos de services, le parcours contact, le responsive et les tests. |

NextGen modifie 531 fichiers par rapport à main, Forma 57. Les nombres comprennent ajouts et suppressions. Les tests portent sur les révisions ci-dessus, dans des copies isolées sous Linux.

### Inventaire et décisions

| Exigence | Statut réel et preuve | Fichiers | Manque ou prochaine action |
|---|---|---|---|
| Projet, génération depuis un brief | API FastAPI, persistance MongoDB, orchestrateur de brief, architecture, direction, visuels, génération des pages, QA et retouche. Préférence locale par défaut. L’appel réel sans serveur de modèle laisse le projet en erreur explicite, récupérable dans l’API. | backend/lib/pipeline.py, local_engine.py et llm.py, backend/models/schemas.py | Réutiliser. Mesurer sur le PC Windows avec les modèles effectivement installés. Le défaut configuré est qwen2.5-coder:14b, contexte 16384, avec Ollama ou LM Studio configurable. |
| Design varié et modules métier | Le mode premium compose du contenu structuré avec 18 types de sections, un thème et des variantes. Il ajoute un hero si nécessaire et ignore une section dont le rendu échoue. Le formulaire premium intercepte l’envoi et affiche un état local. | backend/lib/premium/__init__.py, themes.py, runtime.js et backend/lib/pipeline.py | Conserver le moteur et le mode code. Sur deux briefs réels, mesurer la répétition, les sections perdues, le responsive et les temps. Une option payée requiert son propre test fonctionnel et un backend lorsque nécessaire. |
| Édition, versions et export | Interface de chat, sélection dans la preview, édition de fichiers, historique. Test API avec contenu témoin, deux versions, restauration et lecture du HTML dans le ZIP. | frontend/src/pages/Editor.tsx, backend/routers/projects.py, backend/lib/pipeline.py | Corriger la lecture d’une version inexistante. Puis évaluer la cohérence des snapshots concurrents et la propagation de la version aux liens et ressources avant le partage public. |
| Validation initiale et commande | Les snapshots NextGen conservent les fichiers et le numéro. Aucun état d’approbation vendeur/client associé à une commande Forma identifié sur ces branches. | backend/models/schemas.py, backend/lib/db.py, backend/routers/projects.py | Ajouter ultérieurement une référence explicite à la version acceptée, aux options et aux conditions. Réutiliser les identifiants existants. |
| Vision, modèles et médias | UI Vision, publicité, marques, import des médias dans l’éditeur. Routage ComfyUI, catalogue LoRA SDXL, configuration vidéo et moteur distant SANA. Tests unitaires des chemins de sélection et d’indisponibilité. | frontend/src/pages/Vision.tsx, Publicities.tsx, Editor.tsx, backend/routers/media.py, backend/lib/comfy.py, hf_sana.py | Tester photo, retouche et vidéo sur Windows/RTX 3060. Mesurer VRAM, durée et sortie réelle. Les tests logiciels ne certifient pas l’inférence, ni une vidéo native 4K. |
| Devis, factures, encaissement et livraison | Build 317 contient SQLite, devis, reçus, factures, avoirs, ZIP et contrôles de livraison. Code Stripe Checkout et webhook. Tests locaux de documents, restrictions de livraison et échanges HTTP. | Build 317, local_app/client_delivery.py, web_sales_orders.py, web_sales_invoice.py et tests/test_client_delivery.py | Réutiliser les règles et jeux de tests. Identifier les propriétaires de données avant de relier le système en ligne à ces fonctions locales. Paiement prestataire de bout en bout à valider en sandbox. |
| Vitrine Forma | Pages, navigation, démos, portfolio conceptuel, estimateur et parcours vers le formulaire. Tarification indicative et récurrences dans la configuration. | src/App.tsx, src/client-spec/Demos.tsx, PricingStudio.tsx, src/config/pricing.ts | Conserver les composants. Pour un achat direct, ajouter périmètre contractuel, version des conditions, prix validé et contrôle de livrabilité de chaque option. |
| Contact et espace client Forma | Formulaire POST conditionné par VITE_FORMA_CONTACT_ENDPOINT. Le portail historique est présenté dans une iframe, les contrôles d’authentification sont désactivés. | src/client-spec/Contact.tsx et Login.tsx, public/original-client, docs/CONTACT.md et CLIENT_AUTHENTICATION.md | Vérifier une réception réelle avec le service configuré. Prévoir session, rôles, isolation par client, commandes, abonnements, factures, messagerie et accès aux livrables. |
| Documents et consentements | Pages de mentions légales et de confidentialité, liste de prérequis au lancement. | src/client-spec/Legal.tsx et docs/PRE_LANCEMENT.md | Compléter les informations réelles et les conditions par prestation, versionner les acceptations et vérifier les traceurs avant commercialisation. |
| Synchronisation et hébergement | Aucune chaîne démontrée achat Forma → production locale → approbation → livraison dans le compte client. Configurations Vercel côté vitrine, scripts Windows et recettes d’installateur côté Studio. | Forma vercel.json, Studio installer/, start-localaistudio.bat, Build 317 local_app/web_delivery.py | Séparer les données en ligne et locales. Prévoir API authentifiée, commande idempotente, accusé de réception et reprise après coupure. Tester un installateur Windows et les deux modes d’hébergement. |

### Première correction soumise à validation

Dans backend/routers/projects.py, une demande de preview avec v positif cherche ce numéro puis se rabat sur les fichiers courants si la révision manque. Reproduction avec l’application FastAPI, son cycle de démarrage, une session locale et une base MongoDB temporaire réelle. Le rendu premium a reçu un contenu témoin déterministe. Les deux écritures suivantes sont passées par la route de sauvegarde.

| Demande sur le même projet | Résultat observé | Critère après correction |
|---|---|---|
| v=1 après sauvegarde de V2 | 200, contenu V1 | Identique |
| v=2 | 200, contenu V2 | Identique |
| v=999 | 200, contenu V2 | 404 explicite |
| sans v | 200, contenu courant V2 | Identique |

Préserver également la convention v=0 utilisée par l’éditeur au démarrage. Ajouter un test de régression ciblé, vérifier l’accès au brouillon et aux versions valides, puis soumettre le changement pour validation. Aucun changement applicatif dans cette phase.

### Résultats de contrôle

- **Forma** — npm ci puis npm run build réussis. Avec Chromium et la configuration Playwright du dépôt, 9/10 passent au premier lancement. Le dernier scénario dépasse le délai global de 45 s. Relancé seul avec un plafond de 180 s, il passe en 41,3 s pour 6 pages × 6 largeurs, de 320 à 1920 px. La suite couvre notamment les 30 entrées de services, les tarifs, le contact sans serveur et le portail désactivé.
- **Build 317** — 44/44 tests ciblés réussis avec des dossiers de données isolés. unittest discover exécuté sur test_web_local_engine (5), test_transactional_projects (13), test_client_delivery (16), test_forma_pro_sales (6) et test_web_delivery (4). Les tests du moteur utilisent des réponses simulées. Les cas de facturation ne font pas d’encaissement externe.
- **NextGen** — 50/50 tests ciblés sur modèles, LoRA, préparation de prompt SANA et contrat UI photo. Suite backend complète sous Linux, CPython 3.11.18 avec requirements-local.txt et dépendances de test, puis résultat également observé sous 3.12 : 577 réussis, 2 échecs, 3 ignorés. test_hf_sana attend que SANA soit masqué alors que le dernier changement le rend sélectionnable. test_prompt_local_provider attend un refus que la validation d’une adresse de boucle locale ne produit pas. Revoir les contrats attendus avant modification.
- **Parcours Studio** — démarrage FastAPI via TestClient et MongoDB 8.0.12 temporaire sur loopback. Session, deux modifications de fichier, lectures de versions, export et restauration validés. Une demande de génération locale a bien atteint le moteur et s’est arrêtée à l’analyse du brief, Ollama étant injoignable. Les résultats ne mesurent ni rendu IA réel, ni durée de génération, ni consommation GPU.
- **Décision** — conserver les deux lignées Studio et la vitrine Forma. Attendre la validation du correctif de lecture de version avant l’implémentation. Les intégrations prestataires, l’inférence sur RTX 3060 et l’installation Windows restent à vérifier sur leurs environnements cibles.
- **Frontend Studio** — tsc -b et vite build réussis sur une copie des sources avec le yarn.lock d’origine. Après des délais de téléchargement, le cache a été complété avec l’archive du registre npm dont l’empreinte correspond au verrou. Avertissement Vite sur le JavaScript principal, 1 051 kB minifiés, 324 kB gzip. L’effet sur le temps de démarrage Windows reste à mesurer.

## 18 novembre 2026 · Lecture d’une version de preview

- Dans `backend/routers/projects.py`, toute révision demandée et absente renvoie HTTP 404. Le navigateur reçoit un message français adapté au cadre de preview. Les clients JSON reçoivent le détail de l’erreur. Les réponses d’erreur interdisent la mise en cache.
- `backend/tests/test_preview_versions.py` couvre V1, V2, le brouillon implicite et explicite (v=0), et les deux représentations de la 404. Avant correction, 4 réussites et 2 échecs. Après correction, 6 réussites.
- Vérification dans l’iframe de l’éditeur sous Chromium, avec FastAPI et une base MongoDB de test. Aux largeurs de 390 et 1366 px, V1 et V2 affichent leurs contenus respectifs, le brouillon distinct reste accessible, V999 affiche le message attendu et renvoie 404. Vérification complémentaire du détail JSON.
- Suite backend Linux sous Python 3.11 : 583 réussites, 3 tests ignorés et les 2 échecs connus de la phase 0 (SANA et validation d’adresse de boucle locale).
- Branche `fix/preview-version-introuvable`. Prochaine action : validation utilisateur sur un projet Windows comportant deux versions.
