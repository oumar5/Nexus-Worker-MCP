"""Provider composite avec bascule automatique vers un fallback.

Enveloppe un provider principal et un provider de secours. Si le principal
échoue (indisponible, timeout, rate limit, auth), la requête est automatiquement
retentée sur le fallback. Transparent : implémente le même Protocol WorkerProvider,
donc aucun outil n'a besoin d'être modifié.
"""

from __future__ import annotations

from typing import Any

from nexus_worker.core.errors import WorkerError
from nexus_worker.core.logger import get_logger
from nexus_worker.providers.base import WorkerProvider, WorkerResponse


class CompositeProvider:
    """Provider qui bascule sur un fallback si le principal échoue.

    Respecte le Protocol WorkerProvider : peut être utilisé partout où un
    WorkerProvider est attendu.

    Attributes:
        primary: Provider principal, tenté en premier.
        fallback: Provider de secours, utilisé si le principal lève une WorkerError.
    """

    def __init__(self, primary: WorkerProvider, fallback: WorkerProvider) -> None:
        """Initialise le provider composite.

        Args:
            primary: Provider principal (tenté en premier).
            fallback: Provider de secours (utilisé en cas d'échec du principal).
        """
        self.primary = primary
        self.fallback = fallback
        self._logger = get_logger()

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Tente le provider principal, puis bascule sur le fallback si besoin.

        Args:
            system_prompt: Instructions système pour le worker.
            user_prompt: La tâche à exécuter.
            max_tokens: Limite de tokens de sortie.
            temperature: Créativité du modèle.

        Returns:
            WorkerResponse du provider qui a réussi.

        Raises:
            WorkerError: Si le principal ET le fallback échouent (l'erreur du
                fallback est propagée).
        """
        try:
            return await self.primary.complete(
                system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature
            )
        except WorkerError as primary_error:
            fb_info = self.fallback.get_info()
            self._logger.warning(
                f"Provider principal en échec ({primary_error.error_type}), "
                f"bascule sur le fallback: {fb_info.get('provider')}/{fb_info.get('model')}",
                extra={
                    "event": "fallback_switch",
                    "primary_error_type": primary_error.error_type,
                    "fallback_provider": fb_info.get("provider"),
                },
            )
            return await self.fallback.complete(
                system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature
            )

    async def health_check(self) -> bool:
        """Vérifie qu'au moins un des deux providers est joignable.

        Returns:
            True si le principal OU le fallback répond.
        """
        if await self.primary.health_check():
            return True
        return await self.fallback.health_check()

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées, en signalant la présence d'un fallback.

        Returns:
            Métadonnées du provider principal, enrichies des infos du fallback.
        """
        info = dict(self.primary.get_info())
        info["fallback"] = self.fallback.get_info()
        return info
