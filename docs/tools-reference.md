# Référence des Outils MCP — Nexus-Worker-MCP

Ce document détaille chaque outil (Tool) exposé par le serveur MCP au modèle principal (le Cerveau). Les **descriptions** sont le mécanisme central qui indique au Cerveau **quand** et **comment** déléguer au Worker.

> Les descriptions ci-dessous sont volontairement longues et directives. C'est intentionnel : elles agissent comme des **instructions système** pour le Cerveau. Ne les raccourcissez pas.

---

## 1. `worker_generate_code`

**Objectif :** Générer du code neuf — fonctions, classes, fichiers entiers.

### Description (vue par le Cerveau)

> *"Utilise cet outil OBLIGATOIREMENT lorsque tu dois générer du code dépassant 30 lignes. Ne génère JAMAIS de longs blocs de code toi-même — délègue à cet outil. Fournis une instruction technique détaillée incluant : le langage, le framework, les conventions de nommage, et le comportement attendu. L'outil retournera le code généré prêt à l'emploi."*
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

L'outil retourne un objet contenant : le statut (`success` ou `error`), le code généré, le langage détecté, les tokens consommés (input et output), et le modèle utilisé.

---

## 2. `worker_analyze_file`

**Objectif :** Lire et analyser un fichier volumineux sans encombrer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Utilise cet outil lorsque tu as besoin de comprendre le contenu d'un fichier que tu n'as pas encore lu, ou lorsque tu dois extraire des informations spécifiques d'un fichier volumineux. L'outil lit le fichier et utilise un modèle secondaire pour en extraire les informations que tu demandes."*
>
> **Exemples d'utilisation :** "Quelles routes sont définies ?", "Y a-t-il des failles de sécurité ?", "Résume la logique métier", "Liste les dépendances importées".
>
> **NE PAS utiliser pour :** Des fichiers déjà dans ton contexte, ou des fichiers très courts (< 50 lignes).

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin absolu ou relatif du fichier à analyser |
| `question` | string | ✅ | Question ou consigne d'analyse |
| `focus_lines` | string | ❌ | Plage de lignes à cibler (ex: "100-200") |

### Retour

L'outil retourne : le statut, l'analyse condensée, les informations sur le fichier (chemin, nombre total de lignes), les tokens consommés, et le modèle utilisé.

---

## 3. `worker_refactor_code`

**Objectif :** Appliquer des modifications lourdes sur du code existant.

### Description (vue par le Cerveau)

> *"Utilise cet outil pour appliquer des modifications substantielles sur du code existant : renommage massif, restructuration, ajout de gestion d'erreurs, migration de patterns, ou conversion entre frameworks."*
>
> **Exemples d'utilisation :** Convertir des callbacks en async/await, ajouter du try/catch partout, renommer des variables, migrer des imports CommonJS vers ES Modules, appliquer un design pattern.
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

L'outil retourne : le statut, le code refactoré, un résumé des changements effectués, les tokens consommés, et le modèle utilisé.

---

## 4. `worker_explain_code`

**Objectif :** Obtenir une explication détaillée d'un bloc de code sans consommer le contexte du Cerveau.

### Description (vue par le Cerveau)

> *"Utilise cet outil lorsque tu as besoin de comprendre la logique d'un fichier ou d'un bloc de code avant de prendre une décision architecturale. Plutôt que de lire et analyser un gros fichier toi-même (coûteux en tokens), délègue l'explication à cet outil."*
>
> **Exemples d'utilisation :** Comprendre un algorithme complexe, documenter une fonction legacy, identifier les effets de bord avant un refactoring.

### Paramètres

| Paramètre | Type | Requis | Description |
|---|---|---|---|
| `file_path` | string | ✅ | Chemin du fichier à expliquer |
| `focus` | string | ❌ | Classe, fonction ou section spécifique à cibler |
| `detail_level` | string | ❌ | `"summary"`, `"detailed"`, ou `"line-by-line"` (défaut: `"detailed"`) |

### Retour

L'outil retourne une explication structurée contenant : l'objectif du code, le flux d'exécution, les dépendances identifiées, les points d'attention, les tokens consommés, et le modèle utilisé.

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

L'outil retourne : le statut, le code de test complet, le nombre de tests générés, les domaines de couverture (happy path, edge cases, error handling), les tokens consommés, et le modèle utilisé.

---

## Matrice de décision pour le Cerveau

Ce tableau résume quand le Cerveau doit utiliser chaque outil vs agir seul :

| Situation | Action du Cerveau |
|---|---|
| Générer > 30 lignes de code | → `worker_generate_code` |
| Lire un fichier > 50 lignes | → `worker_analyze_file` |
| Modifier > 20 lignes de code | → `worker_refactor_code` |
| Comprendre un fichier inconnu | → `worker_explain_code` |
| Écrire des tests | → `worker_generate_tests` |
| Corriger 1-5 lignes | → **Agir seul** |
| Décision d'architecture | → **Agir seul** |
| Planification du travail | → **Agir seul** |
| Réponse à une question simple | → **Agir seul** |
