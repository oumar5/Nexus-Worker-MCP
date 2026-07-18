# Architecture — Nexus-Worker-MCP

## Vue d'ensemble

Nexus-Worker-MCP est un serveur MCP (Model Context Protocol) qui agit comme un **pont intelligent** entre un modèle principal coûteux (le Cerveau) et un modèle secondaire économique (le Worker). Il expose des outils MCP que le Cerveau appelle automatiquement pour déléguer les tâches lourdes en tokens.

---

## Diagramme d'architecture

```
                            ┌─────────────────────────────────────────┐
                            │           NEXUS-WORKER-MCP              │
                            │                                         │
 ┌──────────┐  stdio/HTTP   │  ┌───────────┐    ┌─────────────────┐  │    API Call     ┌──────────┐
 │ Cerveau  │──────────────▶│  │ Transport │───▶│  Tool Registry  │  │───────────────▶ │ Worker   │
 │ (IDE)    │               │  │  Layer    │    │                 │  │                 │ Provider │
 │          │◀──────────────│  │           │◀───│  - generate     │  │◀─────────────── │          │
 └──────────┘  Résultat     │  └───────────┘    │  - analyze      │  │   Réponse       └──────────┘
                            │                   │  - refactor     │  │
                            │                   │  - explain      │  │
                            │                   │  - test         │  │
                            │                   └────────┬────────┘  │
                            │                            │           │
                            │                   ┌────────▼────────┐  │
                            │                   │  Provider       │  │
                            │                   │  Adapter Layer  │  │
                            │                   │                 │  │
                            │                   │  - OpenAI       │  │
                            │                   │  - Anthropic    │  │
                            │                   │  - Ollama       │  │
                            │                   │  - Custom       │  │
                            │                   └────────┬────────┘  │
                            │                            │           │
                            │                   ┌────────▼────────┐  │
                            │                   │  Core Services  │  │
                            │                   │                 │  │
                            │                   │  - PromptEngine │  │
                            │                   │  - ErrorHandler │  │
                            │                   │  - Metrics      │  │
                            │                   │  - Logger       │  │
                            │                   └─────────────────┘  │
                            └─────────────────────────────────────────┘
```

---

## Couches du système

### 1. Transport Layer (Couche de transport)

Gère la communication entre le client IDE et le serveur MCP.

| Mode | Usage | Description |
|---|---|---|
| **stdio** | Outils IDE locaux (VS Code, Anti-Gravity, Claude Code) | Le serveur est lancé comme un processus enfant. La communication passe par stdin/stdout. C'est le **mode par défaut**. |
| **HTTP/SSE** | Applications distantes, multi-utilisateurs | Le serveur écoute sur un port réseau. Utile pour le déploiement en équipe ou le cloud. |

Le mode de transport est choisi via la variable d'environnement `MCP_TRANSPORT`. En mode `stdio`, aucune configuration réseau n'est nécessaire. En mode `http`, le serveur se lie à l'adresse et au port définis dans la configuration.

### 2. Tool Registry (Registre des outils)

Chaque outil MCP est déclaré avec :
- Un **nom** unique (ex: `worker_generate_code`)
- Une **description** détaillée — c'est elle qui "programme" le Cerveau pour savoir quand déléguer
- Des **paramètres** typés avec validation automatique
- Un **handler** qui exécute la logique de délégation

Le Cerveau lit ces déclarations au début de la session et sait automatiquement quand appeler chaque outil grâce à leur description. Voir [tools-reference.md](tools-reference.md) pour le détail.

### 3. Provider Adapter Layer (Couche d'adaptateurs)

C'est le cœur de l'agnosticisme. Chaque fournisseur d'API implémente une **interface commune** définie par le protocole `WorkerProvider`. Cette interface impose trois méthodes :

- **complete** — Envoie un prompt au modèle worker et retourne une réponse standardisée
- **health_check** — Vérifie que le fournisseur est joignable et fonctionnel
- **get_info** — Retourne les métadonnées du provider (nom, modèle, endpoint)

Le choix de l'adaptateur est fait automatiquement via un **Factory Pattern** basé sur la variable d'environnement `WORKER_PROVIDER`. Voir [provider-adapters.md](provider-adapters.md) pour le détail.

**Adaptateurs prévus :**

| Adaptateur | Fournisseurs compatibles |
|---|---|
| OpenAI Adapter | OpenAI, Azure OpenAI, Groq, Together AI, vLLM |
| Anthropic Adapter | Anthropic Claude (API directe) |
| Ollama Adapter | Modèles locaux via Ollama, LM Studio |
| Bedrock Adapter | AWS Bedrock (multi-modèles) |
| Custom Adapter | Tout endpoint HTTP personnalisé |

