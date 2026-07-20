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
          ┌────────────────┬────────────────┬──────────────┐
          │                │                │              │
 ┌────────▼──────┐ ┌──────▼───────┐ ┌──────▼─────┐ ┌──────▼───────┐
 │ OpenAIAdapter │ │AnthropicAdpt │ │GeminiAdaptr │ │ OllamaAdaptr │
 │               │ │              │ │              │ │              │
 │ OpenAI        │ │ Claude API   │ │ Google AI    │ │ Local models │
 │ Azure OpenAI  │ │              │ │ Studio       │ │ vLLM         │
 │ Groq          │ │              │ │ Vertex AI    │ │ LM Studio    │
 └───────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
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
| `retry_count` | Nombre de tentatives supplémentaires effectuées avant succès (0 si passé du premier coup) |
| `used_fallback` | `True` si la réponse provient du provider de secours au lieu du principal |

Les champs `retry_count` et `used_fallback` sont remplis automatiquement par la couche de résilience (voir `CompositeProvider` ci-dessous et `with_retry` dans [error-handling.md](error-handling.md)). Ils remontent ensuite dans les métriques de session.

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
- Coût = 0 €

### 4. Google Gemini Adapter ✨ Nouveau

**Compatible avec :** Google AI Studio, Vertex AI.

**Configuration :** Définir `WORKER_PROVIDER=gemini`, votre clé Google AI Studio dans `WORKER_API_KEY`, et le modèle souhaité. Pas de `WORKER_API_BASE_URL` nécessaire.

```env
WORKER_PROVIDER=gemini
WORKER_API_KEY=AIza-votre-cle-google-ai-studio
WORKER_MODEL_NAME=gemini-2.0-flash
```

**Particularités :**
- Utilise le SDK officiel `google-genai`
- Modèles recommandés pour le Worker : `gemini-2.0-flash` (rapide, économique), `gemini-1.5-flash`
- La clé est obtenue gratuitement sur [Google AI Studio](https://aistudio.google.com/)
- Très faible coût — idéal comme Worker économique

### 5. CompositeProvider — bascule automatique primaire → fallback

**Rôle :** Wrapper transparent qui combine un provider **principal** et un provider de **secours** en respectant l'interface `WorkerProvider`. Le reste du code (outils, serveur) ne le distingue pas d'un provider simple.

**Comportement :**
- `complete()` appelle d'abord le provider principal. Si celui-ci lève une `WorkerError`, le composite bascule automatiquement sur le fallback et marque la réponse avec `used_fallback=True`.
- `health_check()` retourne `True` si **au moins un** des deux providers répond.
- `get_info()` retourne les infos du principal enrichies d'une clé `fallback` avec les infos du secours.

**Quand est-il utilisé ?** Uniquement si les variables `WORKER_FALLBACK_*` sont définies dans le `.env`. Dans le cas contraire, le serveur utilise directement le provider principal, sans wrapper. Le composite est donc **strictement opt-in**.

**Configuration minimale :**

```env
# Principal
WORKER_PROVIDER=openai
WORKER_API_KEY=sk-...
WORKER_MODEL_NAME=gpt-4o-mini

# Fallback (optionnel — active le CompositeProvider)
WORKER_FALLBACK_PROVIDER=ollama
WORKER_FALLBACK_API_BASE_URL=http://localhost:11434
WORKER_FALLBACK_MODEL_NAME=qwen2.5-coder
```

Voir la stratégie complète dans [error-handling.md](error-handling.md).

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
| **GPT-4o-mini** | € | ~1-2s | ⭐⭐⭐ | ❌ | Worker par défaut, tâches simples |
| **Gemini 2.0 Flash** | € | ~1-3s | ⭐⭐⭐ | ❌ | Alternative économique à GPT-4o-mini |
| **GPT-4o (Azure)** | €€ | ~2-5s | ⭐⭐⭐⭐ | ❌ | Worker polyvalent haut de gamme |
| **Claude 3 Haiku** | € | ~1-3s | ⭐⭐⭐⭐ | ❌ | Refactoring, code complexe |
| **Ollama (qwen2.5-coder)** | Gratuit | ~5-15s | ⭐⭐⭐ | ✅ | Développement offline, confidentialité |
| **Groq (Llama)** | € | ~0.5-1s | ⭐⭐⭐ | ❌ | Tâches rapides, forte volumétrie |
