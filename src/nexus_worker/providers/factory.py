"""Factory pour l'instanciation automatique des adaptateurs.

Choisit le bon adaptateur selon la variable WORKER_PROVIDER
et gère optionnellement le provider de secours.
"""

from __future__ import annotations

from typing import Any

from nexus_worker.config import Config, WorkerConfig
from nexus_worker.providers.anthropic_ import AnthropicAdapter
from nexus_worker.providers.base import WorkerProvider
from nexus_worker.providers.ollama_ import OllamaAdapter
from nexus_worker.providers.openai_ import OpenAIAdapter


# Registre des adaptateurs disponibles
_REGISTRY: dict[str, type] = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "ollama": OllamaAdapter,
}


def register_provider(name: str, adapter_class: type) -> None:
    """Enregistre un nouvel adaptateur dans le registre.

    Args:
        name: Nom du provider (utilisé dans WORKER_PROVIDER).
        adapter_class: Classe de l'adaptateur à enregistrer.
    """
    _REGISTRY[name] = adapter_class


def create_provider(config: WorkerConfig) -> WorkerProvider:
    """Instancie l'adaptateur correspondant à la configuration.

    Args:
        config: Configuration du worker avec le provider, l'endpoint et le modèle.

    Returns:
        Instance de l'adaptateur configuré.

    Raises:
        ValueError: Si le provider n'est pas dans le registre.
    """
    provider_name = config.provider.lower()

    if provider_name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Provider inconnu: '{provider_name}'. "
            f"Valeurs possibles: {available}"
        )

    adapter_class = _REGISTRY[provider_name]
    return adapter_class(config)


def create_providers_from_config(config: Config) -> tuple[WorkerProvider, WorkerProvider | None]:
    """Crée le provider principal et optionnellement le provider de secours.

    Args:
        config: Configuration globale du serveur.

    Returns:
        Tuple (provider_principal, provider_fallback ou None).
    """
    primary = create_provider(config.worker)

    fallback = None
    if config.fallback.is_configured:
        # Construire un WorkerConfig à partir de la config fallback
        fallback_worker_config = WorkerConfig(
            WORKER_PROVIDER=config.fallback.provider,
            WORKER_API_BASE_URL=config.fallback.api_base_url or "",
            WORKER_API_KEY=config.fallback.api_key or "",
            WORKER_MODEL_NAME=config.fallback.model_name or "",
        )
        fallback = create_provider(fallback_worker_config)

    return primary, fallback


def list_providers() -> list[str]:
    """Retourne la liste des providers disponibles.

    Returns:
        Liste des noms de providers enregistrés.
    """
    return sorted(_REGISTRY.keys())
