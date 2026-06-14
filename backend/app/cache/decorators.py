from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import json
from typing import Any, Callable, Optional

from app.cache.service import CacheService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.redis.client import get_redis

logger = get_logger("cache.decorators")


def _make_cache_key(prefix: str, func: Callable, args: tuple, kwargs: dict) -> str:
    """Generate a deterministic cache key from function name and arguments."""
    bound = inspect.signature(func).bind(*args, **kwargs)
    bound.apply_defaults()
    args_dict = bound.arguments
    args_json = json.dumps(args_dict, sort_keys=True, default=str)
    args_hash = hashlib.sha256(args_json.encode()).hexdigest()[:16]
    return f"{prefix}:{func.__module__}:{func.__qualname__}:{args_hash}"


def cached(
    ttl: int | None = None,
    key_prefix: str = "cache",
) -> Callable:
    """
    Decorator that caches function return values in Redis.

    Works for both sync and async functions. Generates a cache key from
    the function's module, qualified name, and a hash of its arguments.

    Usage:
        @cached(ttl=300, key_prefix="myapp")
        async def expensive_function(a, b):
            ...
    """
    if ttl is None:
        ttl = get_settings().default_cache_ttl

    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            redis = await get_redis()
            service = CacheService(redis, default_ttl=ttl)
            key = _make_cache_key(key_prefix, func, args, kwargs)

            cached_value = await service.get(key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            await service.set(key, result, ttl=ttl)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            loop = asyncio.new_event_loop()
            try:
                redis = loop.run_until_complete(get_redis())
                service = CacheService(redis, default_ttl=ttl)
                key = _make_cache_key(key_prefix, func, args, kwargs)

                cached_value = loop.run_until_complete(service.get(key))
                if cached_value is not None:
                    return cached_value

                result = func(*args, **kwargs)
                loop.run_until_complete(service.set(key, result, ttl=ttl))
                return result
            finally:
                loop.close()

        return async_wrapper if is_async else sync_wrapper

    return decorator


def invalidate_cache(key_prefix: str = "cache") -> Callable:
    """
    Decorator that invalidates cached values after a function runs.

    Usage:
        @invalidate_cache(key_prefix="myapp")
        async def update_data(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            redis = await get_redis()
            key_pattern = f"{key_prefix}:*"
            keys = await redis._redis.keys(key_pattern)
            if keys:
                await redis._redis.delete(*keys)
                logger.debug("Invalidated %d keys matching %s", len(keys), key_pattern)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            loop = asyncio.new_event_loop()
            try:
                result = func(*args, **kwargs)
                redis = loop.run_until_complete(get_redis())
                key_pattern = f"{key_prefix}:*"
                keys = loop.run_until_complete(redis._redis.keys(key_pattern))
                if keys:
                    loop.run_until_complete(redis._redis.delete(*keys))
                    logger.debug("Invalidated %d keys matching %s", len(keys), key_pattern)
                return result
            finally:
                loop.close()

        return async_wrapper if is_async else sync_wrapper

    return decorator
