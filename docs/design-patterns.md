# Design Patterns & Stratégie de Délégation — Nexus-Worker-MCP

Ce document formalise les patterns architecturaux, les stratégies de délégation et les raisonnements théoriques derrière les choix de conception de Nexus-Worker-MCP. Il sert de référence pour comprendre **pourquoi** le système est conçu ainsi, et **comment** optimiser son utilisation.

---

## 1. Pattern Supervisor-Worker

Nexus-Worker-MCP implémente le pattern **Supervisor-Worker** (aussi appelé Routeur-Exécutant). C'est un modèle architectural reconnu dans les systèmes multi-agents.

```mermaid
flowchart TB
    subgraph Supervisor["🧠 Superviseur (Cerveau)"]
        Plan["Planification"]
        Decide["Décision de délégation"]
        Validate["Validation du résultat"]
    end

    subgraph Worker["⚙️ Exécuteur (Worker)"]
        Exec["Exécution Single-Shot"]
    end

    Plan --> Decide
    Decide -->|"Tâche > seuil"| Exec
    Decide -->|"Tâche < seuil"| Plan
    Exec -->|"Résultat"| Validate
    Validate -->|"OK"| Plan
    Validate -->|"Correction nécessaire"| Decide

    style Supervisor fill:#1a1a2e,stroke:#e94560,stroke-width:2px,color:#eee
    style Worker fill:#0f3460,stroke:#533483,stroke-width:2px,color:#eee
```

### Caractéristiques clés

