from __future__ import annotations

import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import GlobalConfig
from app.core.exceptions import AARAError
from app.core.rate_limit import RateLimitMiddleware
from app.observability.logging import get_logger

logger = get_logger("aara.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind correlation ID to structlog context for automatic inclusion in logs
        structlog.contextvars.bind_contextvars(correlation_id=request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        import time
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        response.headers["X-Processing-Time-Ms"] = str(round(elapsed * 1000, 2))
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app, config: GlobalConfig | None = None) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS for production
        if self._config and self._config.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # CSP — no unsafe-inline/unsafe-eval; Next.js uses nonces for inline scripts
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


class AARAErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
            return response
        except AARAError as exc:
            return JSONResponse(
                status_code=exc.error_code.http_status,
                content={
                    "error": {
                        "code": exc.error_code.code,
                        "message": exc.error_code.message,
                        "details": exc.error_code.details,
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )
        except Exception as exc:
            # A FastAPI `@app.exception_handler(Exception)` is the obvious
            # way to catch the rest, but Starlette special-cases handlers
            # registered for the bare `Exception` type into
            # ServerErrorMiddleware, which sits *outside* every middleware
            # added via add_middleware (including CORS). A handler there
            # can never get a CORS header onto its response, so the browser
            # reports any unhandled server bug as an opaque "blocked by
            # CORS policy" / network error instead of a real 500. Catching
            # it here, inside a normal middleware that CORSMiddleware
            # wraps, keeps the response inside the CORS pipeline.
            logger.error(
                "unhandled_exception",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred. Please try again later.",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )


def register_middleware(app: FastAPI) -> None:
    cors_origins = getattr(app.state, "cors_origins", ["*"])
    config = getattr(app.state, "config", None)

    # Starlette executes middleware in reverse-registration order, so the
    # *last* middleware added here becomes the *outermost* layer. Several
    # middlewares below (rate limiting, error handling) can short-circuit
    # with an early response and skip everything registered before them.
    # CORS therefore MUST be added last/outermost — otherwise a 429 or an
    # AARAError response never passes through CORSMiddleware, arrives at
    # the browser with no Access-Control-Allow-Origin header, and shows up
    # as an opaque "blocked by CORS policy" / network error instead of the
    # real status code.
    requests_per_minute = getattr(config, "rate_limit_requests_per_minute", 60)
    app.add_middleware(SecurityHeadersMiddleware, config=config)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=requests_per_minute, config=config)
    app.add_middleware(TimingMiddleware)
    app.add_middleware(AARAErrorMiddleware)

    # CORS — outermost, wraps every other middleware.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
