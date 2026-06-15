from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

settings = get_settings()
logger = get_logger("middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging with correlation ID and user context.

    Generates a unique request_id per request, captures user identity from
    the auth state, measures execution time, and logs a structured JSON entry.
    Also propagates correlation_id from incoming X-Correlation-ID header.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID", request_id)
        start = time.monotonic()

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        extra = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": response.status_code,
            "execution_time_ms": elapsed_ms,
        }

        # Attach user_id if available from auth (set by get_current_user)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            extra["user_id"] = str(user_id)

        logger.info("request completed", extra=extra)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(RateLimitMiddleware)
