# Gestion d'Erreurs et Résilience — Nexus-Worker-MCP

## Philosophie

Le serveur MCP est un **point unique de défaillance** entre le Cerveau et le Worker. S'il échoue silencieusement, le Cerveau ne peut pas travailler. Chaque erreur doit être :
1. **Catchée** — jamais de crash non géré
2. **Loggée** — pour le diagnostic
3. **Communiquée clairement** — le Cerveau reçoit un message exploitable, pas une stack trace

---

## Catégories d'erreurs

### 1. Erreurs de connexion API

| Erreur | Cause | Stratégie |
|---|---|---|
| `ConnectionError` | API unreachable | Retry avec backoff exponentiel |
| `TimeoutError` | Réponse trop lente | Retry 1x, puis message d'erreur au Cerveau |
| `AuthenticationError` (401/403) | Clé API invalide/expirée | **Pas de retry** — erreur fatale, notifier immédiatement |
| `RateLimitError` (429) | Quota dépassé | Retry avec délai progressif (1s, 5s, 15s) |

### 2. Erreurs de contenu

| Erreur | Cause | Stratégie |
|---|---|---|
| Réponse vide | Modèle n'a rien généré | Retry avec température légèrement plus haute |
| Réponse tronquée | `max_tokens` trop bas | Retry avec `max_tokens` augmenté |
| Réponse incohérente | Modèle a halluciné | Retourner au Cerveau avec un warning |
| Format invalide | JSON attendu mais texte reçu | Parser best-effort, puis retourner au Cerveau |

### 3. Erreurs de fichiers

| Erreur | Cause | Stratégie |
|---|---|---|
| `FileNotFoundError` | Chemin invalide | Message clair au Cerveau : "Fichier introuvable" |
| `PermissionError` | Fichier hors zone autorisée | Message : "Accès refusé — hors ALLOWED_PATHS" |
| Fichier trop volumineux | > 100K lignes | Découper et traiter par chunks |
| Encodage inconnu | Fichier binaire ou encodage exotique | Tenter UTF-8, puis Latin-1, puis erreur |

---

## Mécanisme de Retry

Le système utilise un **backoff exponentiel** avec les paramètres suivants :

| Paramètre | Valeur par défaut | Variable d'environnement |
|---|---|---|
| Nombre maximum de tentatives | 3 | `WORKER_MAX_RETRIES` |
| Délai initial | 1 seconde | — |
| Délai maximum | 30 secondes | — |
| Multiplicateur | x2 après chaque échec | — |

**Erreurs retryables :** `ConnectionError`, `TimeoutError`, `RateLimitError`.

**Erreurs non-retryables :** `AuthenticationError` (clé invalide), erreurs 400 (requête malformée).

### Comportement

- **Tentative 1** échoue → attente de 1s → retry
- **Tentative 2** échoue → attente de 2s → retry
- **Tentative 3** échoue → attente de 4s → retry
- **Échec final** → le MCP retourne un message d'erreur structuré au Cerveau

### Traçabilité des retries

Quand `with_retry` obtient une réponse réussie après au moins un échec, elle marque la `WorkerResponse` avec le champ `retry_count` (nombre de tentatives supplémentaires avant succès). Cette information est remontée jusqu'aux métriques de session (`total_retries` global + `retries` par outil), ce qui permet d'observer les zones instables sans devoir lire les logs.

---

## Stratégie de Fallback

Quand le Worker principal échoue définitivement, deux options sont disponibles :

### Option A : Message d'erreur informatif (par défaut)

Le MCP renvoie au Cerveau un message structuré contenant :
- Le type d'erreur (`worker_unavailable`, `timeout`, etc.)
- Un message humainement lisible
- Une suggestion d'action ("tente de réaliser la tâche toi-même" ou "demande à l'utilisateur de vérifier la configuration")
- L'outil qui a échoué et l'instruction originale

Le Cerveau peut alors décider de :
- Réaliser la tâche lui-même (plus cher mais fonctionnel)
- Demander à l'utilisateur de vérifier la connexion

### Option B : Provider de secours (optionnel)

Si les variables `WORKER_FALLBACK_*` sont configurées dans le `.env`, le serveur enveloppe le provider principal dans un `CompositeProvider` qui bascule **automatiquement et de façon transparente** vers le provider alternatif dès que le principal lève une `WorkerError`. Le reste du code n'a pas conscience de cette bascule — il continue de parler à un `WorkerProvider` unique.

**Exemple typique :** Provider principal = API cloud, provider de secours = modèle local Ollama. Si le cloud est indisponible, le travail continue localement (plus lent mais sans interruption).

### Traçabilité des bascules

Quand le composite bascule sur le fallback, il marque la `WorkerResponse` avec `used_fallback=True`. Cette information est remontée aux métriques (`total_fallbacks` global + `fallbacks` par outil), ce qui permet de repérer les périodes de dégradation du provider principal.

Voir [provider-adapters.md — §5 CompositeProvider](provider-adapters.md#5-compositeprovider--bascule-automatique-primaire--fallback) pour l'implémentation.

---

## Protection contre les boucles infinies

Quand le Cerveau appelle un outil, reçoit un résultat insatisfaisant, et rappelle l'outil pour corriger, il y a un risque de **boucle infinie** de correction.

### Mécanisme de protection

Le MCP maintient un **compteur d'appels par outil** sur une fenêtre glissante :

| Paramètre | Valeur par défaut |
|---|---|
| Nombre maximum d'appels par outil | 5 appels |
| Fenêtre de temps | 5 minutes (300 secondes) |

Si un même outil est appelé plus de 5 fois en 5 minutes, le MCP retourne au Cerveau un message indiquant que l'outil est temporairement désactivé, avec la suggestion de résoudre le problème différemment ou de demander l'intervention de l'utilisateur.

---

## Gestion des fichiers volumineux

Pour les fichiers qui dépassent la fenêtre de contexte du Worker, le MCP utilise un **système de chunking intelligent** :

1. Le fichier est découpé en morceaux de **500 lignes maximum** par défaut
2. Le découpage se fait aux **frontières naturelles** du code (définitions de fonctions, de classes, ou séparateurs commentés) pour préserver le contexte sémantique
3. Chaque chunk est traité séparément par le Worker
4. Les résultats sont agrégés et retournés au Cerveau

Si le fichier dépasse 100 000 lignes, le MCP retourne une erreur et suggère au Cerveau de cibler une plage de lignes spécifique via le paramètre `focus_lines`.

---

## Logging structuré

Chaque appel d'outil est loggé avec les informations suivantes :

| Champ | Description |
|---|---|
| `timestamp` | Date et heure de l'appel |
| `level` | Niveau de log (INFO, WARNING, ERROR) |
| `event` | Type d'événement (`tool_call`, `tool_call_failed`, `retry`, `fallback`) |
| `tool` | Nom de l'outil appelé |
| `provider` | Fournisseur utilisé |
| `model` | Modèle worker |
| `tokens_input` | Tokens d'entrée consommés |
| `tokens_output` | Tokens de sortie consommés |
| `latency_ms` | Temps de réponse en millisecondes |
| `status` | Résultat (`success`, `error`, `retried`, `fallback_used`) |
| `attempt` | Numéro de tentative (1, 2, 3...) |
| `error` | Message d'erreur (si applicable) |

Le niveau de log et le fichier de destination sont configurables via `LOG_LEVEL` et `LOG_FILE` dans le `.env`.
