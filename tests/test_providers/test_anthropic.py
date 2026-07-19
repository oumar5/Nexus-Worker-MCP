"""Tests pour l_adaptateur Anthropic."""

from unittest.mock import AsyncMock, patch

import pytest

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import WorkerAuthError
from nexus_worker.providers.anthropic_ import AnthropicAdapter


@pytest.fixture
def base_config():
    return WorkerConfig(
        provider="anthropic",
        api_base_url="https://api.anthropic.com/v1",
        api_key="test-key",
        model_name="claude-3-5-sonnet",
    )


def test_anthropic_init(base_config):
    """Test l_initialisation Anthropic."""
    adapter = AnthropicAdapter(base_config)
    info = adapter.get_info()
    assert info["provider"] == "anthropic"
    assert info["model"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
@patch("nexus_worker.providers.anthropic_.AsyncAnthropic")
async def test_anthropic_complete_success(mock_anthropic_cls, base_config):
    """Test d_une completion reussie."""
    mock_client = AsyncMock()
    mock_anthropic_cls.return_value = mock_client

    # Simuler la reponse Anthropic
    mock_content = AsyncMock()
    mock_content.type = "text"
    mock_content.text = "Response content"
    mock_response = AsyncMock()
    mock_response.content = [mock_content]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20
    mock_response.model = "claude-3-5-sonnet"
    mock_response.model_dump.return_value = {}

    mock_client.messages.create.return_value = mock_response

    adapter = AnthropicAdapter(base_config)
    result = await adapter.complete("System", "User")

    assert result.content == "Response content"
    assert result.tokens_input == 10
    assert result.tokens_output == 20
    assert result.model == "claude-3-5-sonnet"


@pytest.mark.asyncio
@patch("nexus_worker.providers.anthropic_.AsyncAnthropic")
async def test_anthropic_auth_error(mock_anthropic_cls, base_config):
    """Test le mapping d_une erreur d_authentification."""
    from anthropic import AuthenticationError

    mock_client = AsyncMock()
    mock_anthropic_cls.return_value = mock_client

    mock_client.messages.create.side_effect = AuthenticationError(
        message="Invalid key",
        response=AsyncMock(),
        body=None
    )

    adapter = AnthropicAdapter(base_config)

    with pytest.raises(WorkerAuthError, match="Clé API Anthropic invalide"):
        await adapter.complete("Sys", "User")
