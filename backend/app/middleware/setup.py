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
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        request.state.request_id = request_id

        response = await call_next(request)

        elapsed = time.monotonic() - start
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed * 1000, 2),
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(RateLimitMiddleware)
