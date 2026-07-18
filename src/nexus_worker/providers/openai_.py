"""Adaptateur pour les APIs compatibles OpenAI.

Compatible avec : OpenAI, Azure OpenAI, Groq, Together AI, vLLM,
et tout endpoint respectant le format OpenAI Chat Completions.
"""

from __future__ import annotations

import time
from typing import Any

from openai import AsyncAzureOpenAI, AsyncOpenAI

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import (
    WorkerAuthError,
    WorkerRateLimitError,
    WorkerTimeoutError,
    WorkerUnavailableError,
)
from nexus_worker.providers.base import WorkerResponse


class OpenAIAdapter:
    """Adaptateur pour OpenAI et les APIs compatibles (Azure, Groq, etc.).

    Détecte automatiquement si l'endpoint est Azure OpenAI grâce à
    la présence de la variable api_version.
    """

    def __init__(self, config: WorkerConfig) -> None:
        """Initialise l'adaptateur OpenAI.

        Args:
            config: Configuration du worker avec endpoint, clé et modèle.
        """
        self._config = config
        self._model = config.model_name

        if config.api_version:
            # Mode Azure OpenAI (avec support APIM)
            is_apim = "azure-api.net" in config.api_base_url
            
            if is_apim:
                # L'API Gateway n'attend pas de segment /openai/, on forge l'URL avec AsyncOpenAI standard
                base_url = f"{config.api_base_url.rstrip('/')}/deployments/{self._model}"
                self._client = AsyncOpenAI(
                    base_url=base_url,
                    api_key=config.api_key,
                    timeout=config.timeout_seconds,
                    default_headers={"Ocp-Apim-Subscription-Key": config.api_key},
                    default_query={"api-version": config.api_version},
                )
            else:
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=config.api_base_url,
                    api_key=config.api_key,
                    api_version=config.api_version,
                    timeout=config.timeout_seconds,
                )
        else:
            # Mode OpenAI standard / Compatible
            self._client = AsyncOpenAI(
                base_url=config.api_base_url,
                api_key=config.api_key,
                timeout=config.timeout_seconds,
            )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Envoie un prompt au modèle et retourne la réponse.

        Args:
            system_prompt: Instructions système pour le worker.
            user_prompt: La tâche à exécuter.
            max_tokens: Limite de tokens de sortie.
            temperature: Créativité du modèle.

        Returns:
            WorkerResponse standardisée.

        Raises:
            WorkerAuthError: Si la clé API est invalide.
            WorkerRateLimitError: Si le quota est dépassé.
            WorkerTimeoutError: Si la requête timeout.
            WorkerUnavailableError: Si l'API est injoignable.
        """
        start_time = time.time()

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            self._handle_error(e)

        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""
        usage = response.usage

        return WorkerResponse(
            content=content,
            tokens_input=usage.prompt_tokens if usage else 0,
            tokens_output=usage.completion_tokens if usage else 0,
            model=response.model or self._model,
            latency_ms=round(latency_ms, 1),
            raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
        )

    async def health_check(self) -> bool:
        """Vérifie la connexion en envoyant un prompt minimal.

        Returns:
            True si le modèle répond correctement.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return bool(response.choices)
        except Exception:
            return False

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées de l'adaptateur.

        Returns:
            Dictionnaire avec provider, model, endpoint, et mode (azure ou standard).
        """
        is_azure = self._config.api_version is not None
        return {
            "provider": "openai",
            "model": self._model,
            "endpoint": self._config.api_base_url,
            "mode": "azure" if is_azure else "standard",
        }

    def _handle_error(self, error: Exception) -> None:
        """Convertit les erreurs OpenAI en erreurs Worker typées.

        Args:
            error: L'exception OpenAI originale.

        Raises:
            WorkerAuthError: Pour les erreurs 401/403.
            WorkerRateLimitError: Pour les erreurs 429.
            WorkerTimeoutError: Pour les timeouts.
            WorkerUnavailableError: Pour les erreurs de connexion.
        """
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )

        if isinstance(error, AuthenticationError):
            raise WorkerAuthError(f"Clé API invalide: {error}") from error
        elif isinstance(error, RateLimitError):
            raise WorkerRateLimitError(f"Quota dépassé: {error}") from error
        elif isinstance(error, APITimeoutError):
            raise WorkerTimeoutError(f"Timeout: {error}") from error
        elif isinstance(error, APIConnectionError):
            raise WorkerUnavailableError(f"Connexion impossible: {error}") from error
        else:
            raise WorkerUnavailableError(f"Erreur inattendue: {error}") from error
