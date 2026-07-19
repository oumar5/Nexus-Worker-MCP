"""Tests pour l_adaptateur Ollama."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_worker.config import WorkerConfig
from nexus_worker.providers.ollama_ import OllamaAdapter


@pytest.fixture
def base_config():
    return WorkerConfig(
        provider="ollama",
        api_base_url="http://localhost:11434",
        api_key="",
        model_name="llama3",
    )


def test_ollama_init(base_config):
    """Test l_initialisation Ollama."""
    adapter = OllamaAdapter(base_config)
    info = adapter.get_info()
    assert info["provider"] == "ollama"
    assert info["model"] == "llama3"


@pytest.mark.asyncio
@patch("nexus_worker.providers.ollama_.httpx.AsyncClient")
async def test_ollama_complete_success(mock_client_cls, base_config):
    """Test d_une completion reussie."""
    mock_client = AsyncMock()
    mock_client_cls.return_value.__aenter__.return_value = mock_client

    # Simuler la reponse Ollama
    mock_response = {
        "message": {"content": "Response content"},
        "prompt_eval_count": 10,
        "eval_count": 20,
    }

    mock_http_response = AsyncMock()
    mock_http_response.json = MagicMock(return_value=mock_response)
    mock_client.post.return_value = mock_http_response

    adapter = OllamaAdapter(base_config)
    result = await adapter.complete("System", "User")

    assert result.content == "Response content"
    assert result.tokens_input == 10
    assert result.tokens_output == 20
    assert result.model == "llama3"
