"""
chatui/_rate_limiter.py
Thread-safe sliding-window rate limiter.
"""
from __future__ import annotations

import threading
import time

from ._constants import MAX_RATE_LIMIT_HITS


class _RateLimiter:
    """Thread-safe sliding-window limiter (per key) with bounded entries."""

    def __init__(self, max_requests: int = 60, window: float = 60.0):
        self._max = max_requests
        self._window = window
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self._window]
            if len(hits) >= self._max:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits

            if len(self._hits) > MAX_RATE_LIMIT_HITS:
                self._hits = {k: v for k, v in self._hits.items() if v}
            return True
