"""Adaptateur pour l'API Anthropic Claude.

Gère le format Messages API spécifique d'Anthropic où le
prompt système est passé séparément des messages.
"""

from __future__ import annotations

import time
from typing import Any

from anthropic import AsyncAnthropic

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import (
    WorkerAuthError,
    WorkerRateLimitError,
    WorkerTimeoutError,
    WorkerUnavailableError,
)
from nexus_worker.providers.base import WorkerResponse


class AnthropicAdapter:
    """Adaptateur pour l'API Anthropic (Claude).

    Utilise le SDK officiel Anthropic et gère la séparation
    du prompt système (spécificité Anthropic).
    """

    def __init__(self, config: WorkerConfig) -> None:
        """Initialise l'adaptateur Anthropic.

        Args:
            config: Configuration du worker avec endpoint, clé et modèle.
        """
        self._config = config
        self._model = config.model_name
        self._client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.api_base_url if config.api_base_url != "https://api.openai.com/v1" else None,
            timeout=config.timeout_seconds,
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Envoie un prompt au modèle Claude et retourne la réponse.

        Args:
            system_prompt: Instructions système (passé via le paramètre 'system').
            user_prompt: La tâche à exécuter.
            max_tokens: Limite de tokens de sortie.
            temperature: Créativité du modèle.

        Returns:
            WorkerResponse standardisée.
        """
        start_time = time.time()

        try:
            response = await self._client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            self._handle_error(e)

        latency_ms = (time.time() - start_time) * 1000

        # Extraire le contenu textuel de la réponse
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return WorkerResponse(
            content=content,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model,
            latency_ms=round(latency_ms, 1),
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    async def health_check(self) -> bool:
        """Vérifie la connexion en envoyant un prompt minimal.

        Returns:
            True si le modèle répond correctement.
        """
        try:
            response = await self._client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.content)
        except Exception:
            return False

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées de l'adaptateur.

        Returns:
            Dictionnaire avec provider, model et endpoint.
        """
        return {
            "provider": "anthropic",
            "model": self._model,
            "endpoint": self._config.api_base_url,
        }

    def _handle_error(self, error: Exception) -> None:
        """Convertit les erreurs Anthropic en erreurs Worker typées.

        Args:
            error: L'exception Anthropic originale.
        """
        from anthropic import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise WorkerAuthError(f"Clé API Anthropic invalide: {error}") from error
        elif isinstance(error, RateLimitError):
            raise WorkerRateLimitError(f"Quota Anthropic dépassé: {error}") from error
        elif isinstance(error, APITimeoutError):
            raise WorkerTimeoutError(f"Timeout Anthropic: {error}") from error
        elif isinstance(error, APIConnectionError):
            raise WorkerUnavailableError(f"Connexion Anthropic impossible: {error}") from error
        else:
            raise WorkerUnavailableError(f"Erreur Anthropic inattendue: {error}") from error
