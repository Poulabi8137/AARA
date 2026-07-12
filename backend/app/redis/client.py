from __future__ import annotations

import asyncio
import json
from typing import Any

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("redis.client")

_redis_client: RedisClient | None = None


class RedisClient:
    """Async Redis client with connection pooling and retry logic."""

    def __init__(self, url: str, pool_size: int = 10, max_retries: int = 3):
        self._url = url
        self._pool_size = pool_size
        self._max_retries = max_retries
        self._redis: Redis | None = None
        self._pool = None
        self._connected = False
        self._fake_redis = None

    async def connect(self) -> None:
        """Initialize connection pool and connect."""
        if self._url and self._url.lower() in ("memory", ""):
            self._fake_redis = self._create_fake_redis()
            self._connected = True
            logger.info("Using in-memory Redis (fakeredis)")
            return

        attempt = 0
        while attempt < self._max_retries:
            try:
                self._pool = ConnectionPool.from_url(
                    self._url,
                    max_connections=self._pool_size,
                    decode_responses=True,
                )
                self._redis = Redis(connection_pool=self._pool)
                await self._redis.ping()
                self._connected = True
                logger.info("Connected to Redis", extra={"url": self._url})
                return
            except (RedisConnectionError, RedisError, ConnectionError) as exc:
                attempt += 1
                wait = 2**attempt
                logger.warning(
                    "Redis connection attempt %d/%d failed: %s. Retrying in %ds",
                    attempt,
                    self._max_retries,
                    exc,
                    wait,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(wait)
        self._fake_redis = self._create_fake_redis()
        self._connected = True
        logger.info("Redis unavailable, using in-memory fallback (fakeredis)")

    @staticmethod
    def _create_fake_redis():
        try:
            from fakeredis import FakeAsyncRedis

            r = FakeAsyncRedis()
            return r
        except ImportError:
            logger.warning("fakeredis not installed, using dict-based stub")
            return _DictRedisStub()

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception as exc:
                logger.warning("Error closing Redis connection: %s", exc)
        if self._pool is not None:
            await self._pool.disconnect()
        self._connected = False
        logger.info("Redis connection closed")

    @property
    def _r(self):
        return self._fake_redis if self._fake_redis is not None else self._redis

    async def ping(self) -> bool:
        """Health check. Returns True if Redis is reachable."""
        try:
            r = self._r
            if r is None:
                return False
            return await r.ping()
        except (RedisError, ConnectionError) as exc:
            logger.error("Redis ping failed: %s", exc)
            return False

    async def get(self, key: str) -> Any:
        try:
            r = self._r
            value = await r.get(key)
            if isinstance(value, bytes):
                value = value.decode()
            return value
        except (RedisError, Exception) as exc:
            logger.error("Redis GET %s failed: %s", key, exc)
            return None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        try:
            r = self._r
            result = await r.set(key, value, ex=ex)
            return result if isinstance(result, bool) else result is not None
        except (RedisError, Exception) as exc:
            logger.error("Redis SET %s failed: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        try:
            r = self._r
            result = await r.delete(key)
            return result > 0
        except (RedisError, Exception) as exc:
            logger.error("Redis DEL %s failed: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        try:
            r = self._r
            result = await r.exists(key)
            return result > 0
        except (RedisError, Exception) as exc:
            logger.error("Redis EXISTS %s failed: %s", key, exc)
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            r = self._r
            return await r.expire(key, seconds)
        except (RedisError, Exception) as exc:
            logger.error("Redis EXPIRE %s failed: %s", key, exc)
            return False

    async def incr(self, key: str) -> int:
        try:
            r = self._r
            return await r.incr(key)
        except (RedisError, Exception) as exc:
            logger.error("Redis INCR %s failed: %s", key, exc)
            return 0

    async def setnx(self, key: str, value: str) -> bool:
        """Set if not exists (for distributed locks)."""
        try:
            r = self._r
            result = await r.setnx(key, value)
            return result if isinstance(result, bool) else result is not None
        except (RedisError, Exception) as exc:
            logger.error("Redis SETNX %s failed: %s", key, exc)
            return False

    async def sliding_window_counter(
        self, key: str, window_seconds: int, max_requests: int
    ) -> tuple[bool, int]:
        try:
            r = self._r
            if hasattr(r, "eval"):
                lua_script = """
                    local key = KEYS[1]
                    local window_seconds = tonumber(ARGV[1])
                    local max_requests = tonumber(ARGV[2])
                    local now = redis.call('TIME')
                    local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
                    local window_start = now_ms - window_seconds * 1000
                    redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
                    local current = redis.call('ZCARD', key)
                    if current < max_requests then
                        redis.call('ZADD', key, now_ms, tostring(now_ms))
                        redis.call('EXPIRE', key, window_seconds)
                        return {1, current + 1}
                    end
                    return {0, current}
                """
                allowed, count = await r.eval(
                    lua_script, 1, key, window_seconds, max_requests
                )
                return bool(allowed), int(count)
        except (RedisError, Exception) as exc:
            logger.error("Redis sliding window counter failed: %s", exc)
        return True, 0

    async def set_workflow_state(self, execution_id: str, state: dict) -> bool:
        return await self.set(
            f"workflow:state:{execution_id}",
            json.dumps(state, default=str),
        )

    async def get_workflow_state(self, execution_id: str) -> dict | None:
        raw = await self.get(f"workflow:state:{execution_id}")
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("Redis get_workflow_state decode failed: %s", exc)
            return None

    async def acquire_lock(self, lock_key: str, ttl: int = 30) -> bool:
        return await self.setnx(f"lock:{lock_key}", "1") and await self.expire(
            f"lock:{lock_key}", ttl
        )

    async def release_lock(self, lock_key: str) -> bool:
        return await self.delete(f"lock:{lock_key}")

    async def eval(self, script: str, numkeys: int, *args: Any) -> Any:
        try:
            r = self._r
            if hasattr(r, "eval"):
                return await r.eval(script, numkeys, *args)
        except Exception as exc:
            logger.warning("Redis EVAL failed: %s", exc)
        return None


async def get_redis() -> RedisClient:
    """Get or create the global Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = RedisClient(
            url=settings.redis_url,
            pool_size=settings.redis_pool_size,
            max_retries=settings.redis_max_retries,
        )
        await _redis_client.connect()
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection gracefully."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class _DictRedisStub:
    """Minimal dict-based stub when neither redis nor fakeredis is available."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self._expiry: dict[str, float] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        import time

        if key in self._expiry and time.monotonic() > self._expiry[key]:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._data[key] = value
        if ex is not None:
            import time

            self._expiry[key] = time.monotonic() + ex
        return True

    async def delete(self, key: str) -> int:
        return 1 if self._data.pop(key, None) is not None else 0

    async def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._data:
            import time

            self._expiry[key] = time.monotonic() + seconds
            return True
        return False

    async def incr(self, key: str) -> int:
        val = int(self._data.get(key, "0")) + 1
        self._data[key] = str(val)
        return val

    async def setnx(self, key: str, value: str) -> bool:
        if key not in self._data:
            self._data[key] = value
            return True
        return False
