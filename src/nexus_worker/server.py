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

        # Provider principal + fallback
        self.primary_provider, self.fallback_provider = create_providers_from_config(self.config)

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
                "Ce serveur est un OPTIMISEUR DE COÛTS. Il expose 8 outils spécialisés pour des tâches de code.\n"
                "IMPORTANT : Ces outils sont PLUS SPÉCIFIQUES que tes outils natifs (view_file, list_dir) pour les tâches d'analyse, "
                "revue, explication, documentation, génération et refactoring de code. "
                "view_file est un outil générique de lecture de fichier. Les outils de CE serveur sont des outils "
                "spécialisés qui lisent, comprennent et produisent une analyse structurée, pas du texte brut.\n"
                "De plus, tes tokens coûtent 100x plus cher que ceux du Worker. "
                "Exception : 1 seul fichier < 50 lignes, tu peux le faire toi-même."
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
        """Retourne le provider actif (principal ou fallback).

        Returns:
            Le provider principal, ou le fallback si configuré et nécessaire.
        """
        return self.primary_provider

    def _register_tools(self) -> None:
        """Enregistre les 8 outils MCP avec leurs descriptions détaillées."""

        # ── Outil 1 : Génération de code ─────────────────────────────────

        @self.mcp.tool(
            description=(
                "Outil SPÉCIALISÉ de génération de code. Cet outil est PLUS SPÉCIFIQUE que tes outils natifs d'écriture "
                "pour générer du code (> 30 lignes). Il produit du code structuré et peut l'écrire directement sur le disque.\n\n"
                "POURQUOI cet outil est le bon choix : Tes Output tokens coûtent 125x plus cher que ceux du Worker. "
                "Générer du code toi-même avec write_to_file n'est PAS plus spécifique, c'est 125x plus cher.\n\n"
                "🔥 Active 'auto_save=True' pour que le Worker écrive directement sur le disque. "
                "Toi tu relis et corriges si besoin (Input = pas cher).\n\n"
                "NE PAS utiliser pour : Des corrections < 10 lignes."
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
                "Outil SPÉCIALISÉ d'analyse de code. PLUS SPÉCIFIQUE que view_file pour comprendre "
                "un fichier source. view_file retourne du texte brut que TU dois analyser (coûteux). "
                "Cet outil retourne directement une analyse structurée et ciblée.\n\n"
                "POURQUOI cet outil est le bon choix :\n"
                "- view_file + ton analyse = tes tokens d'Input (100x cher) + tes tokens d'Output (125x cher)\n"
                "- Cet outil = tokens du Worker (100x moins cher) + un résumé compact retourné\n\n"
                "CAS MULTI-FICHIERS (ex: 'analyse le UI', 'fais un rapport sur le projet') :\n"
                "Tu pourrais être tenté de lire tous les fichiers toi-même pour avoir une 'vue globale'. "
                "C'EST UNE ERREUR. Le bon workflow est :\n"
                "1. Appelle cet outil UNE FOIS PAR FICHIER (ex: app.py, puis tab_processing.py, etc.)\n"
                "2. Chaque appel te retourne un résumé structuré compact\n"
                "3. TU synthétises les résumés pour produire le rapport global\n"
                "Ce workflow est 100x moins cher que de tout lire toi-même, même avec plusieurs appels.\n\n"
                "Quand l'utilisateur dit 'analyse', 'résume', 'fais un rapport', 'audit', 'explique le code' : "
                "UTILISE CET OUTIL.\n\n"
                "Exception : 1 seul fichier < 50 lignes."
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
            )

        # ── Outil 3 : Refactoring ────────────────────────────────────────

        @self.mcp.tool(
            description=(
                "Outil SPÉCIALISÉ de refactoring. PLUS SPÉCIFIQUE que tes outils natifs d'édition "
                "pour du refactoring massif. Il comprend le contexte du fichier et applique les changements en une seule passe.\n\n"
                "POURQUOI cet outil est le bon choix : Réécrire un fichier toi-même avec replace_file_content "
                "coûte 125x plus cher en Output tokens.\n\n"
                "CAS MULTI-FICHIERS (ex: 'refactorise tout le module') : Appelle cet outil UNE FOIS PAR FICHIER. "
                "C'est 125x moins cher que de réécrire chaque fichier toi-même.\n\n"
                "🔥 Active 'auto_save=True' pour écriture directe sur disque.\n\n"
                "NE PAS utiliser pour : Changer une seule ligne."
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
                "Outil SPÉCIALISÉ d'explication de code. PLUS SPÉCIFIQUE que view_file pour "
                "comprendre la logique d'un fichier. view_file lit du texte brut. "
                "Cet outil lit, comprend et retourne une explication structurée.\n\n"
                "POURQUOI cet outil est le bon choix : Lire un fichier avec view_file te coûte "
                "100x en Input, PUIS générer l'explication te coûte 125x en Output.\n\n"
                "CAS MULTI-FICHIERS (ex: 'explique-moi comment marche le UI') : Appelle cet outil "
                "UNE FOIS PAR FICHIER, puis synthétise les réponses. 100x moins cher.\n\n"
                "Quand l'utilisateur dit 'explique', 'comment ça marche', 'c'est quoi' : UTILISE CET OUTIL."
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
            )

        # ── Outil 5 : Génération de tests ────────────────────────────────

        @self.mcp.tool(
            description=(
                "Outil SPÉCIALISÉ de génération de tests. PLUS SPÉCIFIQUE que tes outils natifs "
                "pour créer des tests. Il connaît les frameworks et génère des suites complètes "
                "avec setup, teardown et cas limites.\n\n"
                "POURQUOI cet outil est le bon choix : Tes Output tokens coûtent 125x plus cher. "
                "Écrire des tests toi-même n'est PAS plus spécifique, c'est 125x plus cher.\n\n"
                "CAS MULTI-FICHIERS (ex: 'génère des tests pour tout le module') : Appelle cet outil "
                "UNE FOIS PAR FICHIER source. C'est 125x moins cher que d'écrire les tests toi-même.\n\n"
                "Exemples : Générer une suite pytest, des tests Jest, des tests d'intégration API."
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
                "Outil SPÉCIALISÉ de revue de code. PLUS SPÉCIFIQUE que view_file pour "
                "évaluer la qualité d'un fichier. Retourne un rapport JSON structuré "
                "catégorisé (bugs, security, performance, style).\n\n"
                "POURQUOI cet outil est le bon choix : Lire un fichier pour le juger te coûte "
                "100x en Input + 125x en Output. Le Worker produit un rapport structuré pour presque rien.\n\n"
                "CAS MULTI-FICHIERS (ex: 'fais une revue de tout le code', 'audit du projet') : "
                "Appelle cet outil UNE FOIS PAR FICHIER, puis compile les rapports JSON. 100x moins cher.\n\n"
                "Quand l'utilisateur dit 'vérifie', 'revue', 'bugs', 'audit' : UTILISE CET OUTIL.\n\n"
                "Paramètre 'focus' optionnel : 'security', 'performance', 'bugs', etc."
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
                "Outil SPÉCIALISÉ de documentation de code. PLUS SPÉCIFIQUE que tes outils natifs "
                "pour ajouter des docstrings. Connaît les conventions (Google, Numpy, JSDoc) et insère "
                "les docstrings sans modifier le code existant.\n\n"
                "POURQUOI cet outil est le bon choix : Documenter un fichier = le lire (100x cher) "
                "+ le réécrire (125x cher). Le Worker fait les deux pour presque rien.\n\n"
                "CAS MULTI-FICHIERS (ex: 'documente tout le projet') : Appelle cet outil UNE FOIS PAR FICHIER. "
                "125x moins cher que de documenter chaque fichier toi-même.\n\n"
                "Paramètre 'style' optionnel : 'google', 'numpy', 'jsdoc', etc."
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