### 4. Core Services (Services de base)

| Service | Rôle |
|---|---|
| **PromptEngine** | Sélectionne et formate le template de prompt approprié selon le type de tâche. Les templates sont des fichiers Markdown stockés séparément. |
| **ErrorHandler** | Gère les retries avec backoff exponentiel, les timeouts, les fallbacks vers un provider de secours, et la protection anti-boucle infinie. |
| **Metrics** | Comptabilise les tokens consommés (input/output), le temps de réponse, le taux de succès par outil, et le nombre d'appels par session. |
| **Logger** | Journal structuré de tous les appels pour le diagnostic, avec niveau configurable. |

---

## Structure du projet

```
Nexus-Worker-MCP/
├── README.md
├── pyproject.toml                # Config du package Python
├── .env.example                  # Template de variables d'environnement
├── .gitignore
│
├── src/
│   └── nexus_worker/
│       ├── __init__.py
│       ├── __main__.py           # Point d'entrée (python -m nexus_worker)
│       ├── server.py             # Serveur MCP principal
│       ├── config.py             # Chargement de la configuration (.env)
│       │
│       ├── tools/                # Outils MCP exposés au Cerveau
│       │   ├── __init__.py
│       │   ├── generate.py       # worker_generate_code
│       │   ├── analyze.py        # worker_analyze_file
│       │   ├── refactor.py       # worker_refactor_code
│       │   ├── explain.py        # worker_explain_code
│       │   └── test.py           # worker_generate_tests
│       │
│       ├── providers/            # Adaptateurs fournisseurs
│       │   ├── __init__.py
│       │   ├── base.py           # Interface WorkerProvider (Protocol)
│       │   ├── openai_.py        # OpenAI / Azure / Compatible
│       │   ├── anthropic_.py     # Anthropic Claude
│       │   ├── ollama_.py        # Modèles locaux
│       │   └── factory.py        # Factory d'instanciation
│       │
│       ├── prompts/              # Templates de prompts système
│       │   ├── __init__.py
│       │   ├── engine.py         # Moteur de sélection de prompt
│       │   └── templates/        # Fichiers .md de prompts
│       │
│       ├── core/                 # Services transversaux
│       │   ├── __init__.py
│       │   ├── errors.py         # Gestion d'erreurs et fallback
│       │   ├── metrics.py        # Compteurs et statistiques
│       │   └── logger.py         # Logging structuré
│       │
│       └── utils/
│           ├── __init__.py
│           └── files.py          # Lecture/écriture de fichiers sécurisée
│
├── tests/
│   ├── conftest.py               # Fixtures pytest (mock provider, etc.)
│   ├── test_tools/
│   ├── test_providers/
│   └── test_prompts/
│
└── docs/                         # Ce dossier
```

---

## Flux d'exécution détaillé

### Séquence complète d'un appel outil

1. **L'utilisateur** envoie une demande au Cerveau (ex: "Ajoute une route d'authentification")
2. **Le Cerveau** analyse la demande, identifie qu'il s'agit de génération de code, et décide d'appeler `worker_generate_code`
3. **Le Transport Layer** reçoit l'appel d'outil via stdio ou HTTP et valide les paramètres
4. **Le Tool Handler** intercepte l'appel et prépare la requête
5. **Le PromptEngine** sélectionne le template de prompt adapté (ex: `generate.md`) et y injecte l'instruction et le contexte
6. **Le Provider Adapter** formule la requête API selon le fournisseur configuré et l'envoie au Worker
7. **Le Worker** traite la demande et retourne le résultat
8. **L'ErrorHandler** vérifie le résultat — en cas d'erreur, il déclenche un retry ou un fallback
9. **Les Metrics** enregistrent les statistiques de l'appel (tokens, latence, statut)
10. **Le Transport Layer** renvoie le résultat épuré au Cerveau
11. **Le Cerveau** lit le code généré (opération peu coûteuse en tokens d'entrée), valide la cohérence, et présente le résultat à l'utilisateur

---

## Principes de conception

1. **Agnosticisme total** — Aucun module hors des adaptateurs ne référence un fournisseur spécifique
2. **Fail gracefully** — Si le Worker est indisponible, le MCP retourne un message clair au Cerveau, jamais un crash
3. **Observabilité** — Chaque appel est tracé avec ses métriques (tokens, latence, statut)
4. **Sécurité** — Les fichiers accessibles sont limités aux répertoires déclarés dans `ALLOWED_PATHS`
5. **Extensibilité** — Ajouter un outil ou un adaptateur = ajouter un fichier, pas modifier le core
