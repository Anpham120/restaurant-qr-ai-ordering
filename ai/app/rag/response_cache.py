"""LRU response cache for AI chatbot.

Caches successful LLM responses keyed by (normalized_query, top_source_ids).
Reduces API calls and latency for repeated/similar questions.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


DEFAULT_MAX_SIZE = 500
DEFAULT_TTL_SECONDS = 300  # 5 minutes


@dataclass(frozen=True)
class CacheEntry:
    """A cached response with expiration."""
    response: dict[str, Any]
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl_seconds


class ResponseCache:
    """Thread-safe LRU cache for chat responses.

    Key is derived from normalized query + top retrieved source IDs,
    so semantically identical questions hitting the same sources
    get cache hits.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._max_size = max(1, max_size)
        self._ttl_seconds = max(0, ttl_seconds)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, query: str, source_ids: list[str]) -> dict[str, Any] | None:
        """Look up a cached response. Returns None on miss or expiry."""
        key = self._make_key(query, source_ids)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.response

    def put(self, query: str, source_ids: list[str], response: dict[str, Any]) -> None:
        """Store a response in the cache."""
        key = self._make_key(query, source_ids)
        entry = CacheEntry(
            response=response,
            created_at=time.monotonic(),
            ttl_seconds=self._ttl_seconds,
        )
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = entry
            else:
                self._cache[key] = entry
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)  # evict LRU

    def invalidate(self) -> None:
        """Clear the entire cache (e.g., when menu changes)."""
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "ttl_seconds": self._ttl_seconds,
            }

    def _make_key(self, query: str, source_ids: list[str]) -> str:
        """Create a cache key from normalized query + source IDs."""
        normalized_query = query.strip().lower()
        source_part = "|".join(sorted(source_ids[:3]))
        raw = f"{normalized_query}::{source_part}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
