"""Sliding-window limiters: in memory for one process, Redis when ``REDIS_URL`` is set.

The in-memory one is exact but private to a process. With several workers or servers the limit must live
in a shared store, so ``make_limiter`` returns a Redis-backed window when Redis is configured. If Redis
cannot be reached the Redis limiter lets the request through and logs the problem: losing the limiter
must not take the whole product down (the proxy's own limits remain the outer wall).
"""

import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any, Protocol


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


class Limiter(Protocol):
    def check(self, key: str) -> None: ...
    def hit(self, key: str) -> None: ...
    def reset(self, key: str) -> None: ...


logger = logging.getLogger(__name__)


class RedisWindow:
    """The same sliding window kept in a Redis sorted set per key, shared by every process."""

    def __init__(
        self,
        client: Any,
        name: str,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.r, self.name, self.limit, self.window, self.clock = (
            client,
            name,
            limit,
            window_seconds,
            clock,
        )

    def _key(self, key: str) -> str:
        return f"rl:{self.name}:{key}"

    def check(self, key: str) -> None:
        try:
            now = self.clock()
            k = self._key(key)
            self.r.zremrangebyscore(k, 0, now - self.window)
            n = self.r.zcard(k)
            if n >= self.limit:
                oldest = self.r.zrange(k, 0, 0, withscores=True)
                wait = int(self.window - (now - oldest[0][1])) + 1 if oldest else self.window
                raise RateLimitedError(max(1, wait))
        except RateLimitedError:
            raise
        except Exception:
            logger.warning("rate limiter store unavailable; allowing the request", exc_info=True)

    def hit(self, key: str) -> None:
        try:
            now = self.clock()
            k = self._key(key)
            pipe = self.r.pipeline()
            pipe.zadd(k, {f"{now}:{uuid.uuid4().hex[:8]}": now})
            pipe.expire(k, self.window + 5)
            pipe.execute()
        except Exception:
            logger.warning("rate limiter store unavailable", exc_info=True)

    def reset(self, key: str) -> None:
        try:
            self.r.delete(self._key(key))
        except Exception:
            logger.warning("rate limiter store unavailable", exc_info=True)


_redis_clients: dict[str, Any] = {}


def make_limiter(
    name: str, limit: int, window_seconds: int, redis_url: str | None = None
) -> Limiter:
    if not redis_url:
        return SlidingWindow(limit, window_seconds)
    import redis

    client = _redis_clients.get(redis_url)
    if client is None:
        client = _redis_clients[redis_url] = redis.Redis.from_url(
            redis_url, socket_timeout=0.25, socket_connect_timeout=0.25
        )
    return RedisWindow(client, name, limit, window_seconds)
