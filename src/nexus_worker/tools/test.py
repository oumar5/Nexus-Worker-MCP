"""Outil MCP : worker_generate_tests

Lit un fichier source et délègue la génération de tests au Worker.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_worker.core.errors import WorkerError, format_error_for_brain, with_retry
from nexus_worker.core.logger import log_tool_call
from nexus_worker.core.metrics import MetricsCollector
from nexus_worker.prompts.engine import PromptEngine
from nexus_worker.providers.base import WorkerProvider
from nexus_worker.utils.files import read_file_safe


async def worker_generate_tests(
    file_path: str,
    provider: WorkerProvider,
    prompt_engine: PromptEngine,
    metrics: MetricsCollector,
    call_tracker: Any,
    allowed_paths: list[Path] | None = None,
    max_retries: int = 3,
    max_tokens: int = 4096,
    test_framework: str = "pytest",
    focus_functions: str = "",
    coverage_level: str = "thorough",
) -> str:
    """Génère des tests en déléguant au Worker.

    Args:
        file_path: Chemin du fichier source à tester.
        provider: Adaptateur du fournisseur Worker.
        prompt_engine: Moteur de prompts.
        metrics: Collecteur de métriques.
        call_tracker: Tracker anti-boucle.
        allowed_paths: Répertoires autorisés.
        max_retries: Nombre max de tentatives.
        max_tokens: Limite de tokens de sortie.
        test_framework: Framework de test (pytest, jest, etc.).
        focus_functions: Fonctions spécifiques à tester (séparées par virgules).
        coverage_level: Niveau de couverture (basic, thorough, exhaustive).

    Returns:
        Résultat JSON stringifié avec les tests ou l'erreur.
    """
    tool_name = "worker_generate_tests"
    call_tracker.check_and_record(tool_name)

    # Lire le fichier source
    try:
        content, total_lines = read_file_safe(file_path, allowed_paths=allowed_paths)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return json.dumps(
            {"status": "error", "error_type": "file_error", "message": str(e)},
            ensure_ascii=False,
        )

    # Construire les prompts
    source_file_name = Path(file_path).name
    system_prompt = prompt_engine.get_system_prompt(
        "test",
        test_framework=test_framework,
        coverage_level=coverage_level,
        source_file=source_file_name,
    )

    user_prompt = f"Fichier source à tester: {file_path} ({total_lines} lignes)\n"
    user_prompt += f"Framework de test: {test_framework}\n"
    user_prompt += f"Niveau de couverture: {coverage_level}\n"
    if focus_functions:
        user_prompt += f"Fonctions spécifiques à tester: {focus_functions}\n"
    user_prompt += f"\nCode source:\n{content}"

    try:
        response = await with_retry(
            lambda: provider.complete(system_prompt, user_prompt, max_tokens=max_tokens),
            max_retries=max_retries,
        )

        provider_info = provider.get_info()
        log_tool_call(
            tool=tool_name,
            provider=provider_info.get("provider", "unknown"),
            model=response.model,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            latency_ms=response.latency_ms,
            status="success",
        )
        metrics.record_call(
            tool_name=tool_name,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            latency_ms=response.latency_ms,
            success=True,
            was_retry=response.retry_count > 0,
            was_fallback=response.used_fallback,
        )

        return json.dumps(
            {
                "status": "success",
                "test_code": response.content,
                "source_file": file_path,
                "test_framework": test_framework,
                "coverage_level": coverage_level,
                "tokens_used": {
                    "input": response.tokens_input,
                    "output": response.tokens_output,
                },
                "model": response.model,
            },
            ensure_ascii=False,
        )

    except WorkerError as e:
        metrics.record_call(tool_name=tool_name, success=False)
        error_response = format_error_for_brain(e, tool_name, f"generate tests for {file_path}")
        return json.dumps(error_response, ensure_ascii=False)
