from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import get_logger


settings = get_settings()
logger = get_logger("exceptions")


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        correlation_id = getattr(request.state, "correlation_id", request_id)

        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error.get("loc", [])),
                    "message": error.get("msg", "Validation error"),
                    "type": error.get("type", ""),
                }
            )

        error_context = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "error_type": "validation",
            "path": str(request.url),
            "method": request.method,
            "errors": errors,
            "timestamp": time.time(),
        }

        logger.warning("validation error", extra=error_context)

        # Send to Sentry if configured
        if hasattr(settings, "sentry_dsn") and settings.sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.capture_event(
                    event_type="validation_error",
                    message="Request validation failed",
                    extra=error_context,
                    tags={
                        "request_id": request_id,
                        "correlation_id": correlation_id,
                        "endpoint": str(request.url),
                        "method": request.method,
                    },
                )
            except ImportError:
                pass

        response = JSONResponse(
            status_code=422,
            content={"detail": "Request validation failed", "errors": errors},
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        correlation_id = getattr(request.state, "correlation_id", request_id)

        error_context = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "error_type": "database",
            "path": str(request.url),
            "method": request.method,
            "error_message": str(exc),
            "timestamp": time.time(),
        }

        logger.error("database error", extra=error_context)

        # Send to Sentry if configured
        if hasattr(settings, "sentry_dsn") and settings.sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(
                    exc,
                    event_type="database_error",
                    extra=error_context,
                    tags={
                        "request_id": request_id,
                        "correlation_id": correlation_id,
                        "endpoint": str(request.url),
                        "method": request.method,
                    },
                )
            except ImportError:
                pass

        response = JSONResponse(
            status_code=500,
            content={"detail": "An internal database error occurred"},
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        correlation_id = getattr(request.state, "correlation_id", request_id)

        error_context = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "error_type": "unhandled",
            "path": str(request.url),
            "method": request.method,
            "error_message": str(exc),
            "error_class": exc.__class__.__name__,
            "timestamp": time.time(),
        }

        logger.error("unhandled exception", extra=error_context)

        # Send to Sentry if configured
        if hasattr(settings, "sentry_dsn") and settings.sentry_dsn:
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(
                    exc,
                    event_type="unhandled_exception",
                    extra=error_context,
                    tags={
                        "request_id": request_id,
                        "correlation_id": correlation_id,
                        "endpoint": str(request.url),
                        "method": request.method,
                    },
                )
            except ImportError:
                pass

        response = JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
