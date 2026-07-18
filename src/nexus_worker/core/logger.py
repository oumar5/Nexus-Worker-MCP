"""Logger structuré pour Nexus-Worker-MCP.

Fournit un logging JSON structuré pour tracer tous les appels d'outils,
les retries, les fallbacks et les erreurs.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Formatter qui produit des logs JSON structurés."""

    def format(self, record: logging.LogRecord) -> str:
        """Formate un LogRecord en JSON structuré.

        Args:
            record: Le LogRecord à formater.

        Returns:
            Ligne JSON contenant les champs structurés.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Ajouter les champs extra s'ils existent
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "tool"):
            log_entry["tool"] = record.tool
        if hasattr(record, "provider"):
            log_entry["provider"] = record.provider
        if hasattr(record, "model"):
            log_entry["model"] = record.model
        if hasattr(record, "tokens_input"):
            log_entry["tokens_input"] = record.tokens_input
        if hasattr(record, "tokens_output"):
            log_entry["tokens_output"] = record.tokens_output
        if hasattr(record, "latency_ms"):
            log_entry["latency_ms"] = record.latency_ms
        if hasattr(record, "status"):
            log_entry["status"] = record.status
        if hasattr(record, "attempt"):
            log_entry["attempt"] = record.attempt
        if hasattr(record, "error_type"):
            log_entry["error_type"] = record.error_type

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """Configure et retourne le logger principal de Nexus-Worker-MCP.

    Args:
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Chemin du fichier de log. None pour désactiver l'écriture fichier.

    Returns:
        Le logger configuré.
    """
    logger = logging.getLogger("nexus_worker")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Éviter les doublons si appelé plusieurs fois
    if logger.handlers:
        return logger

    formatter = StructuredFormatter()

    # Handler stderr (pour ne pas polluer stdout utilisé par MCP stdio)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # Handler fichier (optionnel)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Retourne le logger Nexus-Worker-MCP existant.

    Returns:
        Le logger nommé 'nexus_worker'.
    """
    return logging.getLogger("nexus_worker")


def log_tool_call(
    tool: str,
    provider: str,
    model: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    latency_ms: float = 0,
    status: str = "success",
    attempt: int = 1,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    """Log un appel d'outil avec tous les champs structurés.

    Args:
        tool: Nom de l'outil MCP appelé.
        provider: Nom du fournisseur utilisé.
        model: Nom du modèle worker.
        tokens_input: Nombre de tokens d'entrée consommés.
        tokens_output: Nombre de tokens de sortie consommés.
        latency_ms: Temps de réponse en millisecondes.
        status: Résultat de l'appel (success, error, retried, fallback_used).
        attempt: Numéro de la tentative.
        error_type: Type d'erreur si applicable.
        error_message: Message d'erreur si applicable.
    """
    logger = get_logger()
    event = "tool_call" if status == "success" else "tool_call_failed"
    message = error_message or f"Tool call: {tool}"

    logger.log(
        logging.INFO if status == "success" else logging.ERROR,
        message,
        extra={
            "event": event,
            "tool": tool,
            "provider": provider,
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
            "status": status,
            "attempt": attempt,
            "error_type": error_type,
        },
    )
