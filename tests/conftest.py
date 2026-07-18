"""Fixtures partagées pour les tests Nexus-Worker-MCP."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from nexus_worker.config import Config
from nexus_worker.core.errors import CallTracker
from nexus_worker.core.metrics import MetricsCollector
from nexus_worker.prompts.engine import PromptEngine
from nexus_worker.providers.base import WorkerResponse


@pytest.fixture
def mock_config() -> Config:
    """Configuration de test avec des valeurs par défaut."""
    config = Config(env_file=None)
    return config


@pytest.fixture
def mock_response() -> WorkerResponse:
    """Réponse Worker simulée pour les tests."""
    return WorkerResponse(
        content="def hello():\n    return 'Hello, World!'",
        tokens_input=100,
        tokens_output=50,
        model="test-model",
        latency_ms=250.0,
        raw_response=None,
    )


@pytest.fixture
def mock_provider(mock_response: WorkerResponse) -> AsyncMock:
    """Provider Worker simulé qui retourne toujours la mock_response."""
    from unittest.mock import MagicMock
    provider = AsyncMock()
    provider.complete.return_value = mock_response
    provider.health_check.return_value = True
    provider.get_info = MagicMock(return_value={
        "provider": "mock",
        "model": "test-model",
        "endpoint": "http://localhost:0",
    })
    return provider


@pytest.fixture
def prompt_engine() -> PromptEngine:
    """Moteur de prompts utilisant les templates par défaut."""
    return PromptEngine()


@pytest.fixture
def metrics() -> MetricsCollector:
    """Collecteur de métriques activé."""
    return MetricsCollector(enabled=True)


@pytest.fixture
def call_tracker() -> CallTracker:
    """Tracker anti-boucle avec limites élevées pour les tests."""
    return CallTracker(max_calls_per_tool=100, window_seconds=300)
