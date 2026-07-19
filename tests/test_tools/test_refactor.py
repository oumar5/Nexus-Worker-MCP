import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from nexus_worker.tools.refactor import worker_refactor_code
from nexus_worker.core.errors import WorkerError


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock(return_value=MagicMock(
        content="refactored code",
        model="test-model",
        tokens_input=100,
        tokens_output=200,
        latency_ms=1500
    ))
    provider.get_info = MagicMock(return_value={"provider": "test-provider"})
    return provider


@pytest.fixture
def mock_prompt_engine():
    prompt_engine = MagicMock()
    prompt_engine.get_system_prompt = MagicMock(return_value="system prompt")
    return prompt_engine


@pytest.fixture
def mock_metrics():
    return MagicMock()


@pytest.fixture
def mock_call_tracker():
    tracker = MagicMock()
    tracker.check_and_record = MagicMock()
    return tracker


@pytest.fixture
def mock_read_file_safe():
    with patch("nexus_worker.tools.refactor.read_file_safe", return_value=("file content", 100)) as mock:
        yield mock


@pytest.fixture
def mock_with_retry(mock_provider):
    with patch("nexus_worker.tools.refactor.with_retry") as mock:
        mock.return_value = mock_provider.complete.return_value
        yield mock


@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.refactor.log_tool_call") as mock:
        yield mock


@pytest.mark.asyncio
class TestWorkerRefactorCodeHappyPath:
    async def test_refactor_code_success(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, mock_with_retry, mock_log_tool_call):
        result = await worker_refactor_code(
            file_path="test.py",
            instruction="Refactor this code",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker
        )
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["refactored_code"] == "refactored code"
        assert result_data["file_info"]["path"] == "test.py"
        assert result_data["file_info"]["total_lines"] == 100
        assert result_data["tokens_used"]["input"] == 100
        assert result_data["tokens_used"]["output"] == 200
        assert result_data["model"] == "test-model"


@pytest.mark.asyncio
class TestWorkerRefactorCodeEdgeCases:
    # Correction: mock_read_file_safe injecté comme fixture au lieu de variable globale
    async def test_refactor_code_empty_file(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_with_retry, mock_log_tool_call):
        with patch("nexus_worker.tools.refactor.read_file_safe", return_value=("", 0)):
            result = await worker_refactor_code(
                file_path="empty.py",
                instruction="Refactor this code",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker
            )
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["refactored_code"] == "refactored code"
            assert result_data["file_info"]["path"] == "empty.py"
            assert result_data["file_info"]["total_lines"] == 0

    async def test_refactor_code_large_file(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_with_retry, mock_log_tool_call):
        large_content = "a" * 10000
        with patch("nexus_worker.tools.refactor.read_file_safe", return_value=(large_content, 10000)):
            result = await worker_refactor_code(
                file_path="large.py",
                instruction="Refactor this code",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker
            )
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["refactored_code"] == "refactored code"
            assert result_data["file_info"]["path"] == "large.py"
            assert result_data["file_info"]["total_lines"] == 10000


@pytest.mark.asyncio
class TestWorkerRefactorCodeErrorHandling:
    async def test_refactor_code_file_not_found(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_with_retry, mock_log_tool_call):
        with patch("nexus_worker.tools.refactor.read_file_safe", side_effect=FileNotFoundError("File not found")):
            result = await worker_refactor_code(
                file_path="missing.py",
                instruction="Refactor this code",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker
            )
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_type"] == "file_error"
            assert "File not found" in result_data["message"]

    async def test_refactor_code_permission_error(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_with_retry, mock_log_tool_call):
        with patch("nexus_worker.tools.refactor.read_file_safe", side_effect=PermissionError("Permission denied")):
            result = await worker_refactor_code(
                file_path="protected.py",
                instruction="Refactor this code",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker
            )
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_type"] == "file_error"
            assert "Permission denied" in result_data["message"]

    async def test_refactor_code_worker_error(self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker, mock_read_file_safe, mock_with_retry, mock_log_tool_call):
        mock_with_retry.side_effect = WorkerError("Worker failed")
        result = await worker_refactor_code(
            file_path="test.py",
            instruction="Refactor this code",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker
        )
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert "error_type" in result_data
        assert "message" in result_data
