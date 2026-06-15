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
        self._connected = False

    async def connect(self) -> None:
        """Initialize connection pool and connect."""
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
                wait = 2 ** attempt
                logger.warning(
                    "Redis connection attempt %d/%d failed: %s. Retrying in %ds",
                    attempt,
                    self._max_retries,
                    exc,
                    wait,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(wait)
        raise RedisConnectionError(
            f"Could not connect to Redis after {self._max_retries} attempts"
        )

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

    async def ping(self) -> bool:
        """Health check. Returns True if Redis is reachable."""
        try:
            if self._redis is None:
                return False
            return await self._redis.ping()
        except (RedisError, ConnectionError) as exc:
            logger.error("Redis ping failed: %s", exc)
            return False

    async def get(self, key: str) -> Any:
        try:
            value = await self._redis.get(key)
            return value
        except RedisError as exc:
            logger.error("Redis GET %s failed: %s", key, exc)
            return None

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        try:
            return await self._redis.set(key, value, ex=ex)
        except RedisError as exc:
            logger.error("Redis SET %s failed: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        try:
            return await self._redis.delete(key) > 0
        except RedisError as exc:
            logger.error("Redis DEL %s failed: %s", key, exc)
            return False

    async def exists(self, key: str) -> bool:
        try:
            return await self._redis.exists(key) > 0
        except RedisError as exc:
            logger.error("Redis EXISTS %s failed: %s", key, exc)
            return False

    async def expire(self, key: str, seconds: int) -> bool:
        try:
            return await self._redis.expire(key, seconds)
        except RedisError as exc:
            logger.error("Redis EXPIRE %s failed: %s", key, exc)
            return False

    async def incr(self, key: str) -> int:
        try:
            return await self._redis.incr(key)
        except RedisError as exc:
            logger.error("Redis INCR %s failed: %s", key, exc)
            return 0

    async def setnx(self, key: str, value: str) -> bool:
        """Set if not exists (for distributed locks)."""
        try:
            return await self._redis.setnx(key, value)
        except RedisError as exc:
            logger.error("Redis SETNX %s failed: %s", key, exc)
            return False

    async def sliding_window_counter(
        self, key: str, window_seconds: int, max_requests: int
    ) -> tuple[bool, int]:
        """Returns (allowed, current_count) for sliding window rate limiting.

        Uses a Lua script to atomically check-and-increment, eliminating
        TOCTOU race conditions between ZCARD and ZADD.
        """
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
        try:
            allowed, count = await self._redis.eval(
                lua_script, 1, key, window_seconds, max_requests
            )
            return bool(allowed), int(count)
        except RedisError as exc:
            logger.error("Redis sliding window counter failed: %s", exc)
            return True, 0

    async def set_workflow_state(self, execution_id: str, state: dict) -> bool:
        try:
            return await self._redis.set(
                f"workflow:state:{execution_id}",
                json.dumps(state, default=str),
            )
        except RedisError as exc:
            logger.error("Redis set_workflow_state failed: %s", exc)
            return False

    async def get_workflow_state(self, execution_id: str) -> dict | None:
        try:
            raw = await self._redis.get(f"workflow:state:{execution_id}")
            if raw is None:
                return None
            return json.loads(raw)
        except (RedisError, json.JSONDecodeError) as exc:
            logger.error("Redis get_workflow_state failed: %s", exc)
            return None

    async def acquire_lock(self, lock_key: str, ttl: int = 30) -> bool:
        try:
            acquired = await self._redis.set(
                f"lock:{lock_key}", "1", nx=True, ex=ttl
            )
            return acquired is not None
        except RedisError as exc:
            logger.error("Redis acquire_lock failed: %s", exc)
            return False

    async def release_lock(self, lock_key: str) -> bool:
        try:
            return await self._redis.delete(f"lock:{lock_key}") > 0
        except RedisError as exc:
            logger.error("Redis release_lock failed: %s", exc)
            return False


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
