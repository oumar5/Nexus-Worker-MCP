"""Collecteur de métriques pour Nexus-Worker-MCP.

Comptabilise les tokens consommés, le nombre d'appels, la latence
et le taux de succès par outil et par session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelUsage:
    """Consommation de tokens agrégée pour un modèle Worker donné.

    Permet au Cerveau de calculer les coûts par modèle en appliquant
    lui-même sa grille tarifaire (le serveur ne connaît pas les prix).
    """

    calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0

    @property
    def total_tokens(self) -> int:
        """Nombre total de tokens consommés (input + output)."""
        return self.total_tokens_input + self.total_tokens_output


@dataclass
class ToolMetrics:
    """Métriques agrégées pour un outil spécifique."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_ms: float = 0
    retries_count: int = 0
    fallback_count: int = 0

    @property
    def success_rate(self) -> float:
        """Taux de succès en pourcentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.successful_calls / self.total_calls) * 100

    @property
    def average_latency_ms(self) -> float:
        """Latence moyenne en millisecondes."""
        if self.successful_calls == 0:
            return 0.0
        return self.total_latency_ms / self.successful_calls

    @property
    def total_tokens(self) -> int:
        """Nombre total de tokens consommés (input + output)."""
        return self.total_tokens_input + self.total_tokens_output


@dataclass
class SessionMetrics:
    """Métriques globales de la session en cours."""

    session_start: float = field(default_factory=time.time)
    tools: dict[str, ToolMetrics] = field(default_factory=dict)
    models: dict[str, ModelUsage] = field(default_factory=dict)

    def _ensure_tool(self, tool_name: str) -> ToolMetrics:
        """Crée les métriques pour un outil s'il n'existe pas encore.

        Args:
            tool_name: Nom de l'outil MCP.

        Returns:
            L'instance ToolMetrics pour l'outil.
        """
        if tool_name not in self.tools:
            self.tools[tool_name] = ToolMetrics()
        return self.tools[tool_name]

    def _ensure_model(self, model: str) -> ModelUsage:
        """Crée l'agrégat de consommation d'un modèle s'il n'existe pas encore.

        Args:
            model: Nom du modèle Worker (ex: "gpt-4o-2024-05-13").

        Returns:
            L'instance ModelUsage pour ce modèle.
        """
        if model not in self.models:
            self.models[model] = ModelUsage()
        return self.models[model]

    @property
    def total_tokens_input(self) -> int:
        """Total des tokens d'entrée sur tous les outils."""
        return sum(t.total_tokens_input for t in self.tools.values())

    @property
    def total_tokens_output(self) -> int:
        """Total des tokens de sortie sur tous les outils."""
        return sum(t.total_tokens_output for t in self.tools.values())

    @property
    def total_calls(self) -> int:
        """Total des appels sur tous les outils."""
        return sum(t.total_calls for t in self.tools.values())

    @property
    def total_retries(self) -> int:
        """Total des retries sur tous les outils."""
        return sum(t.retries_count for t in self.tools.values())

    @property
    def total_fallbacks(self) -> int:
        """Total des bascules sur le fallback provider, tous outils confondus."""
        return sum(t.fallback_count for t in self.tools.values())

    @property
    def session_duration_seconds(self) -> float:
        """Durée de la session en secondes."""
        return time.time() - self.session_start


class MetricsCollector:
    """Collecteur de métriques en mémoire pour la session en cours.

    Enregistre les statistiques de chaque appel d'outil et fournit
    un résumé agrégé à la demande.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialise le collecteur.

        Args:
            enabled: Si False, les métriques sont silencieusement ignorées.
        """
        self.enabled = enabled
        self.session = SessionMetrics()

    def record_call(
        self,
        tool_name: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        latency_ms: float = 0,
        success: bool = True,
        was_retry: bool = False,
        was_fallback: bool = False,
        model: str = "",
    ) -> None:
        """Enregistre les métriques d'un appel d'outil.

        Args:
            tool_name: Nom de l'outil MCP appelé.
            tokens_input: Tokens d'entrée consommés.
            tokens_output: Tokens de sortie consommés.
            latency_ms: Temps de réponse en millisecondes.
            success: True si l'appel a réussi.
            was_retry: True si c'était un retry après échec.
            was_fallback: True si le fallback provider a été utilisé.
            model: Nom du modèle Worker ayant traité l'appel. Sert à agréger
                   la consommation par modèle pour le calcul des coûts.
        """
        if not self.enabled:
            return

        tool = self.session._ensure_tool(tool_name)
        tool.total_calls += 1
        tool.total_tokens_input += tokens_input
        tool.total_tokens_output += tokens_output

        if success:
            tool.successful_calls += 1
            tool.total_latency_ms += latency_ms
        else:
            tool.failed_calls += 1

        if was_retry:
            tool.retries_count += 1
        if was_fallback:
            tool.fallback_count += 1

        # Agréger la consommation par modèle (uniquement sur succès :
        # un échec n'a pas de tokens ni de modèle fiables à attribuer).
        if success and model:
            usage = self.session._ensure_model(model)
            usage.calls += 1
            usage.total_tokens_input += tokens_input
            usage.total_tokens_output += tokens_output

    def get_summary(self) -> dict[str, Any]:
        """Retourne un résumé complet des métriques de la session.

        Returns:
            Dictionnaire avec les métriques globales et par outil.
        """
        if not self.enabled:
            return {"enabled": False}

        summary: dict[str, Any] = {
            "session_duration_seconds": round(self.session.session_duration_seconds, 1),
            "total_calls": self.session.total_calls,
            "total_tokens_input": self.session.total_tokens_input,
            "total_tokens_output": self.session.total_tokens_output,
            "total_tokens": self.session.total_tokens_input + self.session.total_tokens_output,
            "total_retries": self.session.total_retries,
            "total_fallbacks": self.session.total_fallbacks,
            "tools": {},
            "by_model": {},
        }

        for name, tool in self.session.tools.items():
            summary["tools"][name] = {
                "calls": tool.total_calls,
                "success_rate": round(tool.success_rate, 1),
                "tokens_input": tool.total_tokens_input,
                "tokens_output": tool.total_tokens_output,
                "avg_latency_ms": round(tool.average_latency_ms, 1),
                "retries": tool.retries_count,
                "fallbacks": tool.fallback_count,
            }

        # Consommation par modèle : le Cerveau applique sa propre grille
        # tarifaire sur ces tokens bruts pour estimer les coûts/économies.
        for model_name, usage in self.session.models.items():
            summary["by_model"][model_name] = {
                "calls": usage.calls,
                "tokens_input": usage.total_tokens_input,
                "tokens_output": usage.total_tokens_output,
                "total_tokens": usage.total_tokens,
            }

        return summary
    def reset(self) -> None:
        """Réinitialise toutes les métriques."""
        self.session = SessionMetrics()
