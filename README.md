# Nexus-Worker-MCP

> 🔌 Serveur MCP agnostique qui optimise vos coûts LLM en déléguant les tâches lourdes à un modèle "Ouvrier" économique.

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
| Coût élevé en Input + Output tokens | Réduction de 60-80% des coûts du modèle principal |

## Quick Start

```bash
# 1. Cloner et installer
git clone https://github.com/votre-org/Nexus-Worker-MCP.git
cd Nexus-Worker-MCP
python -m venv .venv
.venv\Scripts\activate  # Windows
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

| Client IDE | Transport | Statut |
|---|---|---|
| VS Code (Copilot) | stdio | ✅ Supporté |
| Anti-Gravity | stdio | ✅ Supporté |
| Claude Code | stdio | ✅ Supporté |
| Cursor | stdio | ✅ Supporté |
| Applications distantes | HTTP/SSE | ✅ Supporté |

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
| [Contributing](docs/contributing.md) | Guide de contribution |

## Licence

MIT — Voir [LICENSE](LICENSE)
