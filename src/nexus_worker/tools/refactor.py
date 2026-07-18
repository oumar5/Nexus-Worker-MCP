"""Outil MCP : worker_refactor_code

Lit un fichier, envoie le code + instructions de refactoring au Worker,
et retourne le code modifié.
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


async def worker_refactor_code(
    file_path: str,
    instruction: str,
    provider: WorkerProvider,
    prompt_engine: PromptEngine,
    metrics: MetricsCollector,
    call_tracker: Any,
    allowed_paths: list[Path] | None = None,
    max_retries: int = 3,
    max_tokens: int = 4096,
    target_lines: str = "",
    context: str = "",
) -> str:
    """Refactore du code en déléguant au Worker.

    Args:
        file_path: Chemin du fichier à refactorer.
        instruction: Instructions de refactoring détaillées.
        provider: Adaptateur du fournisseur Worker.
        prompt_engine: Moteur de prompts.
        metrics: Collecteur de métriques.
        call_tracker: Tracker anti-boucle.
        allowed_paths: Répertoires autorisés.
        max_retries: Nombre max de tentatives.
        max_tokens: Limite de tokens de sortie.
        target_lines: Plage de lignes ciblées (ex: "42-98").
        context: Contexte additionnel (patterns, types).

    Returns:
        Résultat JSON stringifié avec le code refactoré ou l'erreur.
    """
    tool_name = "worker_refactor_code"
    call_tracker.check_and_record(tool_name)

    # Lire le fichier
    try:
        content, total_lines = read_file_safe(
            file_path,
            allowed_paths=allowed_paths,
            focus_lines=target_lines or None,
        )
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return json.dumps(
            {"status": "error", "error_type": "file_error", "message": str(e)},
            ensure_ascii=False,
        )

    # Construire les prompts
    system_prompt = prompt_engine.get_system_prompt(
        "refactor",
        context=context or "Aucun contexte additionnel.",
    )

    user_prompt = f"Fichier: {file_path}\n"
    if target_lines:
        user_prompt += f"Lignes ciblées: {target_lines}\n"
    user_prompt += f"\nInstruction de refactoring:\n{instruction}\n\nCode:\n{content}"

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
        )

        return json.dumps(
            {
                "status": "success",
                "refactored_code": response.content,
                "file_info": {"path": file_path, "total_lines": total_lines},
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
        error_response = format_error_for_brain(e, tool_name, instruction)
        return json.dumps(error_response, ensure_ascii=False)
