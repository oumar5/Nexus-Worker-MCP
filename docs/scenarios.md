# Scénarios d'Usage — Nexus-Worker-MCP

Ce document décrit les cas d'utilisation concrets du système, avec les flux d'interaction détaillés entre le Cerveau, le MCP et le Worker.

> Pour comprendre les principes de conception derrière ces scénarios, consultez [design-patterns.md](design-patterns.md).

---

## Scénario 1 : Création d'une feature complète

**Contexte :** L'utilisateur demande d'ajouter un système d'authentification JWT à une API FastAPI existante.

### Flux d'interaction

```mermaid
sequenceDiagram
    participant U as 👤 Utilisateur
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    U->>B: "Ajoute un système d'authentification JWT"
    Note over B: Planifie : 3 fichiers à créer<br/>(modèle User, routes auth, middleware)

    B->>W: worker_generate_code("Crée un modèle User SQLAlchemy<br/>avec email, hashed_password, created_at")
    W-->>B: 45 lignes de code ✅
    Note over B: Lit le résultat (input tokens)<br/>Valide la cohérence ✅

    B->>W: worker_generate_code("Crée les routes d'auth JWT",<br/>context="Modèle User avec email et hash...")
    W-->>B: 120 lignes de code ✅
    Note over B: Lit le résultat...<br/>⚠️ Secret JWT hardcodé détecté

    B->>W: worker_refactor_code("Extraire le secret JWT<br/>dans une variable d'environnement")
    W-->>B: Code corrigé ✅

    B-->>U: "Feature JWT créée — 3 fichiers générés"
```

### Économie réalisée

| Sans Nexus | Avec Nexus |
|---|---|
| Le Cerveau génère ~165 lignes (Output très cher) | Le Cerveau ne génère que ~3 instructions courtes |
| Coût Output Cerveau : ~0,148 $ | Coût Output Cerveau : ~0,005 $ |

### Pattern appliqué

Ce scénario illustre le **Reviewer-Critic** : le Cerveau délègue, lit les résultats, détecte un problème (secret hardcodé), et re-délègue une correction ciblée plutôt que de réécrire tout le fichier.

---

## Scénario 2 : Analyse et debug de logs massifs

**Contexte :** Un serveur de production crashe. Le fichier de logs fait 15 000 lignes.

### Flux d'interaction

```mermaid
sequenceDiagram
    participant U as 👤 Utilisateur
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    U->>B: "Le serveur crashe, voici les logs"
    Note over B: 15 000 lignes — trop lourd<br/>pour son contexte

    B->>W: worker_analyze_file(logs.txt,<br/>"Isole les stack traces CRITICAL/FATAL<br/>avec 5 lignes de contexte")
    Note over W: Lit 15 000 lignes<br/>(tokens d'input économiques)
    W-->>B: 3 stack traces pertinentes (80 lignes)

    Note over B: Lit 80 lignes seulement<br/>Identifie une race condition<br/>dans le gestionnaire de connexions DB
    B-->>U: "Race condition identifiée dans<br/>le pool de connexions, voici la correction..."
```

### Économie réalisée

- **15 000 lignes** jamais envoyées au modèle cher
- Le Worker encaisse ~45 000 tokens d'input sur l'API économique
- Le Cerveau ne traite que **80 lignes** pertinentes → économie de **95%+ des tokens**

### Pattern appliqué

Ce scénario illustre la **protection de contexte** : le Worker agit comme un filtre qui réduit l'information brute en un résumé actionnable pour le Cerveau.

---

## Scénario 3 : Compression de documentation (RAG économique)

**Contexte :** L'utilisateur veut intégrer l'API Stripe. La doc officielle fait 200 pages.

### Flux d'interaction

```mermaid
sequenceDiagram
    participant U as 👤 Utilisateur
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    U->>B: "Intègre Stripe pour les paiements"

    B->>W: worker_analyze_file(stripe_docs.md,<br/>"Résume uniquement : créer client,<br/>session Checkout, webhooks.<br/>Inclure signatures et types.")
    Note over W: Lit 200 pages<br/>Produit un cheat sheet
    W-->>B: 60 lignes avec 3 endpoints clés

    Note over B: Contexte propre et ciblé :<br/>60 lignes au lieu de 200 pages

    B->>W: worker_generate_code(<br/>"Crée le service d'intégration Stripe",<br/>context="Résumé des 3 endpoints...")
    W-->>B: Service Stripe complet ✅

    B-->>U: "Service Stripe créé et prêt"
```

### Point clé

Le Cerveau n'a jamais vu les 200 pages de documentation Stripe. Son contexte reste propre et ciblé, ce qui améliore la qualité de ses décisions architecturales.

---

## Scénario 4 : Migration de framework

**Contexte :** Migrer 30 composants React de Class Components vers Functional Components (hooks).

### Flux d'interaction

```mermaid
sequenceDiagram
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    Note over B: Planifie : 30 fichiers,<br/>règles de conversion définies

    loop Pour chaque fichier (1 à 30)
        B->>W: worker_refactor_code(fichier_N.jsx,<br/>"this.state → useState,<br/>componentDidMount → useEffect,<br/>this.props → destructuration")
        W-->>B: Composant migré ✅
        Note over B: Lit le résultat,<br/>vérifie les imports
    end

    Note over B: 30/30 composants migrés ✅
```