| Aspect | Choix de Nexus | Justification |
|:---|:---|:---|
| **Type de Worker** | Single-Shot (pas d'agent) | Prédictible, stable, parallélisable |
| **Boucle de raisonnement** | Côté Cerveau uniquement | Évite les dérapages de coût et les boucles infinies |
| **Outils propres au Worker** | Aucun | Le Worker produit du texte, il ne prend pas de décisions |
| **Mémoire du Worker** | Aucune (stateless) | Chaque appel est indépendant, pas de contexte qui s'accumule |

### Pourquoi pas des Workers "Agents" ?

Dans une architecture avec un Cerveau central, donner de l'autonomie (outils, mémoire, boucle de raisonnement) aux Workers comporte des risques :

- **Boucle infinie** — Un worker-agent qui s'auto-corrige peut tourner en boucle et consommer tout le budget.
- **Dérive de comportement** — Un worker-agent peut prendre des décisions contradictoires avec celles du Cerveau.
- **Explosion de tokens** — Chaque itération de la boucle agentic accumule du contexte (l'historique des actions précédentes), ce qui augmente exponentiellement les tokens d'entrée.
- **Imprévisibilité** — Le résultat d'un worker-agent est non-déterministe et difficile à auditer.

Le choix Single-Shot garantit : **1 instruction → 1 réponse → coût prévisible**.

---

## 2. Stratégie de Délégation

### Les seuils de délégation

Les descriptions des outils MCP programment le Cerveau pour savoir **quand** déléguer. Ces seuils sont calibrés pour que le surcoût de coordination (formuler le prompt, transmettre, lire le résultat) reste toujours **inférieur** au coût de faire le travail soi-même.

```mermaid
graph LR
    subgraph Zone_Brain["🧠 Zone Cerveau seul"]
        A["Correction < 10 lignes"]
        B["Décision d'architecture"]
        C["Planification"]
    end

    subgraph Zone_Hybrid["🔄 Zone hybride"]
        D["Code 10-30 lignes<br/>(selon le contexte)"]
    end

    subgraph Zone_Worker["⚡ Zone Worker"]
        E["Génération > 30 lignes"]
        F["Refactoring > 20 lignes"]
        G["Analyse fichier > 50 lignes"]
        H["Tests (toujours)"]
        I["Revue de code (toujours)"]
        J["Documentation (toujours)"]
    end

    style Zone_Brain fill:#533483,color:#fff,stroke:none
    style Zone_Hybrid fill:#e94560,color:#fff,stroke:none
    style Zone_Worker fill:#0f3460,color:#fff,stroke:none
```

### Justification économique des seuils

Le point d'équilibre dépend du **ratio de prix** entre le Cerveau et le Worker :

| Modèle | Output / 1M tokens | Ratio vs GPT-4o-mini |
|:---|:---|:---|
| GPT-5.6 Sol (Cerveau) | 30,00 $ | **50×** |
| Gemini 3.1 Pro (Cerveau) | 12,00 $ | **20×** |
| GPT-4o-mini (Worker) | 0,60 $ | 1× |

**Calcul du point d'équilibre pour la génération de code :**

- **Coût de délégation** = tokens d'instruction du Cerveau (~50 tokens output × prix cher) + tokens de lecture du résultat (~N tokens input × prix cher) + tokens du Worker (~N tokens output × prix économique)
- **Coût sans délégation** = N tokens output × prix cher

Pour GPT-5.6 Sol → GPT-4o-mini, la délégation devient rentable dès **~15 lignes de code** (environ 150 tokens). Le seuil de 30 lignes intègre une marge de sécurité pour couvrir les cas où l'instruction doit être très détaillée.

---

## 3. Optimisation des Tokens : Input vs Output

### La règle fondamentale

> **Les tokens d'entrée (input) coûtent 3 à 6× moins cher que les tokens de sortie (output), quel que soit le modèle.**

| Modèle | Input / 1M tokens | Output / 1M tokens | Ratio Output/Input |
|:---|:---|:---|:---|
| GPT-5.6 Sol | 5,00 $ | 30,00 $ | **6×** |
| Gemini 3.1 Pro | 2,00 $ | 12,00 $ | **6×** |
| GPT-4o-mini | 0,15 $ | 0,60 $ | **4×** |

### Implication architecturale

Cette asymétrie de prix est **la raison fondamentale** de l'architecture Nexus :

```mermaid
flowchart LR
    subgraph Sans_Nexus["❌ Sans Nexus"]
        direction TB
        B1["🧠 Cerveau"]
        B1 -->|"📤 Output: 500 lignes de code<br/>= 3 000 tokens × 30$/M<br/>= 0,090 $"| R1["Résultat"]
    end

    subgraph Avec_Nexus["✅ Avec Nexus"]
        direction TB
        B2["🧠 Cerveau"]
        B2 -->|"📤 Output: instruction courte<br/>= 50 tokens × 30$/M<br/>= 0,0015 $"| W2["⚙️ Worker"]
        W2 -->|"📤 Output: 500 lignes<br/>= 3 000 tokens × 0,60$/M<br/>= 0,0018 $"| B3["🧠 Cerveau"]
        B3 -->|"📥 Input: lit le résultat<br/>= 3 000 tokens × 5$/M<br/>= 0,015 $"| R2["Résultat"]
    end

    style Sans_Nexus fill:#e94560,color:#fff,stroke:none
    style Avec_Nexus fill:#2ecc71,color:#fff,stroke:none
```

**Résultat :**
- Sans Nexus : **0,090 $** (Output cher du Cerveau)
- Avec Nexus : **0,018 $** (Instruction + Worker + Lecture)
- **Économie : 80%**

### Le piège du "Copier-Coller" par le Cerveau

> ⚠️ **Attention** : Si le Cerveau doit réécrire le code du Worker pour le sauvegarder dans un fichier, il consomme autant de tokens de sortie (chers) que s'il avait écrit le code lui-même. L'économie est alors annulée.

**Workflow optimal (Reviewer-Critic) :**

1. Le Worker génère le code → **Output tokens économiques**
2. Le Cerveau lit le code → **Input tokens modérés**
3. Le Cerveau corrige uniquement les lignes problématiques → **Output tokens minimaux**

**Workflow sous-optimal :**

1. Le Worker génère le code → Output tokens économiques
2. Le Cerveau lit le code → Input tokens modérés
3. ❌ Le Cerveau réécrit tout le code pour le sauvegarder → **Output tokens très chers** (l'économie est perdue)

---

## 4. Qualité du Code : Cerveau seul vs Délégation

### Comparaison qualitative

| Critère | 🧠 Cerveau seul | ⚡ Délégation au Worker |
|:---|:---|:---|
| **Cohérence globale** | ★★★★★ — Vision complète du projet | ★★★☆☆ — Ne connaît que ce qu'on lui donne |
| **Qualité unitaire** | ★★★★☆ — Très bon | ★★★★★ — Excellent sur une tâche isolée |
| **Style uniforme** | ★★★★★ — Un seul "auteur" | ★★★☆☆ — Risque de styles différents |
| **Gestion des imports** | ★★★★★ — Connaît tout le projet | ★★☆☆☆ — Risque de réinventer l'existant |
| **Performance** | ★★★★☆ | ★★★★★ — Optimisé pour la tâche |

### Stratégies pour égaliser la qualité

#### A. Injection de Contexte

Toujours remplir le paramètre `context` des outils avec les conventions du projet :

```
❌ Mauvaise délégation :
"Crée une fonction qui formate une date."

✅ Bonne délégation (injection de contexte) :
"Crée une fonction qui formate une date.
Contexte : Dans ce projet, on utilise datetime standard,
on gère les erreurs avec try/except en loggant via
'from core.logger import logger', et on utilise le typage strict."
```

#### B. Partage de Squelettes (Stubs)

Inclure les signatures des fonctions et types existants pour éviter la duplication :

```
"Voici les interfaces existantes que tu dois utiliser :
- `def get_user(id: int) -> dict` (dans utils/users.py)
- `class AuthError(Exception)` (dans core/errors.py)
Ne réimplémente PAS ces fonctions, importe-les."
```

#### C. Revue par le Cerveau (Pattern Reviewer-Critic)

Le Cerveau agit comme un **Tech Lead** qui relit la Pull Request d'un développeur :

```mermaid
flowchart TD
    W["⚙️ Worker produit le code"] --> B["🧠 Cerveau lit le résultat"]
    B --> Q{"Le code est-il correct ?"}
    Q -->|"✅ Oui"| OK["Intégrer sans modification<br/>(0 output token supplémentaire)"]
    Q -->|"⚠️ Presque"| Fix["Corriger 1-2 lignes<br/>(~10 output tokens)"]
    Q -->|"❌ Non"| Redo["Re-déléguer avec instruction corrigée<br/>(~80 output tokens)"]

    style W fill:#0f3460,color:#fff,stroke:none
    style B fill:#1a1a2e,color:#fff,stroke:#e94560
    style OK fill:#2ecc71,color:#fff,stroke:none
    style Fix fill:#f39c12,color:#fff,stroke:none
    style Redo fill:#e94560,color:#fff,stroke:none
```

---

## 5. Stratégie de Démarrage de Projet

### Quand introduire le Worker ?

```mermaid
gantt
    title Cycle de vie d'un projet avec Nexus
    dateFormat  X
    axisFormat %s

    section Phase 1 : Fondations
    Architecture & conventions    :active, a1, 0, 3
    Fichiers de base (< 1000 LOC) :a2, 3, 6

    section Phase 2 : Mise à l'échelle
    Génération de code (Worker)    :crit, b1, 6, 10
    Tests unitaires (Worker)       :crit, b2, 8, 12
    Documentation (Worker)         :crit, b3, 10, 13

    section Phase 3 : Maintenance
    Refactoring (Worker)           :c1, 13, 16
    Revue de code (Worker)         :c2, 14, 17
    Analyse de fichiers (Worker)   :c3, 15, 18
```

| Phase | Cerveau seul ? | Worker ? | Justification |
|:---|:---|:---|:---|
| **Phase 1 : Fondations** (0–1 000 lignes) | ✅ Oui | ❌ Non | Le contexte est petit, le Cerveau doit poser les bases avec cohérence totale |
| **Phase 2 : Mise à l'échelle** (1 000+ lignes) | Supervision | ✅ Oui | Les conventions sont établies, le Worker peut produire en masse |
| **Phase 3 : Maintenance** | Décisions | ✅ Oui | Le Worker analyse, refactore et documente le code existant |

### Règle d'or

> **Le Cerveau pose l'architecture. Le Worker la remplit.**
>
> Ne déléguez jamais la création de la colonne vertébrale de votre application (la structure des dossiers, les interfaces, les conventions d'erreur). Déléguez le travail répétitif qui suit ces conventions.

---

## 6. Parallélisme Asynchrone

Les Workers Nexus étant des appels Single-Shot asynchrones (`async/await`), le Cerveau peut lancer **plusieurs tâches en parallèle** sans surcoût.

```mermaid
sequenceDiagram
    participant B as 🧠 Cerveau
    participant N1 as ⚡ Nexus (Worker 1)
    participant N2 as ⚡ Nexus (Worker 2)
    participant N3 as ⚡ Nexus (Worker 3)

    B->>N1: worker_generate_tests("auth.py")
    B->>N2: worker_refactor_code("users.py")
    B->>N3: worker_review_code("api.py")

    Note over N1,N3: Les 3 appels s'exécutent en parallèle

    N2-->>B: Code refactoré ✅
    N1-->>B: Tests générés ✅
    N3-->>B: Revue terminée ✅

    Note over B: Le Cerveau traite les 3 résultats
```

### Avantages du parallélisme

- **Temps total** = temps du Worker le plus lent (pas la somme)
- **Coût identique** — 3 appels parallèles coûtent autant que 3 appels séquentiels
- **Protection du contexte** — Le Cerveau ne charge pas les 3 fichiers dans sa mémoire en même temps

---

## 7. Comparaison avec les Alternatives

### Nexus (Supervisor-Worker) vs Multi-Agent complet

```mermaid
graph TB
    subgraph NexusArch["Nexus : Supervisor-Worker"]
        N_B["🧠 Cerveau<br/>(chef d'orchestre)"]
        N_W1["⚙️ Worker 1<br/>(single-shot)"]
        N_W2["⚙️ Worker 2<br/>(single-shot)"]
        N_W3["⚙️ Worker 3<br/>(single-shot)"]
        N_B --> N_W1
        N_B --> N_W2
        N_B --> N_W3
        N_W1 --> N_B
        N_W2 --> N_B
        N_W3 --> N_B
    end

    subgraph MultiAgent["Multi-Agent : Agents autonomes"]
        M_O["🧠 Orchestrateur"]
        M_A1["🤖 Agent Testeur<br/>(boucle + outils)"]
        M_A2["🤖 Agent Revieweur<br/>(boucle + outils)"]
        M_A3["🤖 Agent Codeur<br/>(boucle + outils)"]
        M_O --> M_A1
        M_O --> M_A2
        M_O --> M_A3
        M_A1 -->|"Historique<br/>croissant"| M_A1
        M_A2 -->|"Historique<br/>croissant"| M_A2
        M_A3 -->|"Historique<br/>croissant"| M_A3
        M_A1 --> M_O
        M_A2 --> M_O
        M_A3 --> M_O
    end

    style NexusArch fill:#2ecc71,color:#fff,stroke:none
    style MultiAgent fill:#e94560,color:#fff,stroke:none
```

| Critère | Nexus (Supervisor-Worker) | Multi-Agent complet |
|:---|:---|:---|
| **Tokens consommés** | Prévisibles (1 aller-retour) | Imprévisibles (boucles multiples) |
| **Coût** | Bas et stable | Potentiellement élevé |
| **Latence** | Faible (~2-5 s par appel) | Variable (~10-60 s par agent) |
| **Qualité unitaire** | Très bonne | Excellente (auto-correction) |
| **Complexité** | Simple | Élevée |
| **Risque de dérapage** | Quasi nul | Élevé (boucles infinies) |
| **Cas d'usage idéal** | Tâches bien définies sur 1 fichier | Tâches complexes nécessitant de l'exploration |
| **Débogage** | Facile (1 prompt → 1 résultat) | Difficile (historique multi-tours) |

---

## Résumé

```mermaid
mindmap
    root["🏗️ Nexus-Worker-MCP<br/>Design Patterns"]
        Supervisor-Worker
            Worker Single-Shot
            Cerveau chef d orchestre
            Pas de boucle côté Worker
        Seuils de Délégation
            Génération > 30 lignes
            Refactoring > 20 lignes
            Analyse > 50 lignes
            Tests : toujours
        Optimisation Tokens
            Input tokens 3-6x moins chers
            Minimiser les Output du Cerveau
            Piège du copier-coller
        Reviewer-Critic
            Worker produit
            Cerveau lit
            Correction chirurgicale
        Cycle de Vie Projet
            Phase 1 : Cerveau seul
            Phase 2 : Worker en masse
            Phase 3 : Worker en maintenance
        Parallélisme
            Appels async simultanés
            Temps = max pas somme
            Coût identique
```
