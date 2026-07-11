from __future__ import annotations

import pytest

from app.rate_limiting.memory import MemoryLimiter
from app.rate_limiting.redis_limiter import RedisRateLimiter
from app.rate_limiting.sliding_window import SlidingWindowLimiter
from app.rate_limiting.token_bucket import TokenBucketLimiter


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis, enough to exercise
    RedisRateLimiter's fixed-window counter logic without a real server."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._ttls: dict[str, int] = {}
        self.raise_on_call = False

    async def incrby(self, key: str, amount: int) -> int:
        if self.raise_on_call:
            raise ConnectionError("redis unavailable")
        self._counts[key] = self._counts.get(key, 0) + amount
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds

    async def ttl(self, key: str) -> int:
        return self._ttls.get(key, -1)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._counts.pop(key, None)
            self._ttls.pop(key, None)

    async def scan(self, cursor: int = 0, match: str = "*", count: int = 100):
        prefix = match.rstrip("*")
        matched = [k for k in self._counts if k.startswith(prefix)]
        return 0, matched


class TestTokenBucketLimiter:
    @pytest.mark.asyncio
    async def test_check_allows(self):
        limiter = TokenBucketLimiter(default_capacity=10, default_refill_rate=10)
        result = await limiter.check("user:1")
        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_check_blocks_when_empty(self):
        limiter = TokenBucketLimiter(default_capacity=1, default_refill_rate=0.1)
        await limiter.check("user:1")
        result = await limiter.check("user:1")
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_configure(self):
        limiter = TokenBucketLimiter()
        limiter.configure("premium", capacity=1000, refill_rate=100)
        result = await limiter.check("premium")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = TokenBucketLimiter(default_capacity=1, default_refill_rate=1)
        await limiter.check("user:1")
        await limiter.reset("user:1")
        result = await limiter.check("user:1")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_clear(self):
        limiter = TokenBucketLimiter()
        await limiter.check("user:1")
        await limiter.clear()
        assert len(limiter._buckets) == 0


class TestSlidingWindowLimiter:
    @pytest.mark.asyncio
    async def test_check_allows(self):
        limiter = SlidingWindowLimiter(default_max_requests=10, default_window_ms=1000)
        result = await limiter.check("user:1")
        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_check_blocks(self):
        limiter = SlidingWindowLimiter(default_max_requests=1, default_window_ms=1000)
        await limiter.check("user:1")
        result = await limiter.check("user:1")
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_configure(self):
        limiter = SlidingWindowLimiter()
        limiter.configure("premium", max_requests=100, window_ms=5000)
        result = await limiter.check("premium")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset(self):
        limiter = SlidingWindowLimiter(default_max_requests=1, default_window_ms=1000)
        await limiter.check("user:1")
        await limiter.reset("user:1")
        window = limiter._windows.get("user:1")
        assert window is None or len(window) == 0

    @pytest.mark.asyncio
    async def test_clear(self):
        limiter = SlidingWindowLimiter()
        await limiter.check("user:1")
        await limiter.clear()
        assert len(limiter._windows) == 0


class TestRedisRateLimiter:
    @pytest.mark.asyncio
    async def test_check_allows_under_limit(self):
        limiter = RedisRateLimiter(FakeRedis(), default_max_requests=10, default_window_seconds=60)
        result = await limiter.check("user:1")
        assert result.allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_check_blocks_over_limit(self):
        redis = FakeRedis()
        limiter = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)
        await limiter.check("user:1")
        result = await limiter.check("user:1")
        assert result.allowed is False
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_shared_across_limiter_instances(self):
        """The whole point of the Redis backend: two middleware instances
        (e.g. two app replicas) sharing one Redis see the same counter."""
        redis = FakeRedis()
        limiter_a = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)
        limiter_b = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)

        result_a = await limiter_a.check("user:1")
        result_b = await limiter_b.check("user:1")

        assert result_a.allowed is True
        assert result_b.allowed is False

    @pytest.mark.asyncio
    async def test_fails_open_when_redis_unavailable(self):
        redis = FakeRedis()
        redis.raise_on_call = True
        limiter = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)

        result = await limiter.check("user:1")

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset_clears_key(self):
        redis = FakeRedis()
        limiter = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)
        await limiter.check("user:1")
        await limiter.reset("user:1")
        result = await limiter.check("user:1")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_clear_removes_all_prefixed_keys(self):
        redis = FakeRedis()
        limiter = RedisRateLimiter(redis, default_max_requests=1, default_window_seconds=60)
        await limiter.check("user:1")
        await limiter.check("user:2")
        await limiter.clear()
        assert redis._counts == {}

    @pytest.mark.asyncio
    async def test_cost_greater_than_one(self):
        redis = FakeRedis()
        limiter = RedisRateLimiter(redis, default_max_requests=10, default_window_seconds=60)
        result = await limiter.check("user:1", cost=5)
        assert result.allowed is True
        assert result.remaining == 5


class TestMemoryLimiter:
    @pytest.mark.asyncio
    async def test_defaults_to_token_bucket(self):
        limiter = MemoryLimiter()
        result = await limiter.check("key")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_with_sliding_window(self):
        sw = SlidingWindowLimiter(default_max_requests=5, default_window_ms=1000)
        limiter = MemoryLimiter(impl=sw)
        result = await limiter.check("key")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_reset_and_clear(self):
        limiter = MemoryLimiter()
        await limiter.check("key")
        await limiter.reset("key")
        await limiter.clear()


class TestBuildLimiter:
    @pytest.fixture(autouse=True)
    def _valid_keys_env(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("ENCRYPTION_KEY", "b" * 44)

    def test_defaults_to_memory_when_no_config(self):
        from app.core.rate_limit import _build_limiter

        limiter = _build_limiter(None, 60)
        assert isinstance(limiter, MemoryLimiter)

    def test_defaults_to_memory_when_backend_not_redis(self, monkeypatch):
        from app.core.config import GlobalConfig
        from app.core.rate_limit import _build_limiter

        monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
        config = GlobalConfig()
        limiter = _build_limiter(config, 60)
        assert isinstance(limiter, MemoryLimiter)

    def test_uses_redis_when_backend_is_redis(self, monkeypatch):
        from app.core.config import GlobalConfig
        from app.core.rate_limit import _build_limiter

        monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")
        config = GlobalConfig()
        limiter = _build_limiter(config, 60)
        assert isinstance(limiter, RedisRateLimiter)
