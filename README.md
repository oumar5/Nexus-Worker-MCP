# Nexus-Worker-MCP

[![CI](https://github.com/oumar5/Nexus-Worker-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/oumar5/Nexus-Worker-MCP/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-green)](pyproject.toml)

> Serveur MCP agnostique qui optimise vos coûts LLM en déléguant les tâches lourdes à un modèle "Ouvrier" économique.

## Concept

Nexus-Worker-MCP implémente le pattern **Supervisor-Worker** (Planificateur / Exécuteur / Critique) :

- **Le Cerveau** (modèle principal dans votre IDE) planifie, supervise et valide (pattern *Reviewer-Critic*)
- **Le Worker** (modèle économique via API) exécute les tâches lourdes en tokens (Single-Shot, parallélisable)
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
| [Architecture](docs/architecture.md) | Architecture technique avec diagrammes Mermaid |
| [Design Patterns](docs/design-patterns.md) | Patterns architecturaux et stratégie de délégation |
| [Installation](docs/setup.md) | Guide d'installation et configuration |
| [Outils MCP](docs/tools-reference.md) | Référence complète des 8 outils exposés |
| [Adaptateurs](docs/provider-adapters.md) | Guide des fournisseurs supportés |
| [Scénarios](docs/scenarios.md) | Cas d'usage détaillés avec flux et diagrammes |
| [Gestion d'erreurs](docs/error-handling.md) | Stratégie de résilience et fallback |
| [Templates de prompts](docs/prompt-templates.md) | Prompts systèmes par type de tâche |
| [Analyse FinOps](docs/finops.md) | Analyse financière, économie de tokens et ROI |
| [Contributing](docs/contributing.md) | Guide de contribution |

## Roadmap (v2.0)

- **Tool-based Routing (Routage par Outil)** : Possibilité de configurer un modèle spécifique pour chaque outil (ex: `WORKER_GENERATE_CODE_MODEL=claude-3-5-sonnet` pour le code, et `WORKER_REVIEW_CODE_MODEL=gpt-4o-mini` pour la relecture) afin de pousser l'optimisation des coûts à son maximum.
- **Agenticité micro (Self-Verification bornée)** : Sur les outils producteurs de code (`generate_code`, `refactor_code`, `generate_tests`), le Worker pourra valider sa propre sortie (parse/lint) et itérer 2-3 fois max pour corriger ses erreurs. **Ligne rouge** : le Worker ne lit jamais d'autres fichiers que celui fourni — l'orchestration agentique reste au Cerveau. Périmètre v1 : registre de validateurs multi-langage extensible, activation par flag `verify` par outil.
- **Edits chirurgicaux pour `refactor_code`** : Optionnellement, le Worker pourra renvoyer une liste d'edits `[{old_string, new_string}, ...]` au lieu du fichier réécrit intégralement. Application côté MCP avec exigence d'unicité de `old_string` (même contrat que l'outil `Edit` de Claude Code) — pas de numéros de ligne, pas de diffs fuzzy. **Bénéfice** : sortie compacte (baisse forte des tokens output sur gros fichiers modifiés localement). **Prérequis** : la Self-Verification doit être en place (un edit qui casse la syntaxe est plus discret qu'un rewrite qui la casse). Périmètre limité à `refactor_code` — `generate_code` et `generate_tests` créent du contenu neuf et restent en rewrite. Le Worker ne touche jamais lui-même au filesystem : il produit les edits, le MCP les applique.
- **Support de nouveaux providers** : Intégration de nouveaux LLMs selon les besoins de la communauté.

## Licence

MIT — Voir [LICENSE](LICENSE)
