"""Interface commune pour tous les adaptateurs de fournisseurs.

Définit le Protocol WorkerProvider et la dataclass WorkerResponse
que tout adaptateur doit respecter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class WorkerResponse:
    """Réponse standardisée d'un worker, quel que soit le fournisseur.

    Attributes:
        content: Le texte ou code généré par le worker.
        tokens_input: Nombre de tokens d'entrée consommés.
        tokens_output: Nombre de tokens de sortie consommés.
        model: Nom du modèle utilisé.
        latency_ms: Temps de réponse en millisecondes.
        raw_response: Réponse brute du provider (pour debug).
        used_fallback: True si la réponse provient du provider de secours.
        retry_count: Nombre de tentatives supplémentaires avant succès (0 = premier essai).
    """

    content: str
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""
    latency_ms: float = 0
    raw_response: dict[str, Any] | None = None
    used_fallback: bool = False
    retry_count: int = 0


@runtime_checkable
class WorkerProvider(Protocol):
    """Interface que tout adaptateur fournisseur doit implémenter.

    Les trois méthodes sont obligatoires :
    - complete: envoie un prompt et retourne la réponse
    - health_check: vérifie la disponibilité du fournisseur
    - get_info: retourne les métadonnées du provider
    """

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> WorkerResponse:
        """Envoie un prompt au modèle worker et retourne la réponse.

        Args:
            system_prompt: Prompt système (instructions pour le worker).
            user_prompt: Prompt utilisateur (la tâche à exécuter).
            max_tokens: Limite de tokens de sortie.
            temperature: Créativité du modèle (0=déterministe, 1=créatif).

        Returns:
            WorkerResponse avec le contenu et les métriques.
        """
        ...

    async def health_check(self) -> bool:
        """Vérifie que le fournisseur est joignable et fonctionnel.

        Returns:
            True si le fournisseur répond correctement.
        """
        ...

    def get_info(self) -> dict[str, Any]:
        """Retourne les métadonnées du provider.

        Returns:
            Dictionnaire avec provider, model, endpoint, etc.
        """
        ...
