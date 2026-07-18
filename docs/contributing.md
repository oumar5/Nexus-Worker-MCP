# Guide de Contribution — Nexus-Worker-MCP

## Bienvenue

Merci de votre intérêt pour Nexus-Worker-MCP ! Ce guide explique comment contribuer au projet, que ce soit pour corriger un bug, ajouter un adaptateur de fournisseur, proposer un nouvel outil MCP, ou améliorer la documentation.

---

## Types de contributions

| Type | Description | Difficulté |
|---|---|---|
| 🐛 Bug fix | Corriger un comportement inattendu | Facile |
| 📝 Documentation | Améliorer ou traduire la documentation | Facile |
| 🔌 Nouvel adaptateur | Ajouter le support d'un nouveau fournisseur LLM | Moyenne |
| 🛠️ Nouvel outil MCP | Proposer un nouvel outil de délégation | Moyenne |
| 📐 Nouveau template | Créer ou améliorer un template de prompt | Moyenne |
| 🏗️ Architecture | Modification du core (transport, error handling, metrics) | Avancée |

---

## Règles générales

### Structure du code

- **Un fichier = une responsabilité.** Ne pas mélanger la logique d'un outil avec celle d'un adaptateur.
- **L'interface `WorkerProvider` est sacrée.** Tout adaptateur DOIT implémenter les trois méthodes (`complete`, `health_check`, `get_info`) sans exception.
- **Les descriptions d'outils sont le cœur du produit.** Toute modification d'une description d'outil doit être justifiée et testée avec au moins deux modèles principaux différents.

### Conventions de nommage

| Élément | Convention | Exemple |
|---|---|---|
| Fichiers de modules | snake_case | `openai_.py`, `smart_chunker.py` |
| Classes | PascalCase | `OpenAIAdapter`, `PromptEngine` |
| Fonctions/méthodes | snake_case | `get_provider`, `run_health_check` |
| Variables d'environnement | SCREAMING_SNAKE_CASE | `WORKER_API_KEY` |
| Outils MCP | snake_case préfixé `worker_` | `worker_generate_code` |

### Style de code

- Python 3.11+ avec **type hints** obligatoires sur toutes les fonctions publiques
- Docstrings Google-style sur toutes les classes et fonctions publiques
- Formatage avec **Black** (longueur de ligne : 100)
- Linting avec **Ruff**
- Tri des imports avec **isort**

---

## Ajouter un nouvel adaptateur de fournisseur

1. Créer le fichier dans `src/nexus_worker/providers/` (nommé `fournisseur_.py`)
2. Implémenter les trois méthodes de l'interface `WorkerProvider`
3. Enregistrer l'adaptateur dans le Factory (`factory.py`)
4. Ajouter les variables d'environnement correspondantes dans `.env.example`
5. Documenter le fournisseur dans `docs/provider-adapters.md`
6. Écrire les tests dans `tests/test_providers/`

---

## Ajouter un nouvel outil MCP

1. Créer le fichier dans `src/nexus_worker/tools/` (nommé selon la fonction)
2. Définir les paramètres avec validation de type
3. Rédiger la **description d'outil** — c'est l'élément le plus critique. Elle doit indiquer clairement au Cerveau **quand** utiliser l'outil et **quand ne pas** l'utiliser
4. Créer le template de prompt correspondant dans `src/nexus_worker/prompts/templates/`
5. Documenter l'outil dans `docs/tools-reference.md`
6. Ajouter un scénario d'usage dans `docs/scenarios.md`
7. Écrire les tests dans `tests/test_tools/`

---

## Tests

### Lancer les tests

Exécutez la suite de tests complète avec pytest. Les tests doivent passer à 100% avant toute pull request.

### Mock obligatoire

Tous les tests doivent utiliser des **mocks** pour les appels API. Aucun test ne doit effectuer de véritable appel réseau. Les fixtures partagées sont définies dans `tests/conftest.py`.

### Couverture

Visez une couverture de **80% minimum** pour tout nouveau code. Les adaptateurs et les outils doivent couvrir au minimum :
- Le cas nominal (happy path)
- Les erreurs de connexion
- Les réponses vides ou malformées

---

## Pull Request

### Checklist avant soumission

- [ ] Les tests passent localement
- [ ] Le code respecte les conventions (Black, Ruff, isort)
- [ ] Les type hints sont présents sur toutes les fonctions publiques
- [ ] La documentation est mise à jour si nécessaire
- [ ] Les variables d'environnement nouvelles sont ajoutées à `.env.example`
- [ ] Le commit message est clair et descriptif

### Format des commits

Utilisez le format **Conventional Commits** :

| Préfixe | Usage |
|---|---|
| `feat:` | Nouvelle fonctionnalité |
| `fix:` | Correction de bug |
| `docs:` | Modification de documentation |
| `refactor:` | Refactoring sans changement fonctionnel |
| `test:` | Ajout ou modification de tests |
| `chore:` | Maintenance (CI, dépendances, config) |

---

## Questions et discussions

Pour toute question sur l'architecture, les choix de design, ou une proposition de feature, ouvrez une **Issue** sur le dépôt GitHub avant de commencer le développement. Cela permet d'aligner la vision et d'éviter le travail en double.
