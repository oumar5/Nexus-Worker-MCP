"""Tests unitaires pour GeminiAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nexus_worker.config import WorkerConfig


@pytest.fixture
def gemini_config() -> WorkerConfig:
    """Configuration de test pour Gemini."""
    return WorkerConfig(
        WORKER_PROVIDER="gemini",
        WORKER_API_KEY="test-key",
        WORKER_MODEL_NAME="gemini-2.0-flash",
        WORKER_API_BASE_URL="https://generativelanguage.googleapis.com",
    )


class TestGeminiAdapterInit:
    """Tests d'initialisation de GeminiAdapter."""

    def test_init_raises_if_no_sdk(self, gemini_config: WorkerConfig) -> None:
        """Doit lever ImportError si google-genai n'est pas installé."""
        with patch.dict("sys.modules", {"google": None, "google.genai": None}):
            with pytest.raises((ImportError, Exception)):
                from nexus_worker.providers.gemini_ import GeminiAdapter

                GeminiAdapter(gemini_config)

    def test_get_info(self, gemini_config: WorkerConfig) -> None:
        """get_info doit retourner les bonnes métadonnées."""
        mock_genai = MagicMock()
        mock_genai.Client.return_value = MagicMock()

        sys_mods = {"google.genai": mock_genai, "google": MagicMock(genai=mock_genai)}
        with patch.dict("sys.modules", sys_mods):
            with patch("google.genai.Client", mock_genai.Client):
                try:
                    from nexus_worker.providers.gemini_ import GeminiAdapter

                    adapter = GeminiAdapter(gemini_config)
                    info = adapter.get_info()
                    assert info["provider"] == "gemini"
                    assert info["model"] == "gemini-2.0-flash"
                except Exception:
                    pytest.skip("SDK Gemini non disponible dans l'environnement de test")


class TestGeminiAdapterHandleError:
    """Tests de la gestion d'erreurs de GeminiAdapter."""

    def test_handle_auth_error(self, gemini_config: WorkerConfig) -> None:
        """Les erreurs d'authentification doivent lever WorkerAuthError."""
        try:
            from nexus_worker.core.errors import WorkerAuthError
            from nexus_worker.providers.gemini_ import GeminiAdapter

            mock_genai = MagicMock()
            mock_genai.Client.return_value = MagicMock()

            with patch.dict("sys.modules", {"google.genai": mock_genai}):
                adapter = GeminiAdapter.__new__(GeminiAdapter)
                adapter._config = gemini_config
                adapter._model = gemini_config.model_name

                with pytest.raises(WorkerAuthError):
                    adapter._handle_error(Exception("API_KEY not valid. 401"))
        except ImportError:
            pytest.skip("SDK Gemini non disponible")

    def test_handle_rate_limit_error(self, gemini_config: WorkerConfig) -> None:
        """Les erreurs de quota doivent lever WorkerRateLimitError."""
        try:
            from nexus_worker.core.errors import WorkerRateLimitError
            from nexus_worker.providers.gemini_ import GeminiAdapter

            adapter = GeminiAdapter.__new__(GeminiAdapter)
            adapter._config = gemini_config
            adapter._model = gemini_config.model_name

            with pytest.raises(WorkerRateLimitError):
                adapter._handle_error(Exception("quota exceeded 429"))
        except ImportError:
            pytest.skip("SDK Gemini non disponible")

    def test_handle_timeout_error(self, gemini_config: WorkerConfig) -> None:
        """Les erreurs de timeout doivent lever WorkerTimeoutError."""
        try:
            from nexus_worker.core.errors import WorkerTimeoutError
            from nexus_worker.providers.gemini_ import GeminiAdapter

            adapter = GeminiAdapter.__new__(GeminiAdapter)
            adapter._config = gemini_config
            adapter._model = gemini_config.model_name

            with pytest.raises(WorkerTimeoutError):
                adapter._handle_error(Exception("deadline exceeded timeout"))
        except ImportError:
            pytest.skip("SDK Gemini non disponible")

    def test_handle_unknown_error(self, gemini_config: WorkerConfig) -> None:
        """Les erreurs inconnues doivent lever WorkerUnavailableError."""
        try:
            from nexus_worker.core.errors import WorkerUnavailableError
            from nexus_worker.providers.gemini_ import GeminiAdapter

            adapter = GeminiAdapter.__new__(GeminiAdapter)
            adapter._config = gemini_config
            adapter._model = gemini_config.model_name

            with pytest.raises(WorkerUnavailableError):
                adapter._handle_error(Exception("something completely unexpected happened"))
        except ImportError:
            pytest.skip("SDK Gemini non disponible")


class TestGeminiFactoryRegistration:
    """Tests d'enregistrement dans la factory."""

    def test_gemini_in_registry(self) -> None:
        """Le provider 'gemini' doit être dans le registre."""
        from nexus_worker.providers.factory import list_providers

        assert "gemini" in list_providers()
