# Installation et Configuration — Nexus-Worker-MCP

## Prérequis

- **Python** 3.11 ou supérieur
- **pip** (gestionnaire de paquets Python)
- **Git** (pour cloner le dépôt)
- Une **clé API** pour au moins un fournisseur LLM (OpenAI, Azure, Anthropic, Google Gemini, ou un modèle local via Ollama)

---

## Installation

### 1. Cloner le dépôt

Clonez le dépôt Git et accédez au répertoire du projet.

### 2. Créer un environnement virtuel

Créez un environnement virtuel Python dans le répertoire `.venv` et activez-le.

- **Windows :** activez avec `.venv\Scripts\activate`
- **macOS / Linux :** activez avec `source .venv/bin/activate`

### 3. Installer les dépendances

Installez le package en mode développement avec les dépendances de dev via `pip install -e ".[dev]"`. Pour la production, utilisez `pip install -e .` sans les extras de dev.

---

## Configuration

### Variables d'environnement

Copiez le fichier `.env.example` vers `.env` et remplissez vos valeurs. Les variables sont organisées en sections :

#### Configuration du Worker (modèle économique)

| Variable | Description | Exemple |
|---|---|---|
| `WORKER_PROVIDER` | Fournisseur à utiliser | `openai`, `anthropic`, `ollama`, `gemini` |
| `WORKER_API_BASE_URL` | URL de l'endpoint API | `https://api.openai.com/v1` |
| `WORKER_API_KEY` | Clé d'authentification API | `sk-...` |
| `WORKER_MODEL_NAME` | Nom du modèle déployé | `gpt-4o-mini` |
| `WORKER_API_VERSION` | Version API (Azure uniquement) | `2024-12-01-preview` |

#### Configuration du serveur MCP

| Variable | Description | Valeur par défaut |
|---|---|---|
| `MCP_TRANSPORT` | Mode de transport (`stdio` ou `http`) | `stdio` |
| `MCP_HOST` | Adresse d'écoute (mode http uniquement) | `127.0.0.1` |
| `MCP_PORT` | Port d'écoute (mode http uniquement) | `8080` |

#### Résilience

| Variable | Description | Valeur par défaut |
|---|---|---|
| `WORKER_MAX_RETRIES` | Nombre max de tentatives en cas d'erreur | `3` |
| `WORKER_TIMEOUT_SECONDS` | Timeout par requête | `120` |
| `WORKER_MAX_OUTPUT_TOKENS` | Limite de tokens de sortie | `4096` |

#### Fallback (optionnel)

| Variable | Description |
|---|---|
| `WORKER_FALLBACK_PROVIDER` | Provider de secours |
| `WORKER_FALLBACK_API_BASE_URL` | URL du provider de secours |
| `WORKER_FALLBACK_MODEL_NAME` | Modèle du provider de secours |

#### Sécurité et logging

| Variable | Description | Valeur par défaut |
|---|---|---|
| `ALLOWED_PATHS` | Répertoires autorisés (séparés par des virgules) | `.` (répertoire courant) |
| `LOG_LEVEL` | Niveau de log | `INFO` |
| `LOG_FILE` | Fichier de log | `nexus_worker.log` |
| `METRICS_ENABLED` | Activer les métriques | `true` |

#### Cache (optionnel)

| Variable | Description | Valeur par défaut |
|---|---|---|
| `CACHE_ENABLED` | Active le cache en mémoire | `true` |
| `CACHE_TTL_SECONDS` | Durée de vie d'une entrée en secondes | `3600` (1h) |
| `CACHE_MAX_SIZE` | Nombre max d'entrées dans le cache | `256` |

---

## Exemples de configuration par fournisseur

### OpenAI standard
Définir `WORKER_PROVIDER=openai`, l'URL `https://api.openai.com/v1`, votre clé API, et le modèle `gpt-4o-mini`.

### Azure OpenAI
Définir `WORKER_PROVIDER=openai`, l'URL de votre instance Azure (`https://votre-instance.openai.azure.com/`), votre clé Azure, le nom de votre deployment, et la version API.

### Google Gemini (nouveau)
Définir `WORKER_PROVIDER=gemini`, votre clé Google AI Studio dans `WORKER_API_KEY`, et le modèle `gemini-2.0-flash`. Aucune `WORKER_API_BASE_URL` nécessaire.

### Ollama (modèle local)
Définir `WORKER_PROVIDER=ollama`, l'URL locale (`http://localhost:11434`), et le modèle souhaité (ex: `qwen2.5-coder:7b`). Pas de clé API requise.

### Anthropic Claude
Définir `WORKER_PROVIDER=anthropic`, l'URL `https://api.anthropic.com`, votre clé Anthropic, et le modèle souhaité.

---

## Intégration avec les IDE

Le serveur MCP doit être déclaré dans la configuration de votre IDE. Chaque IDE a son propre fichier de configuration :

### VS Code (GitHub Copilot / Extensions MCP)
**Fichier :** `.vscode/mcp.json` ou settings utilisateur.
**Déclaration :** Ajoutez un serveur nommé `nexus-worker` avec la commande `python`, les arguments `["-m", "nexus_worker"]`, et le répertoire de travail pointant vers le projet. Le bon adaptateur est instancé **automatiquement** selon la variable d'environnement `WORKER_PROVIDER`. Le système maintient un registre interne qui associe chaque nom de provider à sa classe d'adaptateur. Si le nom est inconnu, une erreur explicite est levée avec la liste des valeurs possibles : `openai`, `anthropic`, `ollama`, `gemini`.

### Anti-Gravity (Gemini)
**Fichier :** Configuration MCP Anti-Gravity.
**Déclaration :** Même principe — serveur `nexus-worker` avec commande Python et arguments de module.

### Claude Code
**Méthode :** Commande CLI `claude mcp add nexus-worker -- python -m nexus_worker` ou via le fichier `.claude/mcp.json`.

### Cursor
**Fichier :** `.cursor/mcp.json`.
**Déclaration :** Même structure que VS Code.

---

## Vérification de l'installation

### Tests unitaires
Lancez les tests avec `python -m pytest tests/ -v` pour vérifier que tout fonctionne.

### Health check du provider
Lancez `python -m nexus_worker --health-check` pour vérifier la connexion au provider.

Résultat attendu :

| Vérification | Statut attendu |
|---|---|
| Provider détecté | ✅ (ex: openai) |
| Modèle configuré | ✅ (ex: gpt-4o) |
| Connexion API | ✅ OK avec latence affichée |
| Transport | ✅ (ex: stdio) |
| Outils enregistrés | ✅ (ex: 5 outils) |

---

## Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| `ConnectionError` au démarrage | Clé API invalide ou endpoint incorrect | Vérifiez `WORKER_API_BASE_URL` et `WORKER_API_KEY` |
| Le Cerveau n'appelle pas les outils | Serveur MCP non déclaré dans l'IDE | Vérifiez la configuration MCP de votre IDE |
| Timeout sur les gros fichiers | `WORKER_TIMEOUT_SECONDS` trop bas | Augmentez la valeur (ex: 180 ou 300) |
| `PermissionError` sur un fichier | Fichier hors des `ALLOWED_PATHS` | Ajoutez le répertoire dans `ALLOWED_PATHS` |
| Réponses incohérentes du worker | Modèle trop faible pour la tâche | Changez `WORKER_MODEL_NAME` pour un modèle plus capable |
