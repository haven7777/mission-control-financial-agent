"""In-memory TTL cache.

Process-local; sufficient for a single uvicorn worker. Designed for
caching expensive upstream calls (e.g. Alpha Vantage GLOBAL_QUOTE /
OVERVIEW), where the daily quota is the binding constraint.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Generic, TypeVar

log = logging.getLogger(__name__)

V = TypeVar("V")


class TTLCache(Generic[V]):
    """Thread-safe key→value store with per-entry monotonic-clock expiry."""

    def __init__(self, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, V]] = {}

    def get(self, key: str) -> V | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: V) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
