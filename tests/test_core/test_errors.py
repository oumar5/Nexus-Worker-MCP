"""Tests pour la gestion d'erreurs, le retry et le CallTracker."""

from __future__ import annotations

import pytest

from nexus_worker.core.errors import (
    CallTracker,
    ToolRateLimitedError,
    WorkerAuthError,
    WorkerError,
    WorkerTimeoutError,
    WorkerUnavailableError,
    format_error_for_brain,
    with_retry,
)


class TestWithRetry:
    """Tests pour le mécanisme de retry avec backoff."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        """Vérifie qu'un appel réussi ne déclenche pas de retry."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await with_retry(success_func, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """Vérifie que les TimeoutError déclenchent un retry."""
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WorkerTimeoutError("timeout")
            return "ok"

        result = await with_retry(fail_then_succeed, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self) -> None:
        """Vérifie que les AuthError ne déclenchent PAS de retry."""
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise WorkerAuthError("bad key")

        with pytest.raises(WorkerAuthError):
            await with_retry(auth_fail, max_retries=3, base_delay=0.01)

        assert call_count == 1  # Pas de retry

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self) -> None:
        """Vérifie qu'un échec total après tous les retries lève une WorkerError."""
        async def always_fail():
            raise WorkerUnavailableError("down")

        with pytest.raises(WorkerError, match="Échec après"):
            await with_retry(always_fail, max_retries=2, base_delay=0.01)


class TestCallTracker:
    """Tests pour la protection anti-boucle infinie."""

    def test_allows_calls_under_limit(self) -> None:
        """Vérifie que les appels sous la limite sont autorisés."""
        tracker = CallTracker(max_calls_per_tool=3, window_seconds=300)

        # 3 appels devraient passer
        for _ in range(3):
            tracker.check_and_record("test_tool")

    def test_blocks_calls_over_limit(self) -> None:
        """Vérifie que les appels au-dessus de la limite sont bloqués."""
        tracker = CallTracker(max_calls_per_tool=3, window_seconds=300)

        for _ in range(3):
            tracker.check_and_record("test_tool")

        with pytest.raises(ToolRateLimitedError):
            tracker.check_and_record("test_tool")

    def test_different_tools_tracked_separately(self) -> None:
        """Vérifie que chaque outil a son propre compteur."""
        tracker = CallTracker(max_calls_per_tool=2, window_seconds=300)

        tracker.check_and_record("tool_a")
        tracker.check_and_record("tool_a")

        # tool_b devrait encore marcher
        tracker.check_and_record("tool_b")

        # tool_a devrait être bloqué
        with pytest.raises(ToolRateLimitedError):
            tracker.check_and_record("tool_a")

    def test_reset_clears_history(self) -> None:
        """Vérifie que reset permet de réutiliser un outil bloqué."""
        tracker = CallTracker(max_calls_per_tool=1, window_seconds=300)

        tracker.check_and_record("test_tool")

        with pytest.raises(ToolRateLimitedError):
            tracker.check_and_record("test_tool")

        tracker.reset("test_tool")
        tracker.check_and_record("test_tool")  # Devrait passer


class TestFormatErrorForBrain:
    """Tests pour le formatage d'erreurs destinées au Cerveau."""

    def test_timeout_error_format(self) -> None:
        """Vérifie le format d'une erreur timeout."""
        error = WorkerTimeoutError("took too long")
        result = format_error_for_brain(error, "worker_generate_code", "test instruction")

        assert result["status"] == "error"
        assert result["error_type"] == "timeout"
        assert "suggestion" in result
        assert result["attempted_tool"] == "worker_generate_code"
        assert result["original_instruction"] == "test instruction"

    def test_auth_error_format(self) -> None:
        """Vérifie le format d'une erreur d'authentification."""
        error = WorkerAuthError("invalid key")
        result = format_error_for_brain(error, "worker_analyze_file")

        assert result["error_type"] == "auth_error"
        assert "WORKER_API_KEY" in result["suggestion"]
