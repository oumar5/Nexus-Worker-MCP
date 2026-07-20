# Référence des Outils MCP — Nexus-Worker-MCP

Ce document détaille chaque outil (Tool) exposé par le serveur MCP au modèle principal (le Cerveau). Les **descriptions** sont le mécanisme central qui indique au Cerveau **quand** et **comment** déléguer au Worker.

> Les descriptions ci-dessous sont volontairement concises et factuelles. Elles décrivent ce que l'outil fait, quand l'appeler et comment le paramétrer — sans slogan marketing ni chiffres de coût codés en dur (qui varient selon les modèles utilisés). Le calcul économique est laissé à la couche appelante.

---

## 1. `worker_generate_code`

**Objectif :** Générer du code neuf — fonctions, classes, fichiers entiers.

### Description (vue par le Cerveau)

> *"Génère du code via le Worker économique. À utiliser pour produire plus de ~30 lignes de code. Renvoie le code structuré et peut l'écrire sur disque."*
>
> *"Option `auto_save=True` : le Worker écrit directement le fichier ; tu n'as plus qu'à relire et corriger si besoin."*
>
> **NE PAS utiliser pour :** Des ajouts/corrections de moins de ~10 lignes.

### Paramètres

- `instruction` (string) : Exigences techniques détaillées.
- `target_path` (string, optionnel) : Chemin du fichier de destination (sert de contexte).
- `language` (string, optionnel) : Langage de programmation cible.
- `context` (string, optionnel) : Contexte additionnel (patterns, imports).
- `auto_save` (boolean, optionnel) : Si True, enregistre directement le code généré dans `target_path`.

### Retour
```json
{
  "status": "success",
  "code": "def hello():\n    print('world')",
  "language": "python",
  "saved": true,
  "saved_path": "src/hello.py",
  "tokens_used": {"input": 120, "output": 45},
  "model": "gpt-4o"
}
```

---

## 2. `worker_analyze_file`

**Objectif :** Lire et analyser un fichier volumineux sans encombrer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Analyse un fichier source via le Worker et renvoie une analyse structurée et compacte, plutôt que le texte brut du fichier."*
>
> *"Déclencheurs : 'analyse', 'résume', 'fais un rapport', 'audit'."*
>
> *"Multi-fichiers (ex : 'analyse le module UI') : appeler une fois par fichier, chaque appel renvoie un résumé compact, puis synthétiser les résumés pour le rapport global. Ne pas lire tous les fichiers soi-même."*
>
> **Exception :** un seul fichier de moins de ~50 lignes.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin absolu ou relatif du fichier à analyser |
| `question` | string | ✅ | Question ou consigne d'analyse |
| `focus_lines` | string | ❌ | Plage de lignes à cibler (ex: "100-200") |

### Retour

`status`, `analysis`, `file_info`, `tokens_used`, `model`

> **Note :** Les résultats sont mis en cache (TTL configurable). Un deuxième appel avec les mêmes contenus et prompt est instantané.

---

## 3. `worker_refactor_code`

**Objectif :** Appliquer des modifications lourdes sur du code existant.

### Description (vue par le Cerveau)

> *"Refactorise un fichier via le Worker en une seule passe, en tenant compte de son contexte. À utiliser pour un refactoring qui touche de nombreuses lignes."*
>
> *"Multi-fichiers (ex : 'refactorise tout le module') : appeler une fois par fichier."*
>
> *"Option `auto_save=True` : écriture directe sur disque."*
>
> **NE PAS utiliser pour :** Changer une seule ligne.

### Paramètres

- `file_path` (string) : Fichier à refactorer.
- `instruction` (string) : Directives de modification.
- `target_lines` (string, optionnel) : Plage de lignes (ex: "42-98").
- `context` (string, optionnel) : Règles ou conventions spécifiques.
- `auto_save` (boolean, optionnel) : Si True, écrase directement le fichier avec le nouveau code.

### Retour
```json
{
  "status": "success",
  "refactored_code": "...",
  "file_info": {"path": "api.py", "total_lines": 150},
  "saved": true,
  "tokens_used": {"input": 400, "output": 250},
  "model": "gpt-4o"
}
```

---

## 4. `worker_explain_code`

**Objectif :** Obtenir une explication détaillée d'un bloc de code sans consommer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Explique la logique d'un fichier via le Worker et renvoie une explication structurée, plutôt que le code brut."*
>
> *"Déclencheurs : 'explique', 'comment ça marche', 'c'est quoi'."*
>
> *"Multi-fichiers (ex : 'explique comment marche le UI') : appeler une fois par fichier, puis synthétiser les réponses."*
>
> *"Paramètre `detail_level` : `'summary'`, `'detailed'` (défaut) ou `'line-by-line'`."*

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à expliquer |
| `focus` | string | ❌ | Classe, fonction ou section spécifique à cibler |
| `detail_level` | string | ❌ | `"summary"`, `"detailed"`, ou `"line-by-line"` (défaut: `"detailed"`) |

### Retour

`status`, `explanation`, `file_info`, `tokens_used`, `model`

> **Note :** Les résultats sont mis en cache (TTL configurable).

---

## 5. `worker_generate_tests`

**Objectif :** Générer des tests unitaires pour du code existant.

### Description (vue par le Cerveau)

