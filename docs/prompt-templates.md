# Templates de Prompts — Nexus-Worker-MCP

## Principe

Chaque outil MCP utilise un **prompt système** spécialisé pour cadrer le comportement du Worker. Ces templates sont des fichiers Markdown stockés dans `src/nexus_worker/prompts/templates/` et chargés dynamiquement par le `PromptEngine`.

Le prompt système est **invisible pour le Cerveau** — c'est le MCP qui l'injecte automatiquement. Le Cerveau ne fournit que l'instruction utilisateur.

---

## Moteur de prompts (PromptEngine)

Le `PromptEngine` est un service qui :

1. **Charge** les templates depuis le répertoire `templates/` au démarrage (avec mise en cache)
2. **Sélectionne** le bon template en fonction du nom de l'outil appelé
3. **Injecte** les variables dynamiques (contexte, langage, niveau de détail) dans le template
4. **Retourne** le prompt système final prêt à envoyer au Worker

Le répertoire de templates peut être surchargé via la variable d'environnement `PROMPT_TEMPLATES_DIR`.

---

## Template 1 : Génération de code (`generate.md`)

### Rôle assigné au Worker
Le Worker est positionné comme un générateur de code expert qui produit du code propre, fonctionnel et prêt à l'emploi.

### Règles imposées

| # | Règle |
|---|---|
| 1 | Retourner UNIQUEMENT le code — pas d'explication, pas de mise en forme Markdown |
| 2 | Le code doit être syntaxiquement correct et exécutable |
| 3 | Inclure les imports nécessaires en haut du fichier |
| 4 | Respecter les conventions du langage (PEP 8 pour Python, ESLint pour JS/TS, etc.) |
| 5 | Gérer les erreurs de manière appropriée |
| 6 | Ne JAMAIS inclure de clés API, mots de passe ou secrets dans le code |

### Variables injectées

| Variable | Source | Description |
|---|---|---|
| `context` | Paramètre `context` de l'outil | Informations additionnelles fournies par le Cerveau |
| `language` | Paramètre `language` de l'outil | Langage cible pour la génération |

---

## Template 2 : Analyse de fichier (`analyze.md`)

### Rôle assigné au Worker
Le Worker est positionné comme un analyste de code expert qui lit du code source et extrait des informations précises.

### Règles imposées

| # | Règle |
|---|---|
| 1 | Répondre de manière concise et structurée |
| 2 | Citer les numéros de lignes dans les références au code |
| 3 | Séparer les faits (ce que le code fait) des opinions (améliorations possibles) |
| 4 | Signaler les problèmes de sécurité en priorité avec le tag **[SÉCURITÉ]** |
| 5 | Signaler les bugs avec le tag **[BUG]** |
| 6 | Se concentrer sur les sections pertinentes si le fichier est trop long |

### Format de réponse attendu

Le Worker doit structurer sa réponse en deux sections :
- **Réponse directe** — La réponse à la question posée
- **Points d'attention** — Liste optionnelle des problèmes détectés, tagués par catégorie (SÉCURITÉ, BUG, PERFORMANCE)

---

## Template 3 : Refactoring (`refactor.md`)

### Rôle assigné au Worker
Le Worker est positionné comme un expert en refactoring qui applique des modifications précises en préservant le comportement fonctionnel.

### Règles imposées

| # | Règle |
|---|---|
| 1 | Retourner UNIQUEMENT le code modifié — pas d'explication |
| 2 | Préserver TOUS les commentaires existants sauf s'ils deviennent obsolètes |
| 3 | Ne PAS modifier la logique métier sauf si explicitement demandé |
| 4 | Conserver les imports existants, ajouter les nouveaux si nécessaire |
| 5 | S'assurer que les tests existants ne seront pas cassés |
| 6 | Respecter le style de code existant (indentation, quotes, conventions) |

### Variables injectées

| Variable | Source | Description |
|---|---|---|
| `context` | Paramètre `context` de l'outil | Patterns à suivre, types à respecter |

---

## Template 4 : Explication de code (`explain.md`)

### Rôle assigné au Worker
Le Worker est positionné comme un documentaliste technique expert qui explique du code de manière factuelle et structurée.

### Format de réponse imposé

Le Worker doit obligatoirement structurer sa réponse en 5 sections :

| Section | Contenu |
|---|---|
| **Objectif** | Description en 1-2 phrases de ce que fait le code |
| **Flux d'exécution** | Liste numérotée des étapes du code |
| **Fonctions/Classes principales** | Nom + description en 1 ligne pour chaque élément public |
| **Dépendances** | Liste des imports et services externes |
| **Points d'attention** | Problèmes potentiels, dette technique, TODO en suspens |

### Variables injectées

| Variable | Source | Description |
|---|---|---|
| `detail_level` | Paramètre `detail_level` de l'outil | Niveau de détail : `summary`, `detailed`, ou `line-by-line` |

---

## Template 5 : Génération de tests (`test.md`)

### Rôle assigné au Worker
Le Worker est positionné comme un ingénieur QA expert qui génère des suites de tests complètes et robustes.

### Règles imposées

| # | Règle |
|---|---|
| 1 | Retourner UNIQUEMENT le code de test — pas d'explication |
| 2 | Utiliser le framework de test spécifié |
| 3 | Organiser les tests en classes ou groupes logiques |
| 4 | Couvrir : cas nominaux, cas limites et erreurs |
| 5 | Utiliser des noms de tests descriptifs |
| 6 | Mocker les dépendances externes (APIs, BDD, fichiers) |
| 7 | Une seule assertion par test (ou un groupe cohérent) |
| 8 | Inclure les fixtures et setup nécessaires |

### Niveaux de couverture

| Niveau | Description |
|---|---|
| `basic` | Cas nominaux uniquement (happy path) |
| `thorough` | Cas nominaux + cas limites |
| `exhaustive` | Cas nominaux + cas limites + erreurs + edge cases obscurs |

### Variables injectées

| Variable | Source | Description |
|---|---|---|
| `test_framework` | Paramètre de l'outil | Framework cible (pytest, jest, etc.) |
| `coverage_level` | Paramètre de l'outil | Niveau de couverture souhaité |
| `fichier_source` | Déduit du `file_path` | Nom du fichier source pour le header des tests |

---

## Personnalisation des templates

Les templates peuvent être adaptés à votre projet de plusieurs façons :

1. **Ajouter des conventions d'équipe** — Modifier les règles dans les templates existants pour inclure vos standards de code
2. **Modifier le format de sortie** — Forcer du JSON structuré au lieu du texte libre si votre workflow le nécessite
3. **Créer de nouveaux templates** — Pour chaque nouvel outil MCP, créer un fichier `.md` correspondant dans le répertoire templates
4. **Surcharger le répertoire** — Pointer vers un répertoire personnalisé via `PROMPT_TEMPLATES_DIR` pour utiliser des templates différents selon le projet
