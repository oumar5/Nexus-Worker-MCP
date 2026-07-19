"""Collecteur de métriques pour Nexus-Worker-MCP.

Comptabilise les tokens consommés, le nombre d'appels, la latence
et le taux de succès par outil et par session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


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
            "tools": {},
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

        return summary
    def reset(self) -> None:
        """Réinitialise toutes les métriques."""
        self.session = SessionMetrics()
