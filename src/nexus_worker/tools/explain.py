"""Outil MCP : worker_explain_code

Lit un fichier et demande au Worker une explication structurée.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_worker.core.cache import ResultCache
from nexus_worker.core.errors import WorkerError, format_error_for_brain, with_retry
from nexus_worker.core.logger import log_tool_call
from nexus_worker.core.metrics import MetricsCollector
from nexus_worker.prompts.engine import PromptEngine
from nexus_worker.providers.base import WorkerProvider
from nexus_worker.utils.files import read_file_safe


async def worker_explain_code(
    file_path: str,
    provider: WorkerProvider,
    prompt_engine: PromptEngine,
    metrics: MetricsCollector,
    call_tracker: Any,
    allowed_paths: list[Path] | None = None,
    max_retries: int = 3,
    max_tokens: int = 4096,
    focus: str = "",
    detail_level: str = "detailed",
    cache: ResultCache | None = None,
) -> str:
    """Explique le code d'un fichier en déléguant au Worker.

    Args:
        file_path: Chemin du fichier à expliquer.
        provider: Adaptateur du fournisseur Worker.
        prompt_engine: Moteur de prompts.
        metrics: Collecteur de métriques.
        call_tracker: Tracker anti-boucle.
        allowed_paths: Répertoires autorisés.
        max_retries: Nombre max de tentatives.
        max_tokens: Limite de tokens de sortie.
        focus: Classe, fonction ou section spécifique à cibler.
        detail_level: Niveau de détail (summary, detailed, line-by-line).
        cache: Cache de résultats optionnel.

    Returns:
        Résultat JSON stringifié avec l'explication ou l'erreur.
    """
    tool_name = "worker_explain_code"
    call_tracker.check_and_record(tool_name)

    # Lire le fichier
    try:
        content, total_lines = read_file_safe(file_path, allowed_paths=allowed_paths)
    except (FileNotFoundError, PermissionError, ValueError) as e:
        return json.dumps(
            {"status": "error", "error_type": "file_error", "message": str(e)},
            ensure_ascii=False,
        )

    # Construire les prompts
    system_prompt = prompt_engine.get_system_prompt(
        "explain",
        detail_level=detail_level,
    )

    user_prompt = f"Fichier: {file_path} ({total_lines} lignes)\n\n"
    if focus:
        user_prompt += f"Focus spécifique: {focus}\n\n"
    user_prompt += f"Code:\n{content}"

    # Vérifier le cache
    if cache:
        cache_key = ResultCache.make_key(content, user_prompt)
        cached = cache.get(cache_key)
        if cached:
            return cached

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

        result = json.dumps(
            {
                "status": "success",
                "explanation": response.content,
                "file_info": {"path": file_path, "total_lines": total_lines},
                "tokens_used": {
                    "input": response.tokens_input,
                    "output": response.tokens_output,
                },
                "model": response.model,
            },
            ensure_ascii=False,
        )

        if cache:
            cache.set(cache_key, result)

        return result

    except WorkerError as e:
        metrics.record_call(tool_name=tool_name, success=False)
        error_response = format_error_for_brain(e, tool_name, f"explain {file_path}")
        return json.dumps(error_response, ensure_ascii=False)
