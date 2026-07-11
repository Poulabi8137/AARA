from __future__ import annotations

import time
from typing import Any

from app.observability.logging import get_logger
from app.rate_limiting.interface import RateLimiter, RateLimitResult


class RedisRateLimiter(RateLimiter):
    """Fixed-window rate limiter backed by Redis.

    Unlike MemoryLimiter, counters live in Redis so limits are shared across
    every app instance and survive restarts/redeploys. If Redis is
    unreachable, requests fail open (are allowed) rather than taking down
    the API over a cache outage.
    """

    def __init__(
        self,
        redis_client: Any,
        default_max_requests: int = 60,
        default_window_seconds: float = 60.0,
        key_prefix: str = "ratelimit",
    ) -> None:
        self._redis = redis_client
        self._default_max_requests = default_max_requests
        self._default_window_seconds = default_window_seconds
        self._key_prefix = key_prefix
        self._logger = get_logger("aara.rate_limit.redis")

    async def check(self, key: str, cost: int = 1) -> RateLimitResult:
        redis_key = f"{self._key_prefix}:{key}"
        max_requests = self._default_max_requests
        window_seconds = self._default_window_seconds

        try:
            count = await self._redis.incrby(redis_key, cost)
            if count == cost:
                await self._redis.expire(redis_key, max(1, int(window_seconds)))
            ttl = await self._redis.ttl(redis_key)
            retry_after = float(ttl) if ttl and ttl > 0 else window_seconds
        except Exception:
            self._logger.warning("redis_rate_limit_unavailable", key=key)
            return RateLimitResult(
                allowed=True,
                remaining=max_requests,
                reset_at=time.time() + window_seconds,
            )

        allowed = count <= max_requests
        remaining = max(0, max_requests - count)
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=time.time() + retry_after,
            retry_after=0.0 if allowed else retry_after,
        )

    async def reset(self, key: str) -> None:
        try:
            await self._redis.delete(f"{self._key_prefix}:{key}")
        except Exception:
            self._logger.warning("redis_rate_limit_reset_failed", key=key)

    async def clear(self) -> None:
        try:
            cursor = 0
            pattern = f"{self._key_prefix}:*"
            while True:
                cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            self._logger.warning("redis_rate_limit_clear_failed")
