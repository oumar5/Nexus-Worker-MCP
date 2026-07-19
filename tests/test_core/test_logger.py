"""Tests pour le systeme de logging."""

import json
import logging
from unittest.mock import MagicMock, patch

from nexus_worker.core.logger import StructuredFormatter, log_tool_call, setup_logger


def test_structured_formatter():
    """Test que le formateur JSON produit bien du JSON valide avec les champs requis."""
    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="nexus_worker",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["message"] == "Test message"
    assert "timestamp" in data


def test_setup_logger():
    """Test la configuration du logger."""
    logger = setup_logger("DEBUG", log_file=None)
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0].formatter, StructuredFormatter)


@patch("nexus_worker.core.logger.get_logger")
def test_log_tool_call(mock_get_logger):
    """Test le log specifique aux appels d_outils."""
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    log_tool_call(
        tool="generate",
        provider="openai",
        model="gpt-4",
        tokens_input=10,
        tokens_output=20,
        latency_ms=150.5,
        status="success"
    )

    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    assert "Tool call: generate" in args[1]

    extra = kwargs.get("extra", {})
    assert extra["tool"] == "generate"
    assert extra["provider"] == "openai"
    assert extra["tokens_input"] == 10
    assert extra["tokens_output"] == 20
