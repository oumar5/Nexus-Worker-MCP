"""Tests unitaires pour worker_review_code."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_worker.core.errors import WorkerError
from nexus_worker.tools.review import worker_review_code


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
    with patch("nexus_worker.tools.review.read_file_safe") as mock:
        yield mock


@pytest.fixture
def mock_with_retry():
    with patch("nexus_worker.tools.review.with_retry") as mock:
        yield mock


@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.review.log_tool_call") as mock:
        yield mock


@pytest.mark.asyncio
class TestWorkerReviewCode:
    async def test_happy_path_returns_success(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ) -> None:
        """Doit retourner un status success avec une revue JSON parsée."""
        review_json = (
            '{"summary": "Bon code.", "bugs": [], "security": [], '
            '"performance": [], "maintainability": [], "style": []}'
        )
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.return_value = MagicMock(
            content=review_json,
            model="mock-model",
            tokens_input=100,
            tokens_output=50,
            latency_ms=200,
        )

        result = await worker_review_code(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert "review" in data
        assert data["review"]["summary"] == "Bon code."
        assert data["tokens_used"]["input"] == 100

    @pytest.mark.parametrize(
        "exception",
        [
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            ValueError("Invalid path"),
        ],
    )
    async def test_file_errors_return_error_status(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        exception,
    ) -> None:
        """Doit retourner un status error pour les erreurs de fichier."""
        mock_read_file_safe.side_effect = exception

        result = await worker_review_code(
            file_path="test.py",
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
        """Doit retourner un status error si le Worker échoue."""
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.side_effect = WorkerError("Worker failed")

        result = await worker_review_code(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "error"
        assert "error_type" in data

    async def test_non_json_response_stored_as_raw(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ) -> None:
        """Une réponse Worker non-JSON doit être stockée dans raw_review."""
        mock_read_file_safe.return_value = ("code", 1)
        mock_with_retry.return_value = MagicMock(
            content="Voici mes commentaires en texte libre...",
            model="m",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
        )

        result = await worker_review_code(
            file_path="f.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert "raw_review" in data["review"]

    async def test_with_focus_parameter(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ) -> None:
        """Doit inclure le focus dans le prompt utilisateur."""
        mock_read_file_safe.return_value = ("code", 1)
        mock_with_retry.return_value = MagicMock(
            content=(
                '{"summary": "ok", "bugs": [], "security": [], '
                '"performance": [], "maintainability": [], "style": []}'
            ),
            model="m",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
        )

        result = await worker_review_code(
            file_path="f.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            focus="security",
        )

        data = json.loads(result)
        assert data["status"] == "success"
