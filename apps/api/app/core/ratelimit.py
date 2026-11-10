"""A small in-memory sliding-window limiter for sign-in and registration.

It protects one server process. With several processes the limit is per process, so production
should put a shared store or the proxy's limiter in front (docs/THREAT_MODEL.md, Phase 11).
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many attempts")
        self.retry_after = retry_after


class SlidingWindow:
    def __init__(
        self, limit: int, window_seconds: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit, self.window, self.clock = limit, window_seconds, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _trim(self, key: str, now: float) -> deque[float]:
        q = self._hits[key]
        while q and now - q[0] >= self.window:
            q.popleft()
        return q

    def check(self, key: str) -> None:
        """Raise if ``key`` is already over the limit (does not count this call)."""
        with self._lock:
            now = self.clock()
            q = self._trim(key, now)
            if len(q) >= self.limit:
                raise RateLimitedError(max(1, int(self.window - (now - q[0])) + 1))

    def hit(self, key: str) -> None:
        with self._lock:
            now = self.clock()
            self._trim(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
