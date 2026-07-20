# Référence des Outils MCP — Nexus-Worker-MCP

Ce document détaille chaque outil (Tool) exposé par le serveur MCP au modèle principal (le Cerveau). Les **descriptions** sont le mécanisme central qui indique au Cerveau **quand** et **comment** déléguer au Worker.

> Les descriptions ci-dessous sont volontairement longues et directives. C'est intentionnel : elles agissent comme des **instructions système** pour le Cerveau. Ne les raccourcissez pas.

---

## 1. `worker_generate_code`

**Objectif :** Générer du code neuf — fonctions, classes, fichiers entiers.

### Description (vue par le Cerveau)

> *"Outil SPÉCIALISÉ de génération de code. Cet outil est PLUS SPÉCIFIQUE que tes outils natifs d'écriture pour générer du code (> 30 lignes). Il produit du code structuré et peut l'écrire directement sur le disque."*
>
> *"POURQUOI cet outil est le bon choix : Tes Output tokens coûtent 125x plus cher que ceux du Worker. Générer du code toi-même avec write_to_file n'est PAS plus spécifique, c'est 125x plus cher."*
>
> **Exemples d'utilisation :** Créer une route API, un composant UI, un script de migration, un fichier de config. Active `auto_save=True` pour écraser le fichier.
>
> **NE PAS utiliser pour :** Des corrections mineures (< 10 lignes).

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

> *"Outil SPÉCIALISÉ d'analyse de code. PLUS SPÉCIFIQUE que view_file pour comprendre un fichier source. view_file retourne du texte brut que TU dois analyser (coûteux). Cet outil retourne directement une analyse structurée et ciblée."*
>
> *"POURQUOI cet outil est le bon choix : Cet outil = tokens du Worker (100x moins cher). CAS MULTI-FICHIERS (ex: 'analyse le UI') : Tu pourrais être tenté de lire tous les fichiers toi-même pour avoir une 'vue globale'. C'EST UNE ERREUR. Appelle cet outil UNE FOIS PAR FICHIER."*
>
> **Exemples d'utilisation :** "Quelles routes sont définies ?", "Résume la logique métier", "Fais un rapport sur le projet".
>
> **Exception :** 1 seul fichier < 50 lignes.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin absolu ou relatif du fichier à analyser |
| `question` | string | ✅ | Question ou consigne d'analyse |
| `focus_lines` | string | ❌ | Plage de lignes à cibler (ex: "100-200") |

### Retour

`status`, `analysis`, `file_info`, `tokens_used`, `model`

---

## 3. `worker_refactor_code`

**Objectif :** Appliquer des modifications lourdes sur du code existant.

### Description (vue par le Cerveau)

> *"Outil SPÉCIALISÉ de refactoring. PLUS SPÉCIFIQUE que tes outils natifs d'édition pour du refactoring massif. Il comprend le contexte du fichier et applique les changements en une seule passe."*
>
> *"POURQUOI cet outil est le bon choix : Réécrire un fichier toi-même avec replace_file_content coûte 125x plus cher en Output tokens. CAS MULTI-FICHIERS : Appelle cet outil UNE FOIS PAR FICHIER."*
>
> **Exemples d'utilisation :** Convertir des callbacks en async/await, ajouter du try/catch partout, migrer des imports. Active `auto_save=True`.
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

> *"Outil SPÉCIALISÉ d'explication de code. PLUS SPÉCIFIQUE que view_file pour comprendre la logique d'un fichier. view_file lit du texte brut. Cet outil lit, comprend et retourne une explication structurée."*
>
> *"POURQUOI cet outil est le bon choix : Lire un fichier avec view_file te coûte 100x en Input, PUIS générer l'explication te coûte 125x en Output. CAS MULTI-FICHIERS : Appelle cet outil UNE FOIS PAR FICHIER, puis synthétise."*
>
> **Exemples d'utilisation :** Comprendre un algorithme complexe, documenter une fonction legacy, identifier les effets de bord. Quand l'utilisateur dit 'explique', 'comment ça marche', 'c'est quoi' : UTILISE CET OUTIL.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à expliquer |
| `focus` | string | ❌ | Classe, fonction ou section spécifique à cibler |
| `detail_level` | string | ❌ | `"summary"`, `"detailed"`, ou `"line-by-line"` (défaut: `"detailed"`) |

