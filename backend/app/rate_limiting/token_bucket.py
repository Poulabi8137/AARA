from __future__ import annotations

import time
from dataclasses import dataclass

from app.rate_limiting.interface import RateLimiter, RateLimitResult


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    tokens: float
    last_refill: float


class TokenBucketLimiter(RateLimiter):
    def __init__(self, default_capacity: int = 100, default_refill_rate: float = 10.0) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill_rate = default_refill_rate

    def configure(self, key: str, capacity: int, refill_rate: float) -> None:
        self._buckets[key] = TokenBucket(
            capacity=capacity,
            refill_rate=refill_rate,
            tokens=float(capacity),
            last_refill=time.time(),
        )

    async def check(self, key: str, cost: int = 1) -> RateLimitResult:
        now = time.time()
        bucket = self._buckets.get(key)

        if bucket is None:
            bucket = TokenBucket(
                capacity=self._default_capacity,
                refill_rate=self._default_refill_rate,
                tokens=float(self._default_capacity),
                last_refill=now,
            )
            self._buckets[key] = bucket

        elapsed = now - bucket.last_refill
        bucket.tokens = min(
            bucket.capacity,
            bucket.tokens + elapsed * bucket.refill_rate,
        )
        bucket.last_refill = now

        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return RateLimitResult(
                allowed=True,
                remaining=int(bucket.tokens),
                reset_at=(
                    now + (bucket.capacity - bucket.tokens) / bucket.refill_rate
                    if bucket.refill_rate > 0 else now
                ),
            )

        wait_time = (
            (cost - bucket.tokens) / bucket.refill_rate
            if bucket.refill_rate > 0 else float("inf")
        )
        return RateLimitResult(
            allowed=False,
            remaining=0,
            reset_at=now + wait_time,
            retry_after=wait_time,
        )

    async def reset(self, key: str) -> None:
        self._buckets.pop(key, None)

    async def clear(self) -> None:
        self._buckets.clear()
