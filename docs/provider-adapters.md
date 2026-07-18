# Adaptateurs Fournisseurs — Nexus-Worker-MCP

## Principe d'agnosticisme

Le système repose sur une **interface commune** (`WorkerProvider`) que chaque adaptateur implémente. Le code des outils MCP ne connaît **jamais** le fournisseur utilisé — il passe toujours par cette interface abstraite.

```
                    ┌──────────────────────┐
                    │   WorkerProvider     │  ← Interface commune
                    │                      │
                    │   + complete()       │
                    │   + health_check()   │
                    │   + get_info()       │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
     │ OpenAIAdapter │ │AnthropicAdpt │ │ OllamaAdaptr │
     │               │ │              │ │              │
     │ OpenAI        │ │ Claude API   │ │ Local models │
     │ Azure OpenAI  │ │              │ │ vLLM         │
     │ Together      │ │              │ │ LM Studio    │
     │ Groq          │ │              │ │              │
     └───────────────┘ └──────────────┘ └──────────────┘
```

---

## Interface WorkerProvider

Tout adaptateur doit implémenter les trois méthodes suivantes :

| Méthode | Rôle | Paramètres principaux |
|---|---|---|
| **complete** | Envoie un prompt au modèle worker et retourne la réponse | `system_prompt`, `user_prompt`, `max_tokens`, `temperature` |
| **health_check** | Vérifie que le fournisseur est joignable et fonctionnel | Aucun |
| **get_info** | Retourne les métadonnées du provider (nom, modèle, endpoint) | Aucun |

### Réponse standardisée (WorkerResponse)

Quel que soit le fournisseur, la réponse est toujours normalisée dans un format unique contenant :

| Champ | Description |
|---|---|
| `content` | Le texte ou code généré par le worker |
| `tokens_input` | Nombre de tokens d'entrée consommés |
| `tokens_output` | Nombre de tokens de sortie consommés |
| `model` | Nom du modèle utilisé |
| `latency_ms` | Temps de réponse en millisecondes |
| `raw_response` | Réponse brute du provider (pour debug uniquement) |

---

## Adaptateurs disponibles

### 1. OpenAI Adapter

**Compatible avec :** OpenAI, Azure OpenAI, Groq, Together AI, vLLM (mode OpenAI-compatible), tout endpoint respectant le format OpenAI Chat Completions.

**Configuration :** Définir `WORKER_PROVIDER=openai` avec l'URL de l'endpoint, la clé API et le nom du modèle. Pour Azure, ajouter la variable `WORKER_API_VERSION`.

**Particularités :**
- Gère automatiquement la différence entre les endpoints OpenAI standard et Azure
- Compatible avec les déploiements personnalisés (custom deployment names)
- Supporte le mode streaming si activé

### 2. Anthropic Adapter

**Compatible avec :** API Anthropic directe (Claude).

**Configuration :** Définir `WORKER_PROVIDER=anthropic` avec l'URL Anthropic, la clé API et le nom du modèle.

**Particularités :**
- Utilise le format Messages API d'Anthropic (différent du format OpenAI)
- Le prompt système est passé séparément des messages utilisateur
- Gère les headers spécifiques requis par Anthropic (`anthropic-version`)

### 3. Ollama Adapter

**Compatible avec :** Ollama, LM Studio, tout serveur local exposant une API REST.

**Configuration :** Définir `WORKER_PROVIDER=ollama` avec l'URL locale (typiquement `http://localhost:11434`) et le nom du modèle.

**Particularités :**
- Pas de clé API requise (modèle local)
- Le health check vérifie que le modèle est bien chargé en mémoire
- Peut être plus lent mais coût = 0€

### 4. AWS Bedrock Adapter

**Compatible avec :** Tous les modèles disponibles sur Amazon Bedrock.

**Configuration :** Définir `WORKER_PROVIDER=bedrock` avec le nom du modèle et la région AWS. Les credentials sont lues automatiquement via le mécanisme standard AWS (profil, variables d'environnement, ou rôle IAM).

**Particularités :**
- Utilise le SDK AWS Bedrock Runtime (via `boto3`)
- Pas de variable `WORKER_API_KEY` — utilise les credentials AWS standard
- Supporte le cross-region inference

### 5. Custom Adapter

**Compatible avec :** Tout endpoint HTTP personnalisé.

**Configuration :** Définir `WORKER_PROVIDER=custom` avec l'URL de l'endpoint, la clé API, le nom du modèle, et optionnellement des headers personnalisés via `WORKER_CUSTOM_HEADERS`.

**Particularités :**
- Le format de requête et de réponse est configurable
- Idéal pour les modèles auto-hébergés avec des APIs non-standard

---

## Factory Pattern

Le bon adaptateur est instancié **automatiquement** selon la variable d'environnement `WORKER_PROVIDER`. Le système maintient un registre interne qui associe chaque nom de provider à sa classe d'adaptateur. Si le nom est inconnu, une erreur explicite est levée avec la liste des valeurs possibles.

---

## Ajouter un nouveau fournisseur

Pour ajouter un fournisseur non prévu, trois étapes suffisent :

1. **Créer un fichier** dans `src/nexus_worker/providers/` (ex: `nouveau_.py`)
2. **Implémenter les trois méthodes** de l'interface `WorkerProvider` (`complete`, `health_check`, `get_info`)
3. **Enregistrer** le nouvel adaptateur dans le registre du Factory

Aucune modification du code des outils MCP ou du serveur n'est nécessaire.

---

## Comparatif des fournisseurs

| Fournisseur | Coût | Latence | Qualité code | Offline | Idéal pour |
|---|---|---|---|---|---|
| **GPT-4o (Azure)** | €€ (gratuit si entreprise) | ~2-5s | ⭐⭐⭐⭐ | ❌ | Worker principal polyvalent |
| **GPT-4o-mini** | € | ~1-2s | ⭐⭐⭐ | ❌ | Tâches simples (doc, format) |
| **Claude Sonnet** | €€ | ~3-6s | ⭐⭐⭐⭐⭐ | ❌ | Code complexe, refactoring |
| **Ollama (CodeLlama)** | Gratuit | ~5-15s | ⭐⭐⭐ | ✅ | Développement offline |
| **Groq (Llama)** | € | ~0.5-1s | ⭐⭐⭐ | ❌ | Tâches rapides, forte volumétrie |
