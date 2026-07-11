from __future__ import annotations

from app.rate_limiting.interface import RateLimiter, RateLimitResult
from app.rate_limiting.token_bucket import TokenBucketLimiter


class MemoryLimiter(RateLimiter):
    def __init__(self, impl: RateLimiter | None = None) -> None:
        self._impl = impl or TokenBucketLimiter()

    async def check(self, key: str, cost: int = 1) -> RateLimitResult:
        return await self._impl.check(key, cost)

    async def reset(self, key: str) -> None:
        await self._impl.reset(key)

    async def clear(self) -> None:
        await self._impl.clear()
