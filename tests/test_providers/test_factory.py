"""Tests pour le Provider Factory."""

from __future__ import annotations

import pytest

from nexus_worker.config import WorkerConfig
from nexus_worker.providers.anthropic_ import AnthropicAdapter
from nexus_worker.providers.factory import create_provider, list_providers
from nexus_worker.providers.ollama_ import OllamaAdapter
from nexus_worker.providers.openai_ import OpenAIAdapter


class TestProviderFactory:
    """Tests pour la factory de providers."""

    def test_create_openai_provider(self) -> None:
        """Vérifie que le factory crée un OpenAIAdapter pour 'openai'."""
        config = WorkerConfig(
            WORKER_PROVIDER="openai",
            WORKER_API_BASE_URL="https://api.openai.com/v1",
            WORKER_API_KEY="test-key",
            WORKER_MODEL_NAME="gpt-4o",
        )
        provider = create_provider(config)
        assert isinstance(provider, OpenAIAdapter)

    def test_create_anthropic_provider(self) -> None:
        """Vérifie que le factory crée un AnthropicAdapter pour 'anthropic'."""
        config = WorkerConfig(
            WORKER_PROVIDER="anthropic",
            WORKER_API_BASE_URL="https://api.anthropic.com",
            WORKER_API_KEY="test-key",
            WORKER_MODEL_NAME="claude-sonnet-4-20250514",
        )
        provider = create_provider(config)
        assert isinstance(provider, AnthropicAdapter)

    def test_create_ollama_provider(self) -> None:
        """Vérifie que le factory crée un OllamaAdapter pour 'ollama'."""
        config = WorkerConfig(
            WORKER_PROVIDER="ollama",
            WORKER_API_BASE_URL="http://localhost:11434",
            WORKER_API_KEY="",
            WORKER_MODEL_NAME="codellama:34b",
        )
        provider = create_provider(config)
        assert isinstance(provider, OllamaAdapter)

    def test_create_unknown_provider_raises(self) -> None:
        """Vérifie qu'un provider inconnu lève une ValueError."""
        config = WorkerConfig(
            WORKER_PROVIDER="inexistant",
            WORKER_API_BASE_URL="http://localhost",
            WORKER_API_KEY="",
            WORKER_MODEL_NAME="test",
        )
        with pytest.raises(ValueError, match="Provider inconnu"):
            create_provider(config)

    def test_list_providers(self) -> None:
        """Vérifie que list_providers retourne les providers enregistrés."""
        providers = list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_provider_name_case_insensitive(self) -> None:
        """Vérifie que le nom du provider est insensible à la casse."""
        config = WorkerConfig(
            WORKER_PROVIDER="OpenAI",
            WORKER_API_BASE_URL="https://api.openai.com/v1",
            WORKER_API_KEY="test-key",
            WORKER_MODEL_NAME="gpt-4o",
        )
        provider = create_provider(config)
        assert isinstance(provider, OpenAIAdapter)