### Point d'attention

Pour les migrations multi-fichiers, le Cerveau maintient un **registre de progression** pour ne pas perdre le fil. La boucle est gérée par le Cerveau, pas par le Worker — c'est le principe fondamental du pattern **Supervisor-Worker**.

### Opportunité de parallélisme

Les 30 fichiers étant indépendants, le Cerveau peut lancer **plusieurs refactorings en parallèle** :

```mermaid
gantt
    title Migration parallélisée (3 Workers simultanés)
    dateFormat s
    axisFormat %S s

    section Worker 1
    Fichier 1   :a1, 0, 3
    Fichier 4   :a2, 3, 6
    Fichier 7   :a3, 6, 9

    section Worker 2
    Fichier 2   :b1, 0, 4
    Fichier 5   :b2, 4, 7
    Fichier 8   :b3, 7, 10

    section Worker 3
    Fichier 3   :c1, 0, 3
    Fichier 6   :c2, 3, 7
    Fichier 9   :c3, 7, 10
```

---

## Scénario 5 : Génération de tests exhaustifs

**Contexte :** Un module métier de 400 lignes n'a aucun test.

### Flux d'interaction

```mermaid
sequenceDiagram
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    B->>W: worker_explain_code(module.py)
    Note over W: Lit 400 lignes,<br/>identifie 8 fonctions publiques
    W-->>B: Résumé structuré (fonctions, rôles, dépendances)

    Note over B: Comprend la logique<br/>sans avoir lu les 400 lignes

    B->>W: worker_generate_tests(module.py,<br/>coverage_level="exhaustive")
    Note over W: Génère 35 tests :<br/>cas nominaux, limites, erreurs
    W-->>B: Suite de tests complète ✅

    Note over B: Vérifie que les mocks<br/>sont cohérents et que les<br/>assertions sont pertinentes
```

### Pattern appliqué

Ce scénario combine deux patterns :
1. **Protection de contexte** : `worker_explain_code` permet au Cerveau de comprendre le module sans le charger
2. **Délégation systématique des tests** : La génération de tests est toujours déléguée (forte production d'output tokens)

---

## Scénario 6 : Revue de code automatisée (Code Review)

**Contexte :** L'utilisateur pousse un commit et veut une revue de qualité avant la PR.

### Flux d'interaction

```mermaid
sequenceDiagram
    participant B as 🧠 Cerveau
    participant W1 as ⚙️ Worker 1
    participant W2 as ⚙️ Worker 2
    participant W3 as ⚙️ Worker 3

    Note over B: 5 fichiers modifiés,<br/>350 lignes changées

    par Revues en parallèle
        B->>W1: worker_review_code(auth.py)
        B->>W2: worker_review_code(users.py)
        B->>W3: worker_review_code(api.py)
    end

    W2-->>B: Revue users.py ✅
    W1-->>B: Revue auth.py ✅
    W3-->>B: Revue api.py ✅

    B->>W1: worker_review_code(models.py)
    W1-->>B: Revue models.py ✅
    B->>W1: worker_review_code(tests.py)
    W1-->>B: Revue tests.py ✅

    Note over B: Agrège les 5 revues,<br/>priorise les problèmes critiques
```

### Point clé : le cache en action

Si l'utilisateur relance la revue sur le même fichier sans modification, le cache retourne le résultat instantanément (0 token, 0 latence).

---

## Scénario 7 : Documentation automatique

**Contexte :** Générer la documentation d'un module entier (docstrings + README).

### Flux d'interaction

```mermaid
sequenceDiagram
    participant B as 🧠 Cerveau
    participant W as ⚙️ Worker

    Note over B: 8 fichiers dans utils/

    loop Pour chaque fichier
        B->>W: worker_explain_code(fichier_N.py)
        W-->>B: Résumé des fonctions publiques

        B->>W: worker_document_code(fichier_N.py,<br/>style="google")
        W-->>B: Fichier avec docstrings insérées ✅
    end

    Note over B: Synthétise tous les résumés

    B->>W: worker_generate_code(<br/>"Crée un README.md récapitulatif",<br/>context="Résumés de tous les fichiers...")
    W-->>B: README.md complet ✅
```

---

## Tableau récapitulatif

| # | Scénario | Outils utilisés | Pattern principal | Gain estimé |
|---|---|---|---|---|
| 1 | Création de feature | `generate` + `refactor` | Reviewer-Critic | 80–90% tokens |
| 2 | Debug de logs | `analyze` | Protection de contexte | 95%+ tokens |
| 3 | Compression doc | `analyze` + `generate` | Protection de contexte | 85% tokens |
| 4 | Migration framework | `refactor` (boucle parallèle) | Parallélisme | 75% tokens |
| 5 | Génération de tests | `explain` + `generate_tests` | Délégation systématique | 90% tokens |
| 6 | Code review | `review` (parallèle + cache) | Parallélisme + Cache | 70–80% tokens |
| 7 | Documentation | `explain` + `document` + `generate` | Pipeline séquentiel | 85% tokens |