> *"Génère une suite de tests pour un fichier via le Worker, avec setup, teardown et cas limites. Connaît les frameworks courants (pytest, Jest, etc.)."*
>
> *"Multi-fichiers (ex : 'génère des tests pour tout le module') : appeler une fois par fichier source."*
>
> *"Paramètres : `test_framework` (défaut `'pytest'`), `focus_functions`, `coverage_level`."*

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier source à tester |
| `test_framework` | string | ❌ | Framework de test (défaut: `"pytest"`) |
| `focus_functions` | string | ❌ | Fonctions spécifiques à tester (séparées par des virgules) |
| `coverage_level` | string | ❌ | `"basic"`, `"thorough"`, `"exhaustive"` (défaut: `"thorough"`) |

### Retour

`status`, `test_code`, `source_file`, `test_framework`, `tokens_used`, `model`

---

## 6. `worker_review_code`

**Objectif :** Effectuer une revue de code structurée et catégorisée.

### Description (vue par le Cerveau)

> *"Fait une revue de code d'un fichier via le Worker et renvoie un rapport JSON structuré (bugs, sécurité, performance, style)."*
>
> *"Déclencheurs : 'vérifie', 'revue', 'bugs', 'audit'."*
>
> *"Multi-fichiers (ex : 'audit du projet') : appeler une fois par fichier, puis compiler les rapports JSON."*
>
> *"Paramètre `focus` optionnel : `'security'`, `'performance'`, `'bugs'`, etc."*

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à réviser |
| `focus` | string | ❌ | Aspect spécifique à évaluer (`"security"`, `"performance"`, etc.) |

### Retour

```json
{
  "status": "success",
  "review": {
    "summary": "...",
    "bugs": [{"line": 42, "severity": "critical", "message": "..."}],
    "security": [...],
    "performance": [...],
    "maintainability": [...],
    "style": [...]
  },
  "file_info": {...},
  "tokens_used": {...},
  "model": "..."
}
```

> **Note :** Les résultats sont mis en cache (TTL configurable). Un deuxième appel sur le même fichier non modifié est instantané.

---

## 7. `worker_document_code`

**Objectif :** Générer automatiquement les docstrings et commentaires manquants.

### Description (vue par le Cerveau)

> *"Ajoute des docstrings à un fichier via le Worker, sans modifier la logique du code. Connaît les conventions (Google, Numpy, JSDoc)."*
>
> *"Déclencheurs : 'documente', 'ajoute des docstrings', 'commente le code'."*
>
> *"Multi-fichiers (ex : 'documente tout le projet') : appeler une fois par fichier."*
>
> *"Paramètre `style` optionnel : `'google'`, `'numpy'`, `'jsdoc'`, etc."*

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à documenter |
| `style` | string | ❌ | Style de docstring (`"google"`, `"numpy"`, `"jsdoc"`) |

### Retour

`status`, `documented_code`, `file_info`, `tokens_used`, `model`

> **Note :** Les résultats sont mis en cache (TTL configurable).

---

## 8. `worker_get_metrics`

**Objectif :** Obtenir un rapport des métriques de la session en cours.

### Description (vue par le Cerveau)

> *"Obtient les métriques pour la session en cours, incluant l'utilisation des tokens par outil et par modèle, les latences, le nombre de retries, les bascules fallback et les statistiques du cache."*
>
> Appelle cet outil en fin de session ou à tout moment pour mesurer l'activité du Worker.

### Paramètres
*(Aucun paramètre requis)*

### Retour

Le serveur rapporte des **faits bruts** (tokens par modèle, retries, fallbacks) sans calculer de prix. La conversion en coût est laissée à la couche appelante (Cerveau ou dashboard externe), car les tarifs varient selon les modèles utilisés.

```json
{
  "status": "success",
  "metrics": {
    "enabled": true,
    "total_calls": 5,
    "successful_calls": 5,
    "failed_calls": 0,
    "total_tokens_input": 4500,
    "total_tokens_output": 1200,
    "total_retries": 1,
    "total_fallbacks": 0,
    "avg_latency_ms": 1250.5,
    "tools": {
      "worker_analyze_file": {
        "calls": 3,
        "success_rate": 100.0,
        "tokens_input": 3000,
        "tokens_output": 800,
        "retries": 1,
        "fallbacks": 0
      }
    },
    "by_model": {
      "gpt-4o": {
        "calls": 5,
        "tokens_input": 4500,
        "tokens_output": 1200,
        "total_tokens": 5700
      }
    }
  },
  "cache": {
    "hits": 2,
    "misses": 5,
    "size": 5
  }
}
```

---

## Matrice de décision pour le Cerveau

| Situation | Action du Cerveau |
|---|---|
| Générer > 30 lignes de code | → `worker_generate_code` |
| Lire un fichier > 50 lignes | → `worker_analyze_file` |
| Modifier > 20 lignes de code | → `worker_refactor_code` |
| Comprendre un fichier inconnu | → `worker_explain_code` |
| Écrire des tests | → `worker_generate_tests` |
| Évaluer la qualité / sécurité du code | → `worker_review_code` |
| Ajouter des docstrings | → `worker_document_code` |
| Mesurer l'activité de la session | → `worker_get_metrics` |
| Corriger 1-5 lignes | → **Agir seul** |
| Décision d'architecture | → **Agir seul** |
| Planification du travail | → **Agir seul** |
