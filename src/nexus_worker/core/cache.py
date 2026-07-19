"""Cache LRU en mémoire pour Nexus-Worker-MCP.

Évite de rappeler le Worker si le fichier et le prompt sont identiques.
La clé de cache est un hash SHA-256 du contenu du fichier + du prompt.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """Une entrée dans le cache.

    Attributes:
        value: La valeur mise en cache (résultat JSON stringifié).
        created_at: Timestamp de création (epoch secondes).
        hits: Nombre de fois où cette entrée a été servie depuis le cache.
    """

    value: str
    created_at: float = field(default_factory=time.time)
    hits: int = 0


class ResultCache:
    """Cache LRU en mémoire pour les résultats des outils Worker.

    Stocke les résultats par clé de hachage (SHA-256 du contenu + prompt).
    Supporte un TTL configurable et une taille maximale (LRU eviction).
    """

    def __init__(self, enabled: bool = True, ttl_seconds: int = 3600, max_size: int = 256) -> None:
        """Initialise le cache.

        Args:
            enabled: Si False, le cache est totalement transparent (no-op).
            ttl_seconds: Durée de vie d'une entrée en secondes.
            max_size: Nombre maximum d'entrées avant éviction LRU.
        """
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._store: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(content: str, prompt: str) -> str:
        """Génère une clé de cache déterministe depuis le contenu et le prompt.

        Args:
            content: Contenu du fichier lu.
            prompt: Prompt utilisateur envoyé au Worker.

        Returns:
            Hash SHA-256 hexadécimal de la combinaison.
        """
        combined = f"{content}\x00{prompt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        """Retourne la valeur en cache si elle existe et n'est pas expirée.

        Args:
            key: Clé de cache (générée par make_key).

        Returns:
            La valeur mise en cache, ou None si absent / expiré.
        """
        if not self.enabled:
            return None

        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None

        # Vérifier le TTL
        if time.time() - entry.created_at > self.ttl_seconds:
            del self._store[key]
            self._misses += 1
            return None

        entry.hits += 1
        self._hits += 1
        return entry.value

    def set(self, key: str, value: str) -> None:
        """Stocke une valeur dans le cache.

        Si le cache est plein, l'entrée la moins récemment créée est évincée (LRU simplifié).

        Args:
            key: Clé de cache.
            value: Valeur à stocker (résultat JSON stringifié).
        """
        if not self.enabled:
            return

        # Éviction LRU si plein
        if len(self._store) >= self.max_size and key not in self._store:
            oldest_key = min(self._store, key=lambda k: self._store[k].created_at)
            del self._store[oldest_key]

        self._store[key] = CacheEntry(value=value)

    def invalidate(self, key: str) -> bool:
        """Supprime une entrée du cache.

        Args:
            key: Clé de cache à supprimer.

        Returns:
            True si l'entrée existait, False sinon.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Vide entièrement le cache."""
        self._store.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Retourne les statistiques d'utilisation du cache.

        Returns:
            Dictionnaire avec taille, hits, misses et taux de hit.
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        return {
            "enabled": self.enabled,
            "size": len(self._store),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 1),
        }
