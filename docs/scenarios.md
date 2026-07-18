# Scénarios d'Usage — Nexus-Worker-MCP

Ce document décrit les cas d'utilisation concrets du système, avec les flux d'interaction détaillés entre le Cerveau, le MCP et le Worker.

---

## Scénario 1 : Création d'une feature complète

**Contexte :** L'utilisateur demande d'ajouter un système d'authentification JWT à une API FastAPI existante.

### Flux d'interaction

1. **Le Cerveau planifie** — Il décompose la demande : modèle User, endpoint login, middleware de vérification. Il identifie 3 fichiers à créer.

2. **Délégation 1 → `worker_generate_code`** — Le Cerveau envoie l'instruction : "Crée un modèle User SQLAlchemy avec email, hashed_password et created_at". Le Worker retourne 45 lignes de code.

3. **Le Cerveau valide** — Il lit le résultat (opération peu coûteuse en tokens d'entrée) et vérifie la cohérence.

4. **Délégation 2 → `worker_generate_code`** — Le Cerveau demande la création des routes d'authentification avec JWT, en passant un résumé du modèle User comme contexte. Le Worker retourne 120 lignes.

5. **Le Cerveau détecte un problème** — Un secret JWT est hardcodé. Il appelle `worker_refactor_code` pour corriger spécifiquement ce point.

6. **Validation finale** — Le Cerveau vérifie l'ensemble et présente le résultat à l'utilisateur.

### Économie réalisée

| Sans Nexus | Avec Nexus |
|---|---|
| Le Cerveau génère ~165 lignes (Output très cher) | Le Cerveau ne génère que ~3 instructions courtes |
| Input : ~500 tokens | Input : ~200 tokens (résumés uniquement) |

---

## Scénario 2 : Analyse et debug de logs massifs

**Contexte :** Un serveur de production crashe. Le fichier de logs fait 15 000 lignes.

### Flux d'interaction

1. **Le Cerveau identifie le volume** — 15 000 lignes, trop lourd pour son contexte.

2. **Délégation → `worker_analyze_file`** — Instruction : "Isole les stack traces d'erreurs fatales (CRITICAL, FATAL, unhandled exception). Pour chaque erreur, inclus les 5 lignes de contexte précédentes."

3. **Le Worker filtre** — Il lit les 15 000 lignes sur l'API économique et retourne 3 stack traces pertinentes (80 lignes au total).

4. **Le Cerveau diagnostique** — Il lit les 80 lignes, identifie une race condition dans le gestionnaire de connexions DB, et propose la correction.

### Économie réalisée

- **15 000 lignes** jamais envoyées au modèle cher
- Le Worker encaisse ~45 000 tokens d'input sur l'API gratuite
- Le Cerveau ne traite que **80 lignes** pertinentes → économie de **95%+ des tokens**

---

## Scénario 3 : Compression de documentation (RAG économique)

**Contexte :** L'utilisateur veut intégrer l'API Stripe. La doc officielle fait 200 pages.

### Flux d'interaction

1. **Délégation 1 → `worker_analyze_file`** — Le Cerveau demande au Worker de résumer uniquement les endpoints nécessaires : créer un client, créer une session Checkout, gérer les webhooks. Inclure les signatures et types de réponse.

2. **Le Worker produit un cheat sheet** — 60 lignes avec les 3 endpoints, leurs paramètres et leurs réponses.

3. **Délégation 2 → `worker_generate_code`** — Le Cerveau utilise ce résumé de 60 lignes comme contexte et demande la création du service d'intégration Stripe.

4. **Validation** — Le Cerveau vérifie la cohérence avec le reste de l'application.

### Point clé

Le Cerveau n'a jamais vu les 200 pages de documentation Stripe. Son contexte reste propre et ciblé, ce qui améliore la qualité de ses décisions architecturales.

---

## Scénario 4 : Migration de framework

**Contexte :** Migrer 30 composants React de Class Components vers Functional Components (hooks).

### Flux d'interaction

1. **Le Cerveau planifie** — Il liste les 30 fichiers et définit les règles de conversion : `this.state` → `useState`, `componentDidMount` → `useEffect`, `this.props` → destructuration.

2. **Boucle de migration** — Pour chaque fichier, le Cerveau appelle `worker_refactor_code` avec le chemin du fichier et les règles de conversion. Le Worker applique les transformations et retourne le composant migré.

3. **Validation unitaire** — Le Cerveau relit chaque résultat et vérifie la cohérence des imports.

4. **Correction si nécessaire** — Si un composant est mal converti, le Cerveau rappelle l'outil avec une instruction de correction ciblée.

5. **Bilan** — Le Cerveau présente le résultat : "30/30 composants migrés".

### Point d'attention

Pour les migrations multi-fichiers, le Cerveau maintient un **registre de progression** pour ne pas perdre le fil. La boucle est gérée par le Cerveau, pas par le Worker.

---

## Scénario 5 : Génération de tests exhaustifs

**Contexte :** Un module métier de 400 lignes n'a aucun test.

### Flux d'interaction

1. **Compréhension → `worker_explain_code`** — Le Cerveau demande d'abord une explication structurée du module. Le Worker identifie 8 fonctions publiques avec leurs rôles.

2. **Le Cerveau comprend la logique** — Sans avoir lu les 400 lignes, il sait ce que fait chaque fonction grâce au résumé.

3. **Génération → `worker_generate_tests`** — Le Cerveau délègue la création des tests avec le niveau de couverture "exhaustive". Le Worker produit 35 tests couvrant cas nominaux, cas limites et erreurs.

4. **Validation** — Le Cerveau vérifie que les mocks sont cohérents et que les assertions sont pertinentes.

---

## Scénario 6 : Revue de code automatisée (Code Review)

**Contexte :** L'utilisateur pousse un commit et veut une revue de qualité avant la PR.

### Flux d'interaction

1. **Le Cerveau identifie les fichiers modifiés** — Via git diff, 5 fichiers modifiés, 350 lignes changées.

2. **Boucle d'analyse** — Pour chaque fichier, le Cerveau appelle `worker_analyze_file` avec l'instruction : "Fais une revue de code professionnelle. Identifie bugs, problèmes de performance, violations de conventions, failles de sécurité, et code dupliqué. Note chaque point avec sa sévérité."

3. **Agrégation** — Le Cerveau reçoit les 5 revues individuelles, les agrège, priorise les problèmes critiques, et présente un rapport structuré à l'utilisateur.

---

## Scénario 7 : Documentation automatique

**Contexte :** Générer la documentation d'un module entier (docstrings + README).

### Flux d'interaction

1. **Le Cerveau liste les fichiers** — 8 fichiers dans le module `utils/`.

2. **Compréhension** — Pour chaque fichier, appel à `worker_explain_code` pour comprendre les fonctions publiques.

3. **Ajout des docstrings** — Pour chaque fichier, appel à `worker_refactor_code` avec l'instruction : "Ajoute des docstrings Google-style à toutes les fonctions publiques. Ne modifie PAS le code, uniquement les docstrings."

4. **Génération du README** — Le Cerveau synthétise les résumés de tous les fichiers et appelle `worker_generate_code` pour produire un README.md récapitulatif.

---

## Tableau récapitulatif

| # | Scénario | Outils utilisés | Gain estimé |
|---|---|---|---|
| 1 | Création de feature | `generate` + `refactor` | 70-80% tokens |
| 2 | Debug de logs | `analyze` | 95%+ tokens |
| 3 | Compression doc | `analyze` + `generate` | 85% tokens |
| 4 | Migration framework | `refactor` (boucle) | 75% tokens |
| 5 | Génération de tests | `explain` + `generate_tests` | 80% tokens |
| 6 | Code review | `analyze` (boucle) | 70% tokens |
| 7 | Documentation | `explain` + `refactor` + `generate` | 85% tokens |
