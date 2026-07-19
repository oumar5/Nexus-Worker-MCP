# Nexus-Worker-MCP

[![CI](https://github.com/oumar5/Nexus-Worker-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/oumar5/Nexus-Worker-MCP/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-green)](pyproject.toml)

> Serveur MCP agnostique qui optimise vos coûts LLM en déléguant les tâches lourdes à un modèle "Ouvrier" économique.

## Concept

Nexus-Worker-MCP implémente le pattern **Planificateur / Exécuteur / Critique** :

- **Le Cerveau** (modèle principal dans votre IDE) planifie, supervise et valide
- **Le Worker** (modèle économique via API) exécute les tâches lourdes en tokens
- **Le MCP** (ce projet) orchestre la délégation entre les deux

```
┌─────────────┐     Tool Call      ┌──────────────┐     API Call      ┌──────────────┐
│   Cerveau   │ ──────────────────▶│  Nexus MCP   │ ───────────────▶ │   Worker     │
│  (Claude,   │                    │  (Routeur)   │                  │  (GPT-4o,    │
│   GPT-5…)   │ ◀──────────────── │              │ ◀─────────────── │   Ollama…)   │
│             │   Résultat épuré   │              │   Réponse brute  │              │
└─────────────┘                    └──────────────┘                  └──────────────┘
```

## Pourquoi ?

| Sans Nexus | Avec Nexus |
|---|---|
| Le modèle cher lit 1200 lignes de code | Le worker lit, le cerveau reçoit un résumé de 50 lignes |
| Le modèle cher génère 300 lignes de tests | Le worker génère, le cerveau valide |
| Le modèle cher fait la revue de code | Le worker revèle les bugs, le cerveau décide |
| Coût élevé en Input + Output tokens | Réduction de 60-80% des coûts du modèle principal |

## Quick Start

```bash
# 1. Cloner et installer
git clone https://github.com/oumar5/Nexus-Worker-MCP.git
cd Nexus-Worker-MCP
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -e .

# 2. Configurer
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Tester
python -m pytest tests/

# 4. Lancer
python -m nexus_worker
```

## Compatibilité

### Clients IDE

| Client IDE | Transport | Statut |
|---|---|---|
| VS Code (Copilot) | stdio | ✅ Supporté |
| Anti-Gravity | stdio | ✅ Supporté |
| Claude Code | stdio | ✅ Supporté |
| Cursor | stdio | ✅ Supporté |
| Applications distantes | HTTP/SSE | ✅ Supporté |

### Providers Worker

| Provider | Modèles recommandés | Statut |
|---|---|---|
| OpenAI | gpt-4o-mini, gpt-4o | ✅ Supporté |
| Anthropic | claude-3-haiku, claude-3.5-haiku | ✅ Supporté |
| Google Gemini | gemini-2.0-flash, gemini-1.5-flash | ✅ Supporté |
| Ollama (local) | codellama, qwen2.5-coder | ✅ Supporté |
| Azure OpenAI | Tout modèle déployé | ✅ Supporté |

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | Architecture technique détaillée |
| [Installation](docs/setup.md) | Guide d'installation et configuration |
| [Outils MCP](docs/tools-reference.md) | Référence complète des outils exposés |
| [Adaptateurs](docs/provider-adapters.md) | Guide des fournisseurs supportés |
| [Scénarios](docs/scenarios.md) | Cas d'usage détaillés avec flux |
| [Gestion d'erreurs](docs/error-handling.md) | Stratégie de résilience et fallback |
| [Templates de prompts](docs/prompt-templates.md) | Prompts systèmes par type de tâche |
| [Analyse FinOps](docs/finops.md) | Analyse financière et ROI de l'architecture |
| [Contributing](docs/contributing.md) | Guide de contribution |

## Licence

MIT — Voir [LICENSE](LICENSE)
