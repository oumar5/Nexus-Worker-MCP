# Analyse FinOps — Nexus-Worker-MCP

Ce document présente une analyse financière de l'architecture **Nexus-Worker-MCP** comparée à une utilisation directe des modèles de pointe (état du marché juillet 2026). Il explique également comment mesurer vos économies en temps réel via l'outil `worker_get_metrics`.

---

## 1. Tarifs des modèles (pour 1 million de tokens)

### Modèles "Cerveau" — haute intelligence, coûteux

| Modèle | Input / 1M tokens | Output / 1M tokens |
|:---|:---|:---|
| GPT-5.6 Sol (OpenAI) | 5,00 $ | 30,00 $ |
| Claude 4.8 Opus (Anthropic) | 5,00 $ | 25,00 $ |
| Gemini 3.1 Pro (Google) | 2,00 $ | 12,00 $ |

### Modèles "Worker" — exécution rapide et économique

| Modèle | Input / 1M tokens | Output / 1M tokens |
|:---|:---|:---|
| GPT-4o-mini (OpenAI) | 0,15 $ | 0,60 $ |
| Gemini 2.0 Flash (Google) | 0,10 $ | 0,40 $ |
| Claude 3 Haiku (Anthropic) | 0,25 $ | 1,25 $ |
| Ollama (modèle local) | 0,00 $ | 0,00 $ |

---

## 2. Cas pratique : génération de tests unitaires

**Scénario :** un développeur demande de lire un fichier source (10 000 tokens) et de générer une suite complète de tests (3 000 tokens).

### Sans Nexus — le Cerveau fait tout

| Cerveau utilisé | Total par exécution |
|:---|:---|
| GPT-5.6 Sol | **0,140 $** |
| Claude 4.8 Opus | **0,125 $** |
| Gemini 3.1 Pro | **0,056 $** |

### Avec Nexus — délégation au Worker

Le Cerveau ne voit que la consigne initiale (~500 tokens) et le résultat final compact. Le Worker traite le fichier complet et génère les tests.

| Étape | Modèle | Coût |
|:---|:---|:---|
| Orchestration + validation | Cerveau (GPT-5.6 Sol) | 0,004 $ |
| Lecture + génération des tests | Worker (GPT-4o-mini) | 0,003 $ |
| **Total** | | **0,007 $** |

**Facteur de réduction : 20x — soit 95 % d'économie.**

---

## 3. Impact du cache

Le cache en mémoire élimine complètement le coût des appels répétés sur le même fichier non modifié. Une revue de code ou une documentation demandée deux fois dans la même session ne consomme des tokens qu'une seule fois.

**Exemple — revue de code demandée 3 fois dans la même session :**

| Appel | Sans cache | Avec cache |
|:---|:---|:---|
| 1er appel | 0,007 $ | 0,007 $ |
| 2e appel (même fichier) | 0,007 $ | 0,000 $ |
| 3e appel (même fichier) | 0,007 $ | 0,000 $ |
| **Total** | **0,021 $** | **0,007 $** |

Sur une session de développement avec 30 % de requêtes répétées, le cache réduit la facture Worker d'environ 30 % supplémentaire.

---

## 4. Mesurer vos économies en temps réel

Nexus expose un outil `worker_get_metrics` qui calcule automatiquement vos économies pour la session en cours. Il compare le coût réel des appels Worker avec ce qu'aurait coûté la même charge de travail sur le Cerveau.

Il retourne notamment :

- Le nombre total de tokens délégués au Worker
- Le coût réel de la session Worker
- Le coût estimé si le Cerveau avait tout traité
- L'économie réalisée en dollars et en pourcentage
- Le taux de cache hits (proportion d'appels servis depuis le cache)

Pour l'appeler, demandez simplement au Cerveau en fin de session : *"Affiche-moi le rapport FinOps de la session."*

Les prix utilisés par défaut correspondent à GPT-4o-mini (Worker) et GPT-5.6 Sol (Cerveau). Ils peuvent être ajustés si vous utilisez un autre provider — par exemple Gemini 2.0 Flash comme Worker est encore moins cher.

---

## 5. Retour sur investissement mensuel

| Architecture | Coût par tâche | Facture pour 1 000 tâches/mois |
|:---|:---|:---|
| Sans Nexus — GPT-5.6 Sol 100 % | 0,140 $ | **140,00 $** |
| Avec Nexus — GPT-5.6 + GPT-4o-mini | 0,007 $ | **7,00 $** |
| Avec Nexus + cache (30 % hit rate) | ~0,005 $ | **~5,00 $** |

L'économie mensuelle estimée est de **133 $ à 135 $ pour 1 000 tâches**, soit une réduction de 95 à 96 %.

L'architecture est rentabilisée dès la première heure d'utilisation. Les 15 minutes de configuration initiale sont amorties après 2 tâches déléguées.

---

## 6. Conseils pour maximiser les économies

- **Garder le cache activé** — il est actif par défaut et réduit significativement la facture sur les sessions longues.
- **Augmenter le TTL du cache** si vos sessions dépassent une heure (variable `CACHE_TTL_SECONDS`).
- **Choisir le bon Worker** — Gemini 2.0 Flash est actuellement le moins cher pour les tâches de génération standard.
- **Configurer `ALLOWED_PATHS` précisément** — limiter les chemins autorisés évite d'exposer des fichiers volumineux inutiles.
- **Consulter les métriques régulièrement** — le rapport FinOps permet d'ajuster la stratégie de délégation en fonction des coûts réels.
