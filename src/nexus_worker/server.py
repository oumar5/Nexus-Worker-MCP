"""Serveur MCP principal de Nexus-Worker-MCP.

Initialise tous les services, enregistre les 8 outils MCP
avec leurs descriptions détaillées, et gère les deux transports.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from nexus_worker.config import Config
from nexus_worker.core.cache import ResultCache
from nexus_worker.core.errors import CallTracker
from nexus_worker.core.logger import setup_logger
from nexus_worker.core.metrics import MetricsCollector
from nexus_worker.prompts.engine import PromptEngine
from nexus_worker.providers.base import WorkerProvider
from nexus_worker.providers.factory import create_providers_from_config
from nexus_worker.providers.fallback import CompositeProvider
from nexus_worker.tools.analyze import worker_analyze_file
from nexus_worker.tools.document import worker_document_code
from nexus_worker.tools.explain import worker_explain_code
from nexus_worker.tools.generate import worker_generate_code
from nexus_worker.tools.refactor import worker_refactor_code
from nexus_worker.tools.review import worker_review_code
from nexus_worker.tools.test import worker_generate_tests


class NexusWorkerServer:
    """Serveur MCP Nexus-Worker-MCP.

    Orchestre la délégation de tâches lourdes vers un modèle Worker
    économique via le protocole MCP.
    """

    def __init__(self, config: Config | None = None) -> None:
        """Initialise le serveur avec tous ses services.

        Args:
            config: Configuration globale. Si None, charge depuis .env.
        """
        self.config = config or Config()

        # Logger
        self.logger = setup_logger(
            level=self.config.logging.level,
            log_file=self.config.logging.file,
        )
        self.logger.info("Initialisation de Nexus-Worker-MCP...")

        # Provider principal + fallback (optionnel)
        self.primary_provider, self.fallback_provider = create_providers_from_config(self.config)

        # Si un fallback est configuré, on encapsule les deux dans un
        # CompositeProvider qui bascule automatiquement en cas d'échec.
        # Sinon, le provider actif reste simplement le principal.
        if self.fallback_provider is not None:
            self.active_provider: WorkerProvider = CompositeProvider(
                primary=self.primary_provider,
                fallback=self.fallback_provider,
            )
        else:
            self.active_provider = self.primary_provider

        # Services
        self.prompt_engine = PromptEngine(self.config.prompt_templates_dir)
        self.metrics = MetricsCollector(enabled=self.config.logging.metrics_enabled)
        self.call_tracker = CallTracker()

        # Cache de résultats
        self.cache = ResultCache(
            enabled=self.config.cache.enabled,
            ttl_seconds=self.config.cache.ttl_seconds,
            max_size=self.config.cache.max_size,
        )

        # Serveur MCP
        self.mcp = FastMCP(
            "nexus-worker",
            host=self.config.transport.host,
            port=self.config.transport.port,
            instructions=(
                "Serveur d'optimisation de coûts. Il expose 8 outils qui délèguent les tâches "
                "de code lourdes en tokens (analyse, revue, explication, documentation, "
                "génération, refactoring, tests) à un modèle Worker économique, et te "
                "renvoient un résultat structuré et compact.\n\n"
                "Quand utiliser ces outils : dès qu'une tâche implique de lire un fichier entier "
                "pour le comprendre, ou de produire/réécrire du code. Ils évitent de charger le "
                "contenu brut dans ton contexte.\n\n"
                "Multi-fichiers : appeler l'outil une fois par fichier, puis synthétiser les "
                "résultats compacts. Ne lis pas les fichiers toi-même pour une 'vue globale'.\n\n"
                "Exception : un seul fichier de moins de ~50 lignes, tu peux le traiter "
                "directement."
            ),
        )

        # Enregistrer les outils
        self._register_tools()

        provider_info = self.primary_provider.get_info()
        self.logger.info(
            f"Serveur initialisé — Provider: {provider_info.get('provider')}, "
            f"Model: {provider_info.get('model')}, "
            f"Transport: {self.config.transport.mode}, "
            f"Cache: {'activé' if self.config.cache.enabled else 'désactivé'}"
        )

    def _get_provider(self) -> WorkerProvider:
        """Retourne le provider actif.

        Si un fallback est configuré, retourne un CompositeProvider qui bascule
        automatiquement du principal vers le fallback en cas d'échec. Sinon,
        retourne directement le provider principal.

        Returns:
            Le provider actif (principal seul, ou composite avec fallback).
        """
        return self.active_provider

    def _register_tools(self) -> None:
        """Enregistre les 8 outils MCP avec leurs descriptions détaillées."""

        # ── Outil 1 : Génération de code ─────────────────────────────────

        @self.mcp.tool(
            description=(
                "Génère du code via le Worker économique. À utiliser pour produire plus de "
                "~30 lignes de code. Renvoie le code structuré et peut l'écrire sur disque.\n\n"
                "Option auto_save=True : le Worker écrit directement le fichier ; tu n'as plus "
                "qu'à relire et corriger si besoin.\n\n"
                "Ne pas utiliser pour des ajouts/corrections de moins de ~10 lignes."
            )
        )
        async def worker_generate_code_tool(
            instruction: str,
            target_path: str = "",
            language: str = "",
            context: str = "",
            auto_save: bool = False,
        ) -> str:
            return await worker_generate_code(
                instruction=instruction,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                target_path=target_path,
                language=language,
                context=context,
                auto_save=auto_save,
            )

        # ── Outil 2 : Analyse de fichier ─────────────────────────────────

        @self.mcp.tool(
            description=(
                "Analyse un fichier source via le Worker et renvoie une analyse structurée "
                "et compacte, plutôt que le texte brut du fichier.\n\n"
                "Déclencheurs : 'analyse', 'résume', 'fais un rapport', 'audit'.\n\n"
                "Multi-fichiers (ex : 'analyse le module UI') : appeler une fois par fichier, "
                "chaque appel renvoie un résumé compact, puis synthétiser les résumés pour le "
                "rapport global. Ne pas lire tous les fichiers soi-même.\n\n"
                "Paramètre focus_lines optionnel pour cibler une plage (ex : '100-200').\n\n"
                "Exception : un seul fichier de moins de ~50 lignes."
            )
        )
        async def worker_analyze_file_tool(
            file_path: str,
            question: str,
            focus_lines: str = "",
        ) -> str:
            return await worker_analyze_file(
                file_path=file_path,
                question=question,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                focus_lines=focus_lines,
                cache=self.cache,
            )

        # ── Outil 3 : Refactoring ────────────────────────────────────────

        @self.mcp.tool(
            description=(
                "Refactorise un fichier via le Worker en une seule passe, en tenant compte de "
                "son contexte. À utiliser pour un refactoring qui touche de nombreuses lignes.\n\n"
                "Multi-fichiers (ex : 'refactorise tout le module') : appeler une fois par "
                "fichier.\n\n"
                "Option auto_save=True : écriture directe sur disque.\n\n"
                "Ne pas utiliser pour changer une seule ligne."
            )
        )
        async def worker_refactor_code_tool(
            file_path: str,
            instruction: str,
            target_lines: str = "",
            context: str = "",
            auto_save: bool = False,
        ) -> str:
            return await worker_refactor_code(
                file_path=file_path,
                instruction=instruction,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                target_lines=target_lines,
                context=context,
                auto_save=auto_save,
            )

        # ── Outil 4 : Explication de code ────────────────────────────────

        @self.mcp.tool(
            description=(
                "Explique la logique d'un fichier via le Worker et renvoie une explication "
                "structurée, plutôt que le code brut.\n\n"
                "Déclencheurs : 'explique', 'comment ça marche', 'c'est quoi'.\n\n"
                "Multi-fichiers (ex : 'explique comment marche le UI') : appeler une fois par "
                "fichier, puis synthétiser les réponses.\n\n"
                "Paramètre detail_level : 'summary', 'detailed' (défaut) ou 'line-by-line'."
            )
        )
        async def worker_explain_code_tool(
            file_path: str,
            focus: str = "",
            detail_level: str = "detailed",
        ) -> str:
            return await worker_explain_code(
                file_path=file_path,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                focus=focus,
                detail_level=detail_level,
                cache=self.cache,
            )

        # ── Outil 5 : Génération de tests ────────────────────────────────

        @self.mcp.tool(
            description=(
                "Génère une suite de tests pour un fichier via le Worker, avec setup, teardown "
                "et cas limites. Connaît les frameworks courants (pytest, Jest, etc.).\n\n"
                "Multi-fichiers (ex : 'génère des tests pour tout le module') : appeler une fois "
                "par fichier source.\n\n"
                "Paramètres : test_framework (défaut 'pytest'), focus_functions, coverage_level."
            )
        )
        async def worker_generate_tests_tool(
            file_path: str,
            test_framework: str = "pytest",
            focus_functions: str = "",
            coverage_level: str = "thorough",
        ) -> str:
            return await worker_generate_tests(
                file_path=file_path,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                test_framework=test_framework,
                focus_functions=focus_functions,
                coverage_level=coverage_level,
            )

        # ── Outil 6 : Revue de code ──────────────────────────────────────

        @self.mcp.tool(
            description=(
                "Fait une revue de code d'un fichier via le Worker et renvoie un rapport JSON "
                "structuré (bugs, sécurité, performance, style).\n\n"
                "Déclencheurs : 'vérifie', 'revue', 'bugs', 'audit'.\n\n"
                "Multi-fichiers (ex : 'audit du projet') : appeler une fois par fichier, puis "
                "compiler les rapports JSON.\n\n"
                "Paramètre focus optionnel : 'security', 'performance', 'bugs', etc."
            )
        )
        async def worker_review_code_tool(
            file_path: str,
            focus: str = "",
        ) -> str:
            return await worker_review_code(
                file_path=file_path,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                focus=focus,
                cache=self.cache,
            )

        # ── Outil 7 : Documentation automatique ──────────────────────────

        @self.mcp.tool(
            description=(
                "Ajoute des docstrings à un fichier via le Worker, sans modifier la logique du "
                "code. Connaît les conventions (Google, Numpy, JSDoc).\n\n"
                "Déclencheurs : 'documente', 'ajoute des docstrings', 'commente le code'.\n\n"
                "Multi-fichiers (ex : 'documente tout le projet') : appeler une fois par "
                "fichier.\n\n"
                "Paramètre style optionnel : 'google', 'numpy', 'jsdoc', etc."
            )
        )
        async def worker_document_code_tool(
            file_path: str,
            style: str = "",
        ) -> str:
            return await worker_document_code(
                file_path=file_path,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                allowed_paths=self.config.security.get_allowed_paths(),
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                style=style,
                cache=self.cache,
            )

        # ── Outil 8 : Métriques FinOps ───────────────────────────────────

        @self.mcp.tool(
            name="worker_get_metrics_tool",
            description=(
                "Retourne un rapport d'utilisation de la session en cours : "
                "tokens délégués (input/output), nombre d'appels, latences "
                "moyennes, et statistiques du cache.\n\n"
                "Appelle cet outil en fin de session ou à tout moment pour "
                "mesurer l'activité du Worker. Le client peut utiliser ces "
                "données brutes de tokens pour calculer les économies financières "
                "générées par rapport à son modèle principal."
            )
        )
        async def worker_get_metrics_tool() -> str:
            cache_stats = self.cache.stats()
            summary = self.metrics.get_summary()
            return json.dumps(
                {
                    "status": "success",
                    "metrics": summary,
                    "cache": cache_stats,
                },
                ensure_ascii=False,
            )

    def run(self) -> None:
        """Lance le serveur MCP selon le transport configuré."""
        transport = self.config.transport.mode.lower()

        if transport == "stdio":
            self.logger.info("Démarrage en mode stdio...")
            self.mcp.run(transport="stdio")
        elif transport == "http":
            host = self.config.transport.host
            port = self.config.transport.port
            self.logger.info(f"Démarrage en mode HTTP sur {host}:{port}...")
            self.mcp.run(transport="sse")
        else:
            raise ValueError(f"Transport inconnu: '{transport}'. Valeurs possibles: stdio, http")
