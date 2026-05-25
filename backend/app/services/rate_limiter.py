"""Minimum-interval rate limiter.

Designed for protecting an upstream API with a per-second burst cap
(Alpha Vantage's free tier is documented at "1 request per second").
Process-local — fine for a single uvicorn worker. If we later move to
multiple workers, this becomes a Redis token bucket.
"""

from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger(__name__)


class MinIntervalRateLimiter:
    """Blocks callers so that any two `wait()` returns are ≥ min_interval_s apart.

    Thread-safe. Holding the lock through the sleep is intentional — it
    serializes concurrent callers cleanly (later threads queue up while
    the current thread waits its turn).
    """

    def __init__(self, min_interval_s: float) -> None:
        if min_interval_s < 0:
            raise ValueError("min_interval_s must be >= 0")
        self.min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._next_allowed: float = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                log.debug("Throttle: sleeping %.3fs to enforce %.3fs interval",
                          sleep_for, self.min_interval_s)
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval_s
