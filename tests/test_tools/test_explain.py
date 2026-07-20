import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nexus_worker.core.errors import WorkerError
from nexus_worker.tools.explain import worker_explain_code


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.complete = AsyncMock(
        return_value=MagicMock(
            retry_count=0,
            used_fallback=False,
            content="Explanation content",
            model="test-model",
            tokens_input=100,
            tokens_output=200,
            latency_ms=123,
        )
    )
    provider.get_info = MagicMock(return_value={"provider": "test-provider"})
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
    tracker = MagicMock()
    tracker.check_and_record = MagicMock()
    return tracker


@pytest.fixture
def mock_read_file_safe():
    with patch(
        "nexus_worker.tools.explain.read_file_safe", return_value=("file content", 10)
    ) as mock:
        yield mock


@pytest.fixture
def mock_with_retry(mock_provider):
    with patch("nexus_worker.tools.explain.with_retry") as mock:
        mock.return_value = mock_provider.complete.return_value
        yield mock


@pytest.fixture
def mock_log_tool_call():
    with patch("nexus_worker.tools.explain.log_tool_call") as mock:
        yield mock


class TestWorkerExplainCodeHappyPath:
    @pytest.mark.asyncio
    async def test_explain_code_success(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
        mock_with_retry,
        mock_log_tool_call,
    ):
        result = await worker_explain_code(
            file_path="test.py",
            provider=mock_provider,
            prompt_engine=mock_prompt_engine,
            metrics=mock_metrics,
            call_tracker=mock_call_tracker,
        )
        result_json = json.loads(result)
        assert result_json["status"] == "success"
        assert result_json["explanation"] == "Explanation content"
        assert result_json["file_info"]["path"] == "test.py"
        assert result_json["file_info"]["total_lines"] == 10
        assert result_json["tokens_used"]["input"] == 100
        assert result_json["tokens_used"]["output"] == 200
        assert result_json["model"] == "test-model"


class TestWorkerExplainCodeEdgeCases:
    @pytest.mark.asyncio
    async def test_explain_code_empty_file(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_with_retry,
        mock_log_tool_call,
    ):
        with patch("nexus_worker.tools.explain.read_file_safe", return_value=("", 0)):
            result = await worker_explain_code(
                file_path="empty.py",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker,
            )
            result_json = json.loads(result)
            assert result_json["status"] == "success"
            assert result_json["explanation"] == "Explanation content"
            assert result_json["file_info"]["path"] == "empty.py"
            assert result_json["file_info"]["total_lines"] == 0

    @pytest.mark.asyncio
    async def test_explain_code_large_file(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_with_retry,
        mock_log_tool_call,
    ):
        large_content = "line\n" * 10000
        with patch(
            "nexus_worker.tools.explain.read_file_safe", return_value=(large_content, 10000)
        ):
            result = await worker_explain_code(
                file_path="large.py",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker,
            )
            result_json = json.loads(result)
            assert result_json["status"] == "success"
            assert result_json["explanation"] == "Explanation content"
            assert result_json["file_info"]["path"] == "large.py"
            assert result_json["file_info"]["total_lines"] == 10000


class TestWorkerExplainCodeErrorHandling:
    @pytest.mark.asyncio
    async def test_explain_code_file_not_found(
        self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker
    ):
        with patch(
            "nexus_worker.tools.explain.read_file_safe",
            side_effect=FileNotFoundError("File not found"),
        ):
            result = await worker_explain_code(
                file_path="missing.py",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker,
            )
            result_json = json.loads(result)
            assert result_json["status"] == "error"
            assert result_json["error_type"] == "file_error"
            assert "File not found" in result_json["message"]

    @pytest.mark.asyncio
    async def test_explain_code_permission_error(
        self, mock_provider, mock_prompt_engine, mock_metrics, mock_call_tracker
    ):
        with patch(
            "nexus_worker.tools.explain.read_file_safe",
            side_effect=PermissionError("Permission denied"),
        ):
            result = await worker_explain_code(
                file_path="restricted.py",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker,
            )
            result_json = json.loads(result)
            assert result_json["status"] == "error"
            assert result_json["error_type"] == "file_error"
            assert "Permission denied" in result_json["message"]

    @pytest.mark.asyncio
    async def test_explain_code_worker_error(
        self,
        mock_provider,
        mock_prompt_engine,
        mock_metrics,
        mock_call_tracker,
        mock_read_file_safe,
    ):
        with patch(
            "nexus_worker.tools.explain.with_retry", side_effect=WorkerError("Worker failed")
        ):
            result = await worker_explain_code(
                file_path="test.py",
                provider=mock_provider,
                prompt_engine=mock_prompt_engine,
                metrics=mock_metrics,
                call_tracker=mock_call_tracker,
            )
            result_json = json.loads(result)
            assert result_json["status"] == "error"
            assert "Worker failed" in result_json["message"]
