"""Tests pour le systeme de metriques."""


from nexus_worker.core.metrics import MetricsCollector


def test_metrics_disabled():
    """Test que le collecteur desactive ne collecte rien."""
    metrics = MetricsCollector(enabled=False)
    metrics.record_call("test_tool", tokens_input=100)

    summary = metrics.get_summary()
    assert summary["enabled"] is False
    assert "tools" not in summary


def test_metrics_enabled_record_success():
    """Test l_enregistrement d_un appel reussi."""
    metrics = MetricsCollector(enabled=True)
    metrics.record_call(
        tool_name="generate",
        tokens_input=100,
        tokens_output=50,
        latency_ms=250.0,
        success=True,
    )

    summary = metrics.get_summary()
    assert summary["total_calls"] == 1
    assert summary["total_tokens_input"] == 100
    assert summary["total_tokens_output"] == 50

    tool_stats = summary["tools"]["generate"]
    assert tool_stats["calls"] == 1
    assert tool_stats["success_rate"] == 100.0
    assert tool_stats["tokens_input"] == 100


def test_metrics_enabled_record_failure():
    """Test l_enregistrement d_un appel echoue."""
    metrics = MetricsCollector(enabled=True)
    metrics.record_call(tool_name="analyze", success=False)

    summary = metrics.get_summary()
    assert summary["total_calls"] == 1

    tool_stats = summary["tools"]["analyze"]
    assert tool_stats["calls"] == 1
    assert tool_stats["success_rate"] == 0.0


def test_metrics_tracks_retries_and_fallbacks():
    """Test que les retries et bascules fallback sont comptabilises."""
    metrics = MetricsCollector(enabled=True)
    metrics.record_call(
        tool_name="analyze",
        tokens_input=100,
        tokens_output=50,
        success=True,
        was_retry=True,
        was_fallback=True,
    )
    metrics.record_call(
        tool_name="analyze",
        tokens_input=100,
        tokens_output=50,
        success=True,
    )

    summary = metrics.get_summary()
    # Totaux globaux de session
    assert summary["total_retries"] == 1
    assert summary["total_fallbacks"] == 1
    # Detail par outil
    tool_stats = summary["tools"]["analyze"]
    assert tool_stats["retries"] == 1
    assert tool_stats["fallbacks"] == 1


def test_metrics_reset():
    """Test la reinitialisation des metriques."""
    metrics = MetricsCollector(enabled=True)
    metrics.record_call("generate", tokens_input=100)
    assert metrics.get_summary()["total_calls"] == 1

    metrics.reset()
    assert metrics.get_summary()["total_calls"] == 0
    assert len(metrics.get_summary()["tools"]) == 0
