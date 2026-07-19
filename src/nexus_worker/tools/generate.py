"""Outil MCP : worker_generate_code

Génère du code neuf en déléguant au Worker via le provider configuré.
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
from nexus_worker.utils.files import write_file_safe


async def worker_generate_code(
    instruction: str,
    provider: WorkerProvider,
    prompt_engine: PromptEngine,
    metrics: MetricsCollector,
    call_tracker: Any,
    allowed_paths: list[Path] | None = None,
    max_retries: int = 3,
    max_tokens: int = 4096,
    target_path: str = "",
    language: str = "",
    context: str = "",
    auto_save: bool = False,
) -> str:
    """Génère du code en déléguant au modèle Worker.

    Args:
        instruction: Consigne technique détaillée pour la génération.
        provider: Adaptateur du fournisseur Worker.
        prompt_engine: Moteur de prompts pour charger le template.
        metrics: Collecteur de métriques.
        call_tracker: Tracker anti-boucle infinie.
        allowed_paths: Répertoires autorisés (pour auto_save).
        max_retries: Nombre max de tentatives.
        max_tokens: Limite de tokens de sortie.
        target_path: Chemin du fichier cible (contexte et sauvegarde).
        language: Langage de programmation cible.
        context: Contexte additionnel (imports, conventions, types).
        auto_save: Si True, enregistre directement le code dans target_path.

    Returns:
        Résultat JSON stringifié avec le code généré ou l'erreur.
    """
    tool_name = "worker_generate_code"

    # Protection anti-boucle
    call_tracker.check_and_record(tool_name)

    # Construire le prompt système
    system_prompt = prompt_engine.get_system_prompt(
        "generate",
        language=language or "non spécifié (infère depuis l'instruction)",
        context=context or "Aucun contexte additionnel fourni.",
    )

    # Construire le prompt utilisateur
    user_prompt = instruction
    if target_path:
        user_prompt = f"Fichier cible: {target_path}\n\n{user_prompt}"

    try:
        response = await with_retry(
            lambda: provider.complete(system_prompt, user_prompt, max_tokens=max_tokens),
            max_retries=max_retries,
        )

        # Logger et enregistrer les métriques
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

        result_dict = {
            "status": "success",
            "code": response.content,
            "language": language or "inferred",
            "tokens_used": {
                "input": response.tokens_input,
                "output": response.tokens_output,
            },
            "model": response.model,
        }

        # Sauvegarde automatique si demandée
        if auto_save and target_path:
            try:
                lines_written = write_file_safe(
                    target_path,
                    response.content,
                    allowed_paths=allowed_paths
                )
                result_dict["saved"] = True
                result_dict["saved_path"] = target_path
                result_dict["lines_written"] = lines_written
            except (PermissionError, OSError) as e:
                result_dict["saved"] = False
                result_dict["save_error"] = str(e)

        return json.dumps(result_dict, ensure_ascii=False)

    except WorkerError as e:
        metrics.record_call(tool_name=tool_name, success=False)
        error_response = format_error_for_brain(e, tool_name, instruction)
        return json.dumps(error_response, ensure_ascii=False)
