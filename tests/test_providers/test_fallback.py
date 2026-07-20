"""Tests pour le CompositeProvider (bascule automatique sur fallback)."""

from __future__ import annotations

from typing import Any

import pytest

from nexus_worker.core.errors import WorkerUnavailableError
from nexus_worker.providers.base import WorkerResponse
from nexus_worker.providers.fallback import CompositeProvider


class _StubProvider:
    """Provider factice pour les tests.

    Peut soit renvoyer une réponse, soit lever une erreur, selon `should_fail`.
    Compte le nombre d'appels reçus.
    """

    def __init__(self, name: str, should_fail: bool = False, healthy: bool = True) -> None:
        self.name = name
        self.should_fail = should_fail
        self.healthy = healthy
        self.complete_calls = 0

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        self.complete_calls += 1
        if self.should_fail:
            raise WorkerUnavailableError(f"{self.name} indisponible")
        return WorkerResponse(content=f"réponse de {self.name}", model=self.name)

    async def health_check(self) -> bool:
        return self.healthy

    def get_info(self) -> dict[str, Any]:
        return {"provider": self.name, "model": self.name}


class TestCompositeProvider:
    """Tests de la logique de bascule primaire → fallback."""

    @pytest.mark.asyncio
    async def test_uses_primary_when_it_succeeds(self) -> None:
        """Le fallback n'est pas appelé si le principal réussit."""
        primary = _StubProvider("primary")
        fallback = _StubProvider("fallback")
        composite = CompositeProvider(primary, fallback)

        response = await composite.complete("sys", "user")

        assert response.content == "réponse de primary"
        assert primary.complete_calls == 1
        assert fallback.complete_calls == 0

    @pytest.mark.asyncio
    async def test_switches_to_fallback_on_primary_failure(self) -> None:
        """Le fallback prend le relais si le principal lève une WorkerError."""
        primary = _StubProvider("primary", should_fail=True)
        fallback = _StubProvider("fallback")
        composite = CompositeProvider(primary, fallback)

        response = await composite.complete("sys", "user")

        assert response.content == "réponse de fallback"
        assert primary.complete_calls == 1
        assert fallback.complete_calls == 1

    @pytest.mark.asyncio
    async def test_raises_when_both_fail(self) -> None:
        """L'erreur du fallback est propagée si les deux échouent."""
        primary = _StubProvider("primary", should_fail=True)
        fallback = _StubProvider("fallback", should_fail=True)
        composite = CompositeProvider(primary, fallback)

        with pytest.raises(WorkerUnavailableError, match="fallback indisponible"):
            await composite.complete("sys", "user")

    @pytest.mark.asyncio
    async def test_health_check_true_if_primary_healthy(self) -> None:
        """health_check renvoie True dès que le principal est sain."""
        primary = _StubProvider("primary", healthy=True)
        fallback = _StubProvider("fallback", healthy=False)
        composite = CompositeProvider(primary, fallback)

        assert await composite.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_falls_back_when_primary_unhealthy(self) -> None:
        """health_check interroge le fallback si le principal est indisponible."""
        primary = _StubProvider("primary", healthy=False)
        fallback = _StubProvider("fallback", healthy=True)
        composite = CompositeProvider(primary, fallback)

        assert await composite.health_check() is True

    def test_get_info_includes_fallback(self) -> None:
        """get_info expose les infos du principal et du fallback."""
        primary = _StubProvider("primary")
        fallback = _StubProvider("fallback")
        composite = CompositeProvider(primary, fallback)

        info = composite.get_info()

        assert info["provider"] == "primary"
        assert info["fallback"]["provider"] == "fallback"
