from __future__ import annotations

from typing import Callable

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("middleware.rate_limit")


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter.

    Rate limits are defined as tuples of (window_seconds, max_requests).
    Applies to authenticated users by user_id, unauthenticated by IP.
    Redis client is accessed lazily from request.app.state.redis_client
    to allow initialization during the lifespan startup event.
    """

    RATE_LIMITS: dict[str, list[tuple[int, int]]] = {
        "/auth/login": [(60, 5)],           # 5 req/min
        "/auth/register": [(60, 3)],         # 3 req/min
        "/documents/upload": [(3600, 20)],   # 20 req/hour
        "/agents/run": [(3600, 10)],         # 10 req/hour
    }

    DEFAULT_LIMITS = [(60, 30)]  # 30 req/min default

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics"):
            return await call_next(request)

        limits = self._get_limits(request.url.path)
        client_id = await self._get_client_id(request)

        for window, max_req in limits:
            allowed, remaining, retry_after = await self._check_limit(
                client_id, request.url.path, window, max_req
            )
            if not allowed:
                raise RateLimitExceeded(retry_after=retry_after)

        response = await call_next(request)
        return response

    async def _check_limit(
        self, client_id: str, path: str, window: int, max_req: int
    ) -> tuple[bool, int, int]:
        """
        Sliding window counter using Redis sorted sets.
        Returns (allowed, remaining, retry_after).
        If Redis is unavailable, allow the request (fail open).
        """
        redis = getattr(self._app.state, "redis_client", None)
        if redis is None:
            return True, max_req, 0

        try:
            key = f"ratelimit:{path}:{client_id}"
            allowed, count = await redis.sliding_window_counter(key, window, max_req)
            remaining = max(0, max_req - count)
            retry_after = window if not allowed else 0
            return allowed, remaining, retry_after
        except Exception:
            logger.warning("rate limit check failed, allowing request", exc_info=True)
            return True, max_req, 0

    async def _get_client_id(self, request: Request) -> str:
        """Get authenticated user ID or IP address."""
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "id"):
            return f"user:{user.id}"
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host}" if request.client else "ip:unknown"

    def _get_limits(self, path: str) -> list[tuple[int, int]]:
        for prefix, limits in self.RATE_LIMITS.items():
            if path.startswith(prefix):
                return limits
        return self.DEFAULT_LIMITS
