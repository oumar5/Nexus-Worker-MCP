"""Tests unitaires pour worker_document_code."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_worker.tools.document import worker_document_code
from nexus_worker.core.errors import WorkerError


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock()
    provider.get_info = MagicMock(return_value={"provider": "mock_provider"})
    return provider


@pytest.fixture
def mock_prompt_engine():
    prompt_engine = MagicMock()
    prompt_engine.get_system_prompt = MagicMock(return_value="mock_system_prompt")
    return prompt_engine


@pytest.fixture
def mock_metrics():
    return MagicMock()


@pytest.fixture
def mock_call_tracker():
    call_tracker = MagicMock()
    call_tracker.check_and_record = MagicMock()
    return call_tracker


@pytest.fixture
def mock_read_file_safe():
    with patch("nexus_worker.tools.document.read_file_safe") as mock:
        yield mock


@pytest.fixture
def mock_with_retry():
    with patch("nexus_worker.tools.document.with_retry") as mock:
        yield mock


@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.document.log_tool_call") as mock:
        yield mock


@pytest.mark.asyncio
class TestWorkerDocumentCode:

    async def test_happy_path_returns_documented_code(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ) -> None:
        """Doit retourner le code documenté dans la réponse."""
        documented = '"""Module doc."""\n\ndef foo():\n    """Do foo."""\n    pass'
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.return_value = MagicMock(
            content=documented,
            model="mock-model",
            tokens_input=80,
            tokens_output=120,
            latency_ms=300,
        )

        result = await worker_document_code(
            file_path="module.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["documented_code"] == documented
        assert data["file_info"]["path"] == "module.py"
        assert data["tokens_used"]["input"] == 80
        assert data["tokens_used"]["output"] == 120

    @pytest.mark.parametrize("exception", [
        FileNotFoundError("File not found"),
        PermissionError("Permission denied"),
        ValueError("Invalid"),
    ])
    async def test_file_errors_return_error_status(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        exception,
    ) -> None:
        """Doit retourner status error pour les erreurs de fichier."""
        mock_read_file_safe.side_effect = exception

        result = await worker_document_code(
            file_path="module.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error_type"] == "file_error"

    async def test_worker_error_returns_error_status(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
    ) -> None:
        """Doit retourner status error si le Worker échoue."""
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.side_effect = WorkerError("Worker unavailable")

        result = await worker_document_code(
            file_path="module.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "error"
        assert "error_type" in data

    async def test_with_style_parameter(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ) -> None:
        """Le paramètre style doit être accepté sans erreur."""
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.return_value = MagicMock(
            content="documented",
            model="m",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
        )

        result = await worker_document_code(
            file_path="f.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            style="google",
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert data["documented_code"] == "documented"
