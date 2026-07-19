import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_worker.core.errors import WorkerError
from nexus_worker.tools.analyze import worker_analyze_file


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock()
    provider.get_info = MagicMock(return_value={"provider": "mock_provider"})
    return provider


@pytest.fixture
def mock_prompt_engine():
    prompt_engine = MagicMock()
    prompt_engine.get_system_prompt = MagicMock(return_value="System prompt")
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
    with patch("nexus_worker.tools.analyze.read_file_safe") as mock:
        yield mock


@pytest.fixture
def mock_with_retry():
    with patch("nexus_worker.tools.analyze.with_retry") as mock:
        yield mock


@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.analyze.log_tool_call") as mock:
        yield mock


@pytest.mark.asyncio
class TestWorkerAnalyzeFileHappyPath:
    async def test_analyze_file_success(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ):
        mock_read_file_safe.return_value = ("file content", 100)
        mock_with_retry.return_value = MagicMock(
            content="analysis result",
            model="mock_model",
            tokens_input=10,
            tokens_output=20,
            latency_ms=100,
        )

        result = await worker_analyze_file(
            file_path="test.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["analysis"] == "analysis result"
        assert result_data["file_info"]["path"] == "test.txt"
        assert result_data["file_info"]["total_lines"] == 100
        assert result_data["tokens_used"]["input"] == 10
        assert result_data["tokens_used"]["output"] == 20
        assert result_data["model"] == "mock_model"


@pytest.mark.asyncio
class TestWorkerAnalyzeFileEdgeCases:
    async def test_analyze_file_empty_content(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ):
        mock_read_file_safe.return_value = ("", 0)
        mock_with_retry.return_value = MagicMock(
            content="empty analysis",
            model="mock_model",
            tokens_input=5,
            tokens_output=5,
            latency_ms=50,
        )

        result = await worker_analyze_file(
            file_path="empty.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["analysis"] == "empty analysis"
        assert result_data["file_info"]["path"] == "empty.txt"
        assert result_data["file_info"]["total_lines"] == 0
        assert result_data["tokens_used"]["input"] == 5
        assert result_data["tokens_used"]["output"] == 5
        assert result_data["model"] == "mock_model"

    async def test_analyze_file_large_content(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ):
        large_content = "line\n" * 10000
        mock_read_file_safe.return_value = (large_content, 10000)
        mock_with_retry.return_value = MagicMock(
            content="large analysis",
            model="mock_model",
            tokens_input=1000,
            tokens_output=1000,
            latency_ms=500,
        )

        result = await worker_analyze_file(
            file_path="large.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["analysis"] == "large analysis"
        assert result_data["file_info"]["path"] == "large.txt"
        assert result_data["file_info"]["total_lines"] == 10000
        assert result_data["tokens_used"]["input"] == 1000
        assert result_data["tokens_used"]["output"] == 1000
        assert result_data["model"] == "mock_model"


@pytest.mark.asyncio
class TestWorkerAnalyzeFileErrorHandling:
    async def test_analyze_file_not_found(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
    ):
        mock_read_file_safe.side_effect = FileNotFoundError("File not found")

        result = await worker_analyze_file(
            file_path="nonexistent.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_type"] == "file_error"
        assert "File not found" in result_data["message"]

    async def test_analyze_file_permission_error(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
    ):
        mock_read_file_safe.side_effect = PermissionError("Permission denied")

        result = await worker_analyze_file(
            file_path="restricted.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_type"] == "file_error"
        assert "Permission denied" in result_data["message"]

    async def test_analyze_file_worker_error(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
    ):
        mock_read_file_safe.return_value = ("file content", 100)
        mock_with_retry.side_effect = WorkerError("Worker failed")

        result = await worker_analyze_file(
            file_path="test.txt",
            question="What is this file about?",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            allowed_paths=[Path("/allowed")],
            max_retries=3,
            max_tokens=4096,
            focus_lines="",
        )

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "Worker failed" in result_data["message"]
