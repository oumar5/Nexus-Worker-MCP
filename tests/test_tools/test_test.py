import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from nexus_worker.tools.test import worker_generate_tests
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
    with patch("nexus_worker.tools.test.read_file_safe") as mock:
        yield mock

@pytest.fixture
def mock_with_retry():
    with patch("nexus_worker.tools.test.with_retry") as mock:
        yield mock

@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.test.log_tool_call") as mock:
        yield mock

@pytest.mark.asyncio
class TestWorkerGenerateTests:

    @pytest.mark.parametrize("file_content, total_lines", [
        ("def foo(): pass", 1),
        ("def bar():\n    pass", 2)
    ])
    async def test_worker_generate_tests_happy_path(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, mock_with_retry, mock_log_tool_call, file_content, total_lines):
        mock_read_file_safe.return_value = (file_content, total_lines)
        mock_with_retry.return_value = MagicMock(content="mock_test_code", model="mock_model", tokens_input=10, tokens_output=20, latency_ms=100)

        result = await worker_generate_tests(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker
        )

        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["test_code"] == "mock_test_code"
        assert result_data["source_file"] == "test.py"
        assert result_data["test_framework"] == "pytest"
        assert result_data["coverage_level"] == "thorough"
        assert result_data["tokens_used"]["input"] == 10
        assert result_data["tokens_used"]["output"] == 20
        assert result_data["model"] == "mock_model"

    @pytest.mark.parametrize("exception", [
        FileNotFoundError("File not found"),
        PermissionError("Permission denied"),
        ValueError("Invalid value")
    ])
    async def test_worker_generate_tests_file_errors(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, exception):
        mock_read_file_safe.side_effect = exception

        result = await worker_generate_tests(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker
        )

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_type"] == "file_error"
        assert result_data["message"] == str(exception)

    @pytest.mark.parametrize("focus_functions", ["foo", "bar,baz"])
    async def test_worker_generate_tests_with_focus_functions(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, mock_with_retry, mock_log_tool_call, focus_functions):
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.return_value = MagicMock(content="mock_test_code", model="mock_model", tokens_input=10, tokens_output=20, latency_ms=100)

        result = await worker_generate_tests(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
            focus_functions=focus_functions
        )

        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["test_code"] == "mock_test_code"
        assert result_data["source_file"] == "test.py"
        assert result_data["test_framework"] == "pytest"
        assert result_data["coverage_level"] == "thorough"
        assert result_data["tokens_used"]["input"] == 10
        assert result_data["tokens_used"]["output"] == 20
        assert result_data["model"] == "mock_model"

    async def test_worker_generate_tests_worker_error(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, mock_with_retry):
        mock_read_file_safe.return_value = ("def foo(): pass", 1)
        mock_with_retry.side_effect = WorkerError("Worker failed")

        result = await worker_generate_tests(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker
        )

        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "error_type" in result_data
        assert "message" in result_data
