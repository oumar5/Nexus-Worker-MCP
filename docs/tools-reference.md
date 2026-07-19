# Référence des Outils MCP — Nexus-Worker-MCP

Ce document détaille chaque outil (Tool) exposé par le serveur MCP au modèle principal (le Cerveau). Les **descriptions** sont le mécanisme central qui indique au Cerveau **quand** et **comment** déléguer au Worker.

> Les descriptions ci-dessous sont volontairement longues et directives. C'est intentionnel : elles agissent comme des **instructions système** pour le Cerveau. Ne les raccourcissez pas.

---

## 1. `worker_generate_code`

**Objectif :** Générer du code neuf — fonctions, classes, fichiers entiers.

### Description (vue par le Cerveau)

> *"Utilise cet outil OBLIGATOIREMENT lorsque tu dois générer du code dépassant 30 lignes. Ne génère JAMAIS de longs blocs de code toi-même — délègue à cet outil. Fournis une instruction technique détaillée incluant : le langage, le framework, les conventions de nommage, et le comportement attendu."*
>
> **Exemples d'utilisation :** Créer une route API, un composant UI, un script de migration, un fichier de config.
>
> **NE PAS utiliser pour :** Des corrections mineures (< 10 lignes), ou de la logique qui dépend de la connaissance de plusieurs fichiers simultanément.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `instruction` | string | ✅ | Consigne technique détaillée pour la génération |
| `target_path` | string | ❌ | Chemin du fichier cible (pour le contexte) |
| `language` | string | ❌ | Langage de programmation (défaut: inféré) |
| `context` | string | ❌ | Contexte additionnel (imports existants, conventions, types) |

### Retour

`status`, `code`, `language`, `tokens_used`, `model`

---

## 2. `worker_analyze_file`

**Objectif :** Lire et analyser un fichier volumineux sans encombrer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Utilise cet outil lorsque tu as besoin de comprendre le contenu d'un fichier que tu n'as pas encore lu, ou lorsque tu dois extraire des informations spécifiques d'un fichier volumineux."*
>
> **Exemples d'utilisation :** "Quelles routes sont définies ?", "Y a-t-il des failles de sécurité ?", "Résume la logique métier".
>
> **NE PAS utiliser pour :** Des fichiers déjà dans ton contexte, ou des fichiers très courts (< 50 lignes).

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

> *"Utilise cet outil pour appliquer des modifications substantielles sur du code existant : renommage massif, restructuration, ajout de gestion d'erreurs, migration de patterns, ou conversion entre frameworks."*
>
> **Exemples d'utilisation :** Convertir des callbacks en async/await, ajouter du try/catch partout, migrer des imports.
>
> **NE PAS utiliser pour :** Changer une seule ligne, ou du refactoring inter-fichiers nécessitant une vision transversale.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à refactorer |
| `instruction` | string | ✅ | Instructions de refactoring détaillées |
| `target_lines` | string | ❌ | Plage de lignes ciblées (ex: "42-98") |
| `context` | string | ❌ | Contexte additionnel (patterns, types) |

### Retour

`status`, `refactored_code`, `file_info`, `tokens_used`, `model`

---

## 4. `worker_explain_code`

**Objectif :** Obtenir une explication détaillée d'un bloc de code sans consommer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Utilise cet outil lorsque tu as besoin de comprendre la logique d'un fichier ou d'un bloc de code avant de prendre une décision architecturale."*
>
> **Exemples d'utilisation :** Comprendre un algorithme complexe, documenter une fonction legacy, identifier les effets de bord avant un refactoring.

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

> *"Utilise cet outil pour générer des tests unitaires ou d'intégration pour un fichier ou une fonction existante. La génération de tests est une tâche lourde en tokens de sortie — délègue-la systématiquement."*
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

> *"Utilise cet outil pour effectuer une revue de code structurée sur un fichier. Le Worker analyse le code et retourne une revue JSON catégorisée : bugs, security, performance, maintainability, style."*
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

> *"Utilise cet outil pour générer automatiquement les docstrings et commentaires manquants dans un fichier. Le Worker retourne le fichier complet avec les docstrings insérées, sans modifier le code existant."*
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

**Objectif :** Obtenir un rapport FinOps de la session en cours.

### Description (vue par le Cerveau)

> *"Retourne un rapport FinOps de la session en cours : tokens délégués, coût réel du Worker, coût estimé si tu avais tout fait toi-même, économies réalisées et statistiques du cache."*
>
> Appelle cet outil en fin de session ou à tout moment pour mesurer l'impact financier de l'architecture Nexus.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `worker_input_price` | float | ❌ | Prix input Worker / 1M tokens (défaut: 0.15 — GPT-4o-mini) |
| `worker_output_price` | float | ❌ | Prix output Worker / 1M tokens (défaut: 0.60) |
| `brain_input_price` | float | ❌ | Prix input Cerveau / 1M tokens (défaut: 5.00 — GPT-5.6 Sol) |
| `brain_output_price` | float | ❌ | Prix output Cerveau / 1M tokens (défaut: 30.00) |

### Retour (exemple)

```json
{
  "status": "success",
  "finops": {
    "total_tokens_delegated": 45230,
    "total_calls": 8,
    "cost_worker_usd": 0.0043,
    "cost_if_brain_usd": 0.0872,
    "savings_usd": 0.0829,
    "savings_percent": 95.1,
    "reduction_factor": 20.0,
    "message": "En déléguant 8 appel(s) au Worker, vous avez économisé ~0.0829 $ (95% d'économie, facteur 20x)."
  },
  "cache": {
    "hits": 3,
    "misses": 5,
    "hit_rate_percent": 37.5
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