### Retour

`status`, `explanation`, `file_info`, `tokens_used`, `model`

---

## 5. `worker_generate_tests`

**Objectif :** Générer des tests unitaires pour du code existant.

### Description (vue par le Cerveau)

> *"Outil SPÉCIALISÉ de génération de tests. PLUS SPÉCIFIQUE que tes outils natifs pour créer des tests. Il connaît les frameworks et génère des suites complètes."*
>
> *"POURQUOI cet outil est le bon choix : Tes Output tokens coûtent 125x plus cher. Écrire des tests toi-même n'est PAS plus spécifique. CAS MULTI-FICHIERS : Appelle cet outil UNE FOIS PAR FICHIER source."*
>
> **Exemples d'utilisation :** Générer une suite pytest, des tests Jest, des tests d'intégration pour une API REST.

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

## 6. `worker_review_code` ✨ Nouveau

**Objectif :** Effectuer une revue de code structurée et catégorisée.

### Description (vue par le Cerveau)

> *"Outil SPÉCIALISÉ de revue de code. PLUS SPÉCIFIQUE que view_file pour évaluer la qualité d'un fichier. Retourne un rapport JSON structuré catégorisé (bugs, security, performance, style)."*
>
> *"POURQUOI cet outil est le bon choix : Lire un fichier pour le juger te coûte 100x en Input + 125x en Output. Le Worker produit un rapport pour presque rien. CAS MULTI-FICHIERS : Appelle cet outil UNE FOIS PAR FICHIER, puis compile."*
>
> **Exemples d'utilisation :** Vérifier la sécurité d'un endpoint API, détecter des fuites mémoire, évaluer la qualité du code avant une PR.
>
> **Paramètre `focus` optionnel :** `"security"`, `"performance"`, `"bugs"`, etc.

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

> **Note :** Les résultats sont mis en cache (TTL 1h). Un deuxième appel sur le même fichier non modifié est instantané et gratuit.

---

## 7. `worker_document_code` ✨ Nouveau

**Objectif :** Générer automatiquement les docstrings et commentaires manquants.

### Description (vue par le Cerveau)

> *"Outil SPÉCIALISÉ de documentation de code. PLUS SPÉCIFIQUE que tes outils natifs pour ajouter des docstrings. Connaît les conventions (Google, Numpy, JSDoc) et insère les docstrings sans modifier le code existant."*
>
> *"POURQUOI cet outil est le bon choix : Documenter un fichier = le lire (100x cher) + le réécrire (125x cher). Le Worker fait les deux pour presque rien. CAS MULTI-FICHIERS : Appelle cet outil UNE FOIS PAR FICHIER."*
>
> **Exemples d'utilisation :** Documenter un fichier legacy, préparer une PR avec de la documentation, générer des docstrings Google Style pour Python.
>
> **Paramètre `style` optionnel :** `"google"`, `"numpy"`, `"jsdoc"`, etc.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à documenter |
| `style` | string | ❌ | Style de docstring (`"google"`, `"numpy"`, `"jsdoc"`) |

### Retour

`status`, `documented_code`, `file_info`, `tokens_used`, `model`

> **Note :** Les résultats sont mis en cache (TTL 1h).

---

## 8. `worker_get_metrics` ✨ Nouveau

**Objectif :** Obtenir un rapport des métriques de la session en cours.

### Description (vue par le Cerveau)

> *"Obtient les métriques pour la session en cours, incluant l'utilisation des tokens, les latences, et les statistiques du cache."*
>
> Appelle cet outil en fin de session ou à tout moment pour mesurer l'activité du Worker.

### worker_get_metrics

Obtient les métriques pour la session en cours, incluant l'utilisation des tokens, les latences, et les statistiques du cache.

### Paramètres
*(Aucun paramètre requis)*

### Retour
```json
{
  "status": "success",
  "metrics": {
    "total_calls": 5,
    "successful_calls": 5,
    "failed_calls": 0,
    "total_tokens_input": 4500,
    "total_tokens_output": 1200,
    "avg_latency_ms": 1250.5
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
| Mesurer les économies de la session | → `worker_get_metrics` |
| Corriger 1-5 lignes | → **Agir seul** |
| Décision d'architecture | → **Agir seul** |
| Planification du travail | → **Agir seul** |
