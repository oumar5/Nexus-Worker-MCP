"""Configuration centralisée chargée depuis les variables d'environnement."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class WorkerConfig(BaseSettings):
    """Configuration du modèle Worker (exécuteur)."""

    provider: str = Field(default="openai", alias="WORKER_PROVIDER")
    api_base_url: str = Field(default="https://api.openai.com/v1", alias="WORKER_API_BASE_URL")
    api_key: str = Field(default="", alias="WORKER_API_KEY")
    model_name: str = Field(default="gpt-4o", alias="WORKER_MODEL_NAME")
    api_version: str | None = Field(default=None, alias="WORKER_API_VERSION")
    max_retries: int = Field(default=3, alias="WORKER_MAX_RETRIES")
    timeout_seconds: int = Field(default=120, alias="WORKER_TIMEOUT_SECONDS")
    max_output_tokens: int = Field(default=4096, alias="WORKER_MAX_OUTPUT_TOKENS")


class FallbackConfig(BaseSettings):
    """Configuration du provider de secours (optionnel)."""

    provider: str | None = Field(default=None, alias="WORKER_FALLBACK_PROVIDER")
    api_base_url: str | None = Field(default=None, alias="WORKER_FALLBACK_API_BASE_URL")
    api_key: str | None = Field(default=None, alias="WORKER_FALLBACK_API_KEY")
    model_name: str | None = Field(default=None, alias="WORKER_FALLBACK_MODEL_NAME")

    @property
    def is_configured(self) -> bool:
        """Vérifie si un fallback est configuré."""
        return self.provider is not None and self.model_name is not None


class TransportConfig(BaseSettings):
    """Configuration du transport MCP."""

    mode: str = Field(default="stdio", alias="MCP_TRANSPORT")
    host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    port: int = Field(default=8080, alias="MCP_PORT")


class SecurityConfig(BaseSettings):
    """Configuration de sécurité."""

    allowed_paths: str = Field(default=".", alias="ALLOWED_PATHS")

    def get_allowed_paths(self) -> list[Path]:
        """Retourne la liste des chemins autorisés en tant que Path résolus."""
        return [Path(p.strip()).resolve() for p in self.allowed_paths.split(",")]


class LoggingConfig(BaseSettings):
    """Configuration du logging."""

    level: str = Field(default="INFO", alias="LOG_LEVEL")
    file: str = Field(default="nexus_worker.log", alias="LOG_FILE")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")


class CacheConfig(BaseSettings):
    """Configuration du cache de résultats en mémoire."""

    enabled: bool = Field(default=True, alias="CACHE_ENABLED")
    ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    max_size: int = Field(default=256, alias="CACHE_MAX_SIZE")


class Config:
    """Configuration globale du serveur Nexus-Worker-MCP.

    Regroupe toutes les sous-configurations et gère le chargement
    depuis les variables d'environnement et le fichier .env.
    """

    def __init__(self, env_file: str | Path | None = ".env") -> None:
        """Charge la configuration depuis l'environnement.

        Args:
            env_file: Chemin vers le fichier .env. None pour ignorer.
        """
        # Charger le .env si présent
        if env_file:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)

        self.worker = WorkerConfig()
        self.fallback = FallbackConfig()
        self.transport = TransportConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        self.cache = CacheConfig()

    @property
    def prompt_templates_dir(self) -> Path | None:
        """Retourne le répertoire de templates personnalisé si configuré."""
        import os

        custom_dir = os.getenv("PROMPT_TEMPLATES_DIR")
        if custom_dir:
            path = Path(custom_dir)
            if path.is_dir():
                return path
        return None
