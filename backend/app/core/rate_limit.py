from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.observability.logging import get_logger
from app.rate_limiting.interface import RateLimiter
from app.rate_limiting.memory import MemoryLimiter
from app.rate_limiting.token_bucket import TokenBucketLimiter

if TYPE_CHECKING:
    from app.core.config import GlobalConfig

logger = get_logger("aara.rate_limit")


def _build_limiter(config: GlobalConfig | None, requests_per_minute: int) -> RateLimiter:
    """Redis-backed when explicitly configured (RATE_LIMIT_BACKEND=redis), so
    limits are shared across instances and survive restarts; in-process
    otherwise. A single instance's in-memory limiter is fine for local dev
    but resets on every restart and is invisible to sibling instances behind
    a load balancer — not safe for a scaled deployment."""
    if config is not None and config.rate_limit_backend == "redis":
        try:
            import redis.asyncio as redis

            from app.rate_limiting.redis_limiter import RedisRateLimiter

            client = redis.from_url(config.redis_url, decode_responses=True)
            return RedisRateLimiter(
                client,
                default_max_requests=requests_per_minute,
                default_window_seconds=60.0,
            )
        except Exception:
            logger.warning("redis_rate_limiter_init_failed_falling_back_to_memory")

    limiter = TokenBucketLimiter(
        default_capacity=requests_per_minute,
        default_refill_rate=requests_per_minute / 60.0,
    )
    return MemoryLimiter(impl=limiter)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        config: GlobalConfig | None = None,
    ) -> None:
        super().__init__(app)
        self._limiter = _build_limiter(config, requests_per_minute)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        client_key = self._resolve_key(request)
        result = await self._limiter.check(client_key)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Retry after {result.retry_after:.0f} seconds.",
                        "retry_after": result.retry_after,
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
                headers={"Retry-After": str(int(result.retry_after))},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response

    def _resolve_key(self, request: Request) -> str:
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        return f"ip:{request.client.host}" if request.client else "ip:unknown"
