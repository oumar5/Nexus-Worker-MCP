"""Gestion d'erreurs, retry avec backoff, et protection anti-boucle.

Ce module fournit les classes d'erreurs custom, le mécanisme de retry
avec backoff exponentiel, et le CallTracker anti-boucle infinie.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from nexus_worker.core.logger import get_logger

T = TypeVar("T")


# ─── Classes d'erreurs custom ────────────────────────────────────────────────


class WorkerError(Exception):
    """Erreur de base pour toutes les erreurs liées au Worker."""

    def __init__(self, message: str, error_type: str = "worker_error") -> None:
        self.error_type = error_type
        super().__init__(message)


class WorkerTimeoutError(WorkerError):
    """Le Worker n'a pas répondu dans le délai imparti."""

    def __init__(self, message: str = "Worker timeout") -> None:
        super().__init__(message, error_type="timeout")


class WorkerAuthError(WorkerError):
    """Erreur d'authentification (clé API invalide ou expirée)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, error_type="auth_error")


class WorkerRateLimitError(WorkerError):
    """Le quota d'appels API est dépassé."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, error_type="rate_limit")


class WorkerUnavailableError(WorkerError):
    """Le Worker est injoignable."""

    def __init__(self, message: str = "Worker unavailable") -> None:
        super().__init__(message, error_type="unavailable")


class ToolRateLimitedError(WorkerError):
    """L'outil a été appelé trop de fois (protection anti-boucle)."""

    def __init__(self, tool_name: str, max_calls: int, window_seconds: int) -> None:
        message = (
            f"L'outil {tool_name} a été appelé {max_calls} fois en {window_seconds}s. "
            f"Pour éviter une boucle de correction infinie, l'outil est temporairement "
            f"désactivé. Essaie de résoudre le problème différemment ou demande à "
            f"l'utilisateur d'intervenir."
        )
        self.tool_name = tool_name
        super().__init__(message, error_type="tool_rate_limited")


# ─── Erreurs retryables vs fatales ───────────────────────────────────────────

RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    WorkerTimeoutError,
    WorkerRateLimitError,
    WorkerUnavailableError,
    ConnectionError,
    TimeoutError,
    OSError,
)

FATAL_ERRORS: tuple[type[Exception], ...] = (WorkerAuthError,)


# ─── Retry avec backoff exponentiel ──────────────────────────────────────────


async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
) -> T:
    """Exécute une fonction async avec retry et backoff exponentiel.

    Args:
        func: Fonction async à exécuter.
        max_retries: Nombre maximum de tentatives après le premier échec.
        base_delay: Délai initial entre les tentatives (en secondes).
        max_delay: Délai maximum entre les tentatives (en secondes).
        exponential_base: Multiplicateur du délai à chaque tentative.

    Returns:
        Le résultat de la fonction si elle réussit.

    Raises:
        WorkerError: Si toutes les tentatives échouent.
        WorkerAuthError: Immédiatement si erreur d'authentification (pas de retry).
    """
    logger = get_logger()
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()

        except FATAL_ERRORS as e:
            # Erreurs fatales : pas de retry
            logger.error(
                f"Erreur fatale (pas de retry): {e}",
                extra={
                    "event": "fatal_error",
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                },
            )
            raise

        except RETRYABLE_ERRORS as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(
                    f"Échec après {max_retries + 1} tentatives: {e}",
                    extra={
                        "event": "retry_exhausted",
                        "attempt": attempt + 1,
                        "error_type": type(e).__name__,
                    },
                )
                break

            delay = min(base_delay * (exponential_base**attempt), max_delay)
            logger.warning(
                f"Tentative {attempt + 1} échouée, retry dans {delay:.1f}s: {e}",
                extra={
                    "event": "retry",
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                },
            )
            await asyncio.sleep(delay)

        except Exception as e:
            # Erreurs inattendues : pas de retry
            logger.error(
                f"Erreur inattendue: {e}",
                extra={
                    "event": "unexpected_error",
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                },
            )
            raise WorkerError(str(e), error_type="unexpected") from e

    raise WorkerError(
        f"Échec après {max_retries + 1} tentatives: {last_exception}",
        error_type="retry_exhausted",
    )


# ─── Protection anti-boucle infinie ──────────────────────────────────────────


class CallTracker:
    """Suit les appels d'outils pour détecter et bloquer les boucles infinies.

    Limite le nombre d'appels par outil sur une fenêtre de temps glissante.
    """

    def __init__(
        self,
        max_calls_per_tool: int = 5,
        window_seconds: int = 300,
    ) -> None:
        """Initialise le tracker.

        Args:
            max_calls_per_tool: Nombre maximum d'appels autorisés par outil.
            window_seconds: Taille de la fenêtre glissante en secondes.
        """
        self.max_calls = max_calls_per_tool
        self.window = window_seconds
        self._history: dict[str, list[float]] = {}

    def check_and_record(self, tool_name: str) -> None:
        """Vérifie si l'appel est autorisé et l'enregistre.

        Args:
            tool_name: Nom de l'outil MCP.

        Raises:
            ToolRateLimitedError: Si la limite d'appels est atteinte.
        """
        now = time.time()
        calls = self._history.get(tool_name, [])

        # Nettoyer les appels hors fenêtre
        calls = [t for t in calls if now - t < self.window]

        if len(calls) >= self.max_calls:
            raise ToolRateLimitedError(tool_name, self.max_calls, self.window)

        calls.append(now)
        self._history[tool_name] = calls

    def reset(self, tool_name: str | None = None) -> None:
        """Réinitialise l'historique des appels.

        Args:
            tool_name: Si fourni, réinitialise uniquement cet outil.
                       Si None, réinitialise tout.
        """
        if tool_name:
            self._history.pop(tool_name, None)
        else:
            self._history.clear()


# ─── Formatage des erreurs pour le Cerveau ───────────────────────────────────


def format_error_for_brain(
    error: WorkerError,
    tool_name: str,
    original_instruction: str = "",
) -> dict[str, Any]:
    """Formate une erreur en réponse structurée compréhensible par le Cerveau.

    Args:
        error: L'erreur Worker survenue.
        tool_name: Nom de l'outil qui a échoué.
        original_instruction: L'instruction originale de l'appel.

    Returns:
        Dictionnaire avec le statut, le type d'erreur, le message et la suggestion.
    """
    suggestions = {
        "timeout": (
            "Le worker n'a pas répondu à temps. "
            "Tu peux retenter ou demander à l'utilisateur "
            "de vérifier la connexion."
        ),
        "auth_error": (
            "La clé API du worker est invalide. "
            "Demande à l'utilisateur de vérifier "
            "WORKER_API_KEY dans le .env."
        ),
        "rate_limit": (
            "Le quota d'appels API est dépassé. "
            "Attends quelques instants ou demande à "
            "l'utilisateur de vérifier son quota."
        ),
        "unavailable": (
            "Le worker est injoignable. Tu peux tenter de "
            "réaliser la tâche toi-même ou demander à "
            "l'utilisateur de vérifier la configuration."
        ),
        "tool_rate_limited": (
            "Cet outil a été appelé trop de fois. Essaie une approche différente."
        ),
        "retry_exhausted": (
            "Le worker a échoué après plusieurs tentatives. "
            "Tu peux tenter de réaliser la tâche toi-même."
        ),
    }

    return {
        "status": "error",
        "error_type": error.error_type,
        "message": str(error),
        "suggestion": suggestions.get(error.error_type, "Une erreur inattendue est survenue."),
        "attempted_tool": tool_name,
        "original_instruction": original_instruction,
    }
