"""Serveur MCP principal de Nexus-Worker-MCP.

Initialise tous les services, enregistre les 8 outils MCP
avec leurs descriptions détaillées, et gère les deux transports.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from nexus_worker.config import Config
from nexus_worker.core.cache import ResultCache
from nexus_worker.core.errors import CallTracker, ToolRateLimitedError
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
            instructions=(
                "Ce serveur expose 8 outils pour déléguer les tâches lourdes en tokens "
                "(génération, analyse, refactoring, explication, tests, revue de code, "
                "documentation, métriques FinOps) à un modèle Worker économique. "
                "Utilisez ces outils au lieu de réaliser ces tâches vous-même "
                "pour optimiser les coûts."
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
                "Utilise cet outil OBLIGATOIREMENT lorsque tu dois générer du code "
                "dépassant 30 lignes. Ne génère JAMAIS de longs blocs de code toi-même "
                "— délègue à cet outil. Fournis une instruction technique détaillée "
                "incluant : le langage, le framework, les conventions de nommage, et le "
                "comportement attendu. L'outil retournera le code généré prêt à l'emploi. "
                "Tu pourras ensuite le relire, le valider et demander des corrections si "
                "nécessaire.\n\n"
                "Exemples d'utilisation : Créer une route API, un composant UI, un script "
                "de migration, un fichier de configuration.\n\n"
                "NE PAS utiliser pour : Des corrections mineures (< 10 lignes), ou de la "
                "logique qui dépend de la connaissance de plusieurs fichiers simultanément."
            )
        )
        async def worker_generate_code_tool(
            instruction: str,
            target_path: str = "",
            language: str = "",
            context: str = "",
        ) -> str:
            return await worker_generate_code(
                instruction=instruction,
                provider=self._get_provider(),
                prompt_engine=self.prompt_engine,
                metrics=self.metrics,
                call_tracker=self.call_tracker,
                max_retries=self.config.worker.max_retries,
                max_tokens=self.config.worker.max_output_tokens,
                target_path=target_path,
                language=language,
                context=context,
            )

        # ── Outil 2 : Analyse de fichier ─────────────────────────────────

        @self.mcp.tool(
            description=(
                "Utilise cet outil lorsque tu as besoin de comprendre le contenu d'un "
                "fichier que tu n'as pas encore lu, ou lorsque tu dois extraire des "
                "informations spécifiques d'un fichier volumineux. L'outil lit le fichier "
                "et utilise un modèle secondaire pour en extraire les informations que tu "
                "demandes.\n\n"
                "Exemples d'utilisation : 'Quelles routes sont définies ?', 'Y a-t-il des "
                "failles de sécurité ?', 'Résume la logique métier', 'Liste les dépendances'.\n\n"
                "NE PAS utiliser pour : Des fichiers déjà dans ton contexte, ou des fichiers "
                "très courts (< 50 lignes) — lis-les directement."
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
                "Utilise cet outil pour appliquer des modifications substantielles sur du "
                "code existant : renommage massif, restructuration, ajout de gestion "
                "d'erreurs, migration de patterns, ou conversion entre frameworks.\n\n"
                "Exemples d'utilisation : Convertir des callbacks en async/await, ajouter "
                "du try/catch partout, migrer des imports, appliquer un design pattern.\n\n"
                "NE PAS utiliser pour : Changer une seule ligne, ou du refactoring "
                "inter-fichiers nécessitant une vision transversale."
            )
        )
        async def worker_refactor_code_tool(
            file_path: str,
            instruction: str,
            target_lines: str = "",
            context: str = "",
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
            )

        # ── Outil 4 : Explication de code ────────────────────────────────

        @self.mcp.tool(
            description=(
                "Utilise cet outil lorsque tu as besoin de comprendre la logique d'un "
                "fichier ou d'un bloc de code avant de prendre une décision architecturale. "
                "Plutôt que de lire et analyser un gros fichier toi-même (coûteux en tokens), "
                "délègue l'explication à cet outil.\n\n"
                "Exemples d'utilisation : Comprendre un algorithme complexe, documenter une "
                "fonction legacy, identifier les effets de bord avant un refactoring."
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
                "Utilise cet outil pour générer des tests unitaires ou d'intégration pour "
                "un fichier ou une fonction existante. La génération de tests est une tâche "
                "lourde en tokens de sortie — délègue-la systématiquement.\n\n"
                "Exemples d'utilisation : Générer une suite pytest, des tests Jest, des "
                "tests d'intégration pour une API REST."
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
                "Utilise cet outil pour effectuer une revue de code structurée sur un fichier. "
                "Le Worker analyse le code et retourne une revue JSON catégorisée "
                "(bugs, security, performance, maintainability, style).\n\n"
                "Exemples d'utilisation : Vérifier la sécurité d'un endpoint API, détecter "
                "des fuites mémoire, évaluer la qualité du code avant une PR.\n\n"
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
                "Utilise cet outil pour générer automatiquement les docstrings et "
                "commentaires manquants dans un fichier. Le Worker retourne le fichier "
                "complet avec les docstrings insérées, sans modifier le code existant.\n\n"
                "Exemples d'utilisation : Documenter un fichier legacy, préparer une PR "
                "avec de la documentation, générer des docstrings Google Style pour Python.\n\n"
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
            description=(
                "Retourne un rapport FinOps de la session en cours : tokens délégués, "
                "coût réel du Worker, coût estimé si tu avais tout fait toi-même, "
                "économies réalisées et statistiques du cache.\n\n"
                "Appelle cet outil en fin de session ou à tout moment pour mesurer "
                "l'impact financier de l'architecture Nexus.\n\n"
                "Paramètres optionnels pour ajuster les prix (en $ par 1M tokens) :\n"
                "- worker_input_price : Coût input du Worker (défaut: 0.15)\n"
                "- worker_output_price : Coût output du Worker (défaut: 0.60)\n"
                "- brain_input_price : Coût input du Cerveau (défaut: 5.00)\n"
                "- brain_output_price : Coût output du Cerveau (défaut: 30.00)"
            )
        )
        async def worker_get_metrics_tool(
            worker_input_price: float = 0.15,
            worker_output_price: float = 0.60,
            brain_input_price: float = 5.00,
            brain_output_price: float = 30.00,
        ) -> str:
            finops = self.metrics.get_finops_summary(
                worker_input_price_per_1m=worker_input_price,
                worker_output_price_per_1m=worker_output_price,
                brain_input_price_per_1m=brain_input_price,
                brain_output_price_per_1m=brain_output_price,
            )
            cache_stats = self.cache.stats()
            return json.dumps(
                {
                    "status": "success",
                    "finops": finops,
                    "cache": cache_stats,
                    "tools_detail": self.metrics.get_summary().get("tools", {}),
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
            self.mcp.run(transport="sse", host=host, port=port)
        else:
            raise ValueError(
                f"Transport inconnu: '{transport}'. Valeurs possibles: stdio, http"
            )
