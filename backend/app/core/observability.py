from __future__ import annotations

import os
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("observability")

# === Prometheus Metrics ===

HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

WORKFLOW_DURATION = Histogram(
    "workflow_duration_seconds",
    "Workflow execution duration in seconds",
    ["status"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

AGENT_DURATION = Histogram(
    "agent_duration_seconds",
    "Per-agent execution duration in seconds",
    ["agent_name", "status"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM provider request duration in seconds",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

ERROR_COUNT = Counter(
    "errors_total",
    "Total errors by type",
    ["error_type", "service"],
)

AUTH_FAILURE_COUNT = Counter(
    "auth_failures_total",
    "Authentication failures",
    ["reason"],
)

RATE_LIMIT_VIOLATIONS = Counter(
    "rate_limit_violations_total",
    "Rate limit violations",
    ["client_type", "path"],
)

QUEUE_DEPTH = Gauge(
    "queue_depth",
    "Current task queue depth",
    ["queue_name"],
)

ACTIVE_WORKFLOWS = Gauge(
    "active_workflows",
    "Currently active workflow executions",
)

# === Metrics Middleware ===


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        start = time.monotonic()
        try:
            response = await call_next(request)
            elapsed = time.monotonic() - start
            status_group = f"{response.status_code // 100}xx"
            HTTP_REQUEST_COUNT.labels(method=method, path=path, status=status_group).inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(elapsed)
            return response
        except Exception as exc:
            elapsed = time.monotonic() - start
            HTTP_REQUEST_COUNT.labels(method=method, path=path, status="5xx").inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(elapsed)
            raise


# === Setup ===


def setup_observability(app: FastAPI) -> None:
    settings = get_settings()

    # Sentry SDK
    sentry_dsn = os.environ.get("SENTRY_DSN", "") or settings.sentry_dsn
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=settings.env,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                profiles_sample_rate=settings.sentry_profiles_sample_rate,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                ],
            )
            logger.info("Sentry SDK initialized", extra={"env": settings.env})
        except Exception as exc:
            logger.warning("Failed to initialize Sentry", extra={"error": str(exc)})
    else:
        logger.info("Sentry not configured (SENTRY_DSN not set)")

    # Prometheus /metrics endpoint
    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # Metrics middleware
    app.add_middleware(MetricsMiddleware)

    logger.info("Observability initialized")


# === Metric recording helpers ===


def record_workflow_duration(duration: float, status: str) -> None:
    WORKFLOW_DURATION.labels(status=status).observe(duration)


def record_agent_duration(agent_name: str, duration: float, status: str) -> None:
    AGENT_DURATION.labels(agent_name=agent_name, status=status).observe(duration)


def record_llm_duration(provider: str, duration: float) -> None:
    LLM_REQUEST_DURATION.labels(provider=provider).observe(duration)


def record_db_query(operation: str, duration: float) -> None:
    DB_QUERY_DURATION.labels(operation=operation).observe(duration)


def record_error(error_type: str, service: str) -> None:
    ERROR_COUNT.labels(error_type=error_type, service=service).inc()


def record_auth_failure(reason: str) -> None:
    AUTH_FAILURE_COUNT.labels(reason=reason).inc()


def record_rate_limit_violation(client_type: str, path: str) -> None:
    RATE_LIMIT_VIOLATIONS.labels(client_type=client_type, path=path).inc()


def set_queue_depth(queue_name: str, depth: int) -> None:
    QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)


def set_active_workflows(count: int) -> None:
    ACTIVE_WORKFLOWS.set(count)
