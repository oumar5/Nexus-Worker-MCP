"""Adaptateur pour Ollama et les modèles locaux.

Compatible avec Ollama, LM Studio, et tout serveur local
exposant une API REST de type chat/completions.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from nexus_worker.config import WorkerConfig
from nexus_worker.core.errors import (
    WorkerTimeoutError,
    WorkerUnavailableError,
)
from nexus_worker.providers.base import WorkerResponse


class OllamaAdapter:
    """Adaptateur pour les modèles locaux via Ollama.

    Utilise httpx directement (pas de SDK dédié) car l'API
    Ollama est une API REST simple.
    """

    def __init__(self, config: WorkerConfig) -> None:
        """Initialise l'adaptateur Ollama.

        Args:
            config: Configuration du worker avec URL locale et modèle.
        """
        self._config = config
        self._model = config.model_name
        self._base_url = config.api_base_url.rstrip("/")
        self._timeout = config.timeout_seconds

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Envoie un prompt au modèle Ollama local.

        Args:
            system_prompt: Instructions système pour le worker.
            user_prompt: La tâche à exécuter.
            max_tokens: Limite de tokens de sortie.
            temperature: Créativité du modèle.

        Returns:
            WorkerResponse standardisée.
        """
        start_time = time.time()
        url = f"{self._base_url}/api/chat"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise WorkerTimeoutError(f"Timeout Ollama: {e}") from e
        except httpx.ConnectError as e:
            raise WorkerUnavailableError(
                f"Ollama injoignable sur {self._base_url}. "
                f"Vérifiez que Ollama est lancé: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise WorkerUnavailableError(f"Erreur Ollama HTTP {e.response.status_code}: {e}") from e

        latency_ms = (time.time() - start_time) * 1000
        data = response.json()

        content = data.get("message", {}).get("content", "")

        # Ollama retourne les métriques dans les champs eval_count / prompt_eval_count
        tokens_input = data.get("prompt_eval_count", 0)
        tokens_output = data.get("eval_count", 0)

        return WorkerResponse(
            content=content,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model=data.get("model", self._model),
            latency_ms=round(latency_ms, 1),
            raw_response=data,
        )

    async def health_check(self) -> bool:
        """Vérifie que Ollama est joignable et que le modèle est disponible.

        Returns:
            True si Ollama répond et que le modèle est listé.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Vérifier que Ollama tourne
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()

                # Vérifier que le modèle est disponible
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self._model.split(":")[0]
                return any(model_base in m for m in models)
        except Exception:
            return False

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées de l'adaptateur.

        Returns:
            Dictionnaire avec provider, model et endpoint.
        """
        return {
            "provider": "ollama",
            "model": self._model,
            "endpoint": self._base_url,
            "mode": "local",
        }
