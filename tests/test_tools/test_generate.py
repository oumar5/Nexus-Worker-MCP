"""Tests pour l'outil worker_generate_code."""

from __future__ import annotations

import json

import pytest

from nexus_worker.tools.generate import worker_generate_code


class TestWorkerGenerateCode:
    """Tests pour la génération de code via le Worker."""

    @pytest.mark.asyncio
    async def test_successful_generation(
        self, mock_provider, prompt_engine, metrics, call_tracker
    ) -> None:
        """Vérifie qu'une génération réussie retourne le code et les métriques."""
        result = await worker_generate_code(
            instruction="Crée une fonction hello world",
            provider=mock_provider,
            prompt_engine=prompt_engine,
            metrics=metrics,
            call_tracker=call_tracker,
        )

        data = json.loads(result)
        assert data["status"] == "success"
        assert "code" in data
        assert data["code"] == "def hello():\n    return 'Hello, World!'"
        assert "tokens_used" in data
        assert data["tokens_used"]["input"] == 100
        assert data["tokens_used"]["output"] == 50

    @pytest.mark.asyncio
    async def test_provider_called_with_correct_prompt(
        self, mock_provider, prompt_engine, metrics, call_tracker
    ) -> None:
        """Vérifie que le provider reçoit le bon prompt."""
        await worker_generate_code(
            instruction="Crée un composant React",
            provider=mock_provider,
            prompt_engine=prompt_engine,
            metrics=metrics,
            call_tracker=call_tracker,
            language="javascript",
            context="Utilise TypeScript",
        )

        mock_provider.complete.assert_called_once()
        call_args = mock_provider.complete.call_args
        system_prompt = call_args.args[0] if call_args.args else call_args.kwargs.get("system_prompt", "")
        assert "javascript" in system_prompt.lower() or "javascript" in str(call_args)

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(
        self, mock_provider, prompt_engine, metrics, call_tracker
    ) -> None:
        """Vérifie que les métriques sont enregistrées après un appel réussi."""
        await worker_generate_code(
            instruction="Test",
            provider=mock_provider,
            prompt_engine=prompt_engine,
            metrics=metrics,
            call_tracker=call_tracker,
        )

        summary = metrics.get_summary()
        assert summary["total_calls"] == 1
        assert "worker_generate_code" in summary["tools"]
        tool_metrics = summary["tools"]["worker_generate_code"]
        assert tool_metrics["calls"] == 1
        assert tool_metrics["tokens_input"] == 100
        assert tool_metrics["tokens_output"] == 50

    @pytest.mark.asyncio
    async def test_error_returns_structured_response(
        self, mock_provider, prompt_engine, metrics, call_tracker
    ) -> None:
        """Vérifie qu'une erreur retourne un JSON structuré pour le Cerveau."""
        from nexus_worker.core.errors import WorkerUnavailableError

        mock_provider.complete.side_effect = WorkerUnavailableError("API down")

        result = await worker_generate_code(
            instruction="Test",
            provider=mock_provider,
            prompt_engine=prompt_engine,
            metrics=metrics,
            call_tracker=call_tracker,
            max_retries=0,
        )

        data = json.loads(result)
        assert data["status"] == "error"
        assert "message" in data
        assert "suggestion" in data
        assert data["attempted_tool"] == "worker_generate_code"

    @pytest.mark.asyncio
    async def test_target_path_included_in_prompt(
        self, mock_provider, prompt_engine, metrics, call_tracker
    ) -> None:
        """Vérifie que le target_path est inclus dans le prompt utilisateur."""
        await worker_generate_code(
            instruction="Crée un service",
            provider=mock_provider,
            prompt_engine=prompt_engine,
            metrics=metrics,
            call_tracker=call_tracker,
            target_path="src/services/auth.py",
        )

        call_args = mock_provider.complete.call_args
        user_prompt = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("user_prompt", "")
        assert "src/services/auth.py" in user_prompt
