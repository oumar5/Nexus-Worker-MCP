"""Adaptateur pour l'API Google Gemini (via google-genai SDK).

Compatible avec les modèles Gemini via Google AI Studio et Vertex AI.
Suit le même contrat d'interface que les autres adaptateurs Nexus.
"""

from __future__ import annotations

import time
from typing import Any

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import (
    WorkerAuthError,
    WorkerRateLimitError,
    WorkerTimeoutError,
    WorkerUnavailableError,
)
from nexus_worker.providers.base import WorkerResponse


class GeminiAdapter:
    """Adaptateur pour l'API Google Gemini (google-genai SDK).

    Supporte les modèles Gemini 1.5 Flash, Gemini 1.5 Pro, Gemini 2.0 Flash, etc.
    La clé API doit être une clé Google AI Studio (GOOGLE_API_KEY).
    """

    def __init__(self, config: WorkerConfig) -> None:
        """Initialise l'adaptateur Gemini.

        Args:
            config: Configuration du worker avec clé API et nom de modèle.
        """
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as e:
            raise ImportError(
                "Le package 'google-genai' est requis pour utiliser le provider Gemini. "
                "Installez-le avec : pip install google-genai"
            ) from e

        self._genai = genai
        self._genai_types = genai_types
        self._config = config
        self._model = config.model_name

        # Initialiser le client Gemini
        self._client = genai.Client(api_key=config.api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Envoie un prompt au modèle Gemini et retourne la réponse.

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
        import asyncio

        start_time = time.time()

        config = self._genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        try:
            # Le SDK google-genai est synchrone : on l'exécute dans un thread
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=user_prompt,
                    config=config,
                ),
            )
        except Exception as e:
            self._handle_error(e)

        latency_ms = (time.time() - start_time) * 1000

        content = response.text or ""

        # Extraire les métriques d'usage
        tokens_input = 0
        tokens_output = 0
        if response.usage_metadata:
            tokens_input = response.usage_metadata.prompt_token_count or 0
            tokens_output = response.usage_metadata.candidates_token_count or 0

        return WorkerResponse(
            content=content,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model=self._model,
            latency_ms=round(latency_ms, 1),
            raw_response=None,
        )

    async def health_check(self) -> bool:
        """Vérifie la connexion en envoyant un prompt minimal.

        Returns:
            True si le modèle répond correctement.
        """
        import asyncio

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents="ping",
                    config=self._genai_types.GenerateContentConfig(max_output_tokens=5),
                ),
            )
            return bool(response.text)
        except Exception:
            return False

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées de l'adaptateur.

        Returns:
            Dictionnaire avec provider, model et endpoint.
        """
        return {
            "provider": "gemini",
            "model": self._model,
            "endpoint": "https://generativelanguage.googleapis.com",
        }

    def _handle_error(self, error: Exception) -> None:
        """Convertit les erreurs Google Gemini en erreurs Worker typées.

        Args:
            error: L'exception Gemini originale.

        Raises:
            WorkerAuthError: Pour les erreurs d'authentification.
            WorkerRateLimitError: Pour les erreurs de quota.
            WorkerTimeoutError: Pour les timeouts.
            WorkerUnavailableError: Pour les erreurs de connexion.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        if any(
            k in error_str
            for k in (
                "api_key",
                "permission",
                "401",
                "403",
            )
        ):
            raise WorkerAuthError(
                f"Clé API Gemini invalide: {error}",
            ) from error
        elif any(
            k in error_str
            for k in (
                "quota",
                "429",
                "rate",
            )
        ):
            raise WorkerRateLimitError(
                f"Quota Gemini dépassé: {error}",
            ) from error
        elif "timeout" in error_str or "deadline" in error_str:
            raise WorkerTimeoutError(
                f"Timeout Gemini: {error}",
            ) from error
        elif any(
            k in error_str
            for k in (
                "connection",
                "network",
                "unavailable",
            )
        ):
            raise WorkerUnavailableError(
                f"Connexion Gemini impossible: {error}",
            ) from error
        else:
            raise WorkerUnavailableError(
                f"Erreur Gemini inattendue ({error_type}): {error}",
            ) from error
