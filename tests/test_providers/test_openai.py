"""Tests pour l_adaptateur OpenAI."""

from unittest.mock import AsyncMock, patch

import pytest
from openai import AuthenticationError, RateLimitError

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import WorkerAuthError, WorkerRateLimitError
from nexus_worker.providers.openai_ import OpenAIAdapter


@pytest.fixture
def base_config():
    return WorkerConfig(
        provider="openai",
        api_base_url="https://api.openai.com/v1",
        api_key="test-key",
        model_name="gpt-4",
    )


def test_openai_init_standard(base_config):
    """Test l_initialisation standard OpenAI."""
    adapter = OpenAIAdapter(base_config)
    info = adapter.get_info()
    assert info["provider"] == "openai"
    assert info["model"] == "gpt-4"
    assert info["mode"] == "standard"


def test_openai_init_azure():
    """Test l_initialisation mode Azure."""
    config = WorkerConfig(
        provider="openai",
        api_base_url="https://test.openai.azure.com/",
        api_key="test-key",
        model_name="gpt-4",
        api_version="2024-02-15-preview",
    )
    adapter = OpenAIAdapter(config)
    info = adapter.get_info()
    assert info["mode"] == "azure"


@pytest.mark.asyncio
@patch("nexus_worker.providers.openai_.AsyncOpenAI")
async def test_openai_complete_success(mock_openai_cls, base_config):
    """Test d_une completion reussie."""
    mock_client = AsyncMock()
    mock_openai_cls.return_value = mock_client

    # Simuler la reponse OpenAI
    mock_choice = AsyncMock()
    mock_choice.message.content = "Response content"
    mock_response = AsyncMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.model = "gpt-4"

    mock_client.chat.completions.create.return_value = mock_response

    adapter = OpenAIAdapter(base_config)
    result = await adapter.complete("System", "User")

    assert result.content == "Response content"
    assert result.tokens_input == 10
    assert result.tokens_output == 20
    assert result.model == "gpt-4"


@pytest.mark.asyncio
@patch("nexus_worker.providers.openai_.AsyncOpenAI")
async def test_openai_auth_error(mock_openai_cls, base_config):
    """Test le mapping d_une erreur d_authentification."""
    mock_client = AsyncMock()
    mock_openai_cls.return_value = mock_client

    mock_client.chat.completions.create.side_effect = AuthenticationError(
        message="Invalid key",
        response=AsyncMock(),
        body=None
    )

    adapter = OpenAIAdapter(base_config)

    with pytest.raises(WorkerAuthError, match="Clé API invalide"):
        await adapter.complete("Sys", "User")


@pytest.mark.asyncio
@patch("nexus_worker.providers.openai_.AsyncOpenAI")
async def test_openai_rate_limit_error(mock_openai_cls, base_config):
    """Test le mapping d_une erreur de quota."""
    mock_client = AsyncMock()
    mock_openai_cls.return_value = mock_client

    mock_client.chat.completions.create.side_effect = RateLimitError(
        message="Quota exceeded",
        response=AsyncMock(),
        body=None
    )

    adapter = OpenAIAdapter(base_config)

    with pytest.raises(WorkerRateLimitError, match="Quota dépassé"):
        await adapter.complete("Sys", "User")
