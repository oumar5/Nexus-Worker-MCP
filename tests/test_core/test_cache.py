"""Tests unitaires pour ResultCache."""

from __future__ import annotations

import time

import pytest

from nexus_worker.core.cache import ResultCache


class TestResultCacheMakeKey:
    """Tests de la génération de clé de cache."""

    def test_same_inputs_same_key(self) -> None:
        """Les mêmes entrées doivent produire la même clé."""
        key1 = ResultCache.make_key("content", "prompt")
        key2 = ResultCache.make_key("content", "prompt")
        assert key1 == key2

    def test_different_content_different_key(self) -> None:
        """Un contenu différent doit produire une clé différente."""
        key1 = ResultCache.make_key("content_a", "prompt")
        key2 = ResultCache.make_key("content_b", "prompt")
        assert key1 != key2

    def test_different_prompt_different_key(self) -> None:
        """Un prompt différent doit produire une clé différente."""
        key1 = ResultCache.make_key("content", "prompt_a")
        key2 = ResultCache.make_key("content", "prompt_b")
        assert key1 != key2

    def test_key_is_64_char_hex(self) -> None:
        """La clé doit être un hash SHA-256 de 64 caractères hexadécimaux."""
        key = ResultCache.make_key("x", "y")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


class TestResultCacheGetSet:
    """Tests du get/set du cache."""

    def test_miss_returns_none(self) -> None:
        """Un miss de cache doit retourner None."""
        cache = ResultCache()
        assert cache.get("nonexistent_key") is None

    def test_hit_returns_value(self) -> None:
        """Un hit de cache doit retourner la valeur stockée."""
        cache = ResultCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_set_then_get(self) -> None:
        """On doit récupérer exactement la valeur stockée."""
        cache = ResultCache()
        cache.set("k", '{"status": "success"}')
        assert cache.get("k") == '{"status": "success"}'

    def test_disabled_cache_always_miss(self) -> None:
        """Un cache désactivé doit toujours retourner None."""
        cache = ResultCache(enabled=False)
        cache.set("key", "value")
        assert cache.get("key") is None

    def test_disabled_cache_set_is_noop(self) -> None:
        """Un set sur un cache désactivé ne doit pas stocker."""
        cache = ResultCache(enabled=False)
        cache.set("key", "value")
        assert cache.stats()["size"] == 0


class TestResultCacheTTL:
    """Tests du TTL du cache."""

    def test_expired_entry_returns_none(self) -> None:
        """Une entrée expirée doit retourner None."""
        cache = ResultCache(ttl_seconds=1)
        cache.set("key", "value")
        # Simuler l'expiration en manipulant l'entrée directement
        cache._store["key"].created_at = time.time() - 2
        assert cache.get("key") is None

    def test_not_expired_entry_returns_value(self) -> None:
        """Une entrée non expirée doit retourner la valeur."""
        cache = ResultCache(ttl_seconds=3600)
        cache.set("key", "value")
        assert cache.get("key") == "value"


class TestResultCacheInvalidate:
    """Tests de l'invalidation du cache."""

    def test_invalidate_existing_key(self) -> None:
        """L'invalidation d'une clé existante doit retourner True."""
        cache = ResultCache()
        cache.set("key", "value")
        assert cache.invalidate("key") is True
        assert cache.get("key") is None

    def test_invalidate_nonexistent_key(self) -> None:
        """L'invalidation d'une clé inexistante doit retourner False."""
        cache = ResultCache()
        assert cache.invalidate("nonexistent") is False


class TestResultCacheLRU:
    """Tests de l'éviction LRU."""

    def test_lru_eviction_when_full(self) -> None:
        """Quand le cache est plein, la plus ancienne entrée doit être évincée."""
        cache = ResultCache(max_size=3)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")
        # Le cache est plein — l'ajout de "d" doit évincer l'entrée la plus ancienne
        cache.set("d", "4")
        assert len(cache._store) == 3
        assert cache.get("d") == "4"


class TestResultCacheStats:
    """Tests des statistiques du cache."""

    def test_stats_initial(self) -> None:
        """Les stats initiales doivent être à zéro."""
        cache = ResultCache()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0
        assert stats["hit_rate_percent"] == 0.0

    def test_stats_after_hit_and_miss(self) -> None:
        """Les stats doivent refléter les hits et misses."""
        cache = ResultCache()
        cache.set("key", "val")
        cache.get("key")   # hit
        cache.get("miss")  # miss
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0

    def test_clear_resets_stats(self) -> None:
        """clear() doit réinitialiser toutes les stats."""
        cache = ResultCache()
        cache.set("k", "v")
        cache.get("k")
        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["size"] == 0
