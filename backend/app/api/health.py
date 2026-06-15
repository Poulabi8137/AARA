from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.health import (
    HealthResponse,
    ReadinessResponse,
    LivenessResponse,
    ServiceStatus,
)

logger = get_logger("api.health")

router = APIRouter(tags=["Health"])

_start_time = time.monotonic()


async def _check_database() -> ServiceStatus:
    """Check database connectivity by acquiring a session from the pool."""
    try:
        from app.db.session import get_db
        from sqlalchemy import text

        async for db in get_db():
            db_start = time.monotonic()
            await db.execute(text("SELECT 1"))
            latency = (time.monotonic() - db_start) * 1000
            return ServiceStatus(status="healthy", latency_ms=round(latency, 2))
        return ServiceStatus(status="unhealthy", error="no database session available")
    except Exception as exc:
        return ServiceStatus(
            status="unhealthy",
            error=str(exc),
        )


async def _check_redis() -> ServiceStatus:
    """Check Redis connectivity if configured."""
    settings = get_settings()
    if not settings.redis_url or settings.redis_url == "memory":
        return ServiceStatus(status="healthy", error="not configured")
    try:
        from app.redis.client import get_redis

        redis_client = await get_redis()
        redis_start = time.monotonic()
        ok = await redis_client.ping()
        latency = (time.monotonic() - redis_start) * 1000
        return ServiceStatus(
            status="healthy" if ok else "unhealthy",
            latency_ms=round(latency, 2),
        )
    except Exception as exc:
        return ServiceStatus(status="unhealthy", error=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Detailed health check — verifies all service dependencies."""
    db_status = await _check_database()
    redis_status = await _check_redis()

    services: dict[str, ServiceStatus] = {
        "database": db_status,
        "redis": redis_status,
    }

    if db_status.status == "unhealthy":
        overall = "unhealthy"
    elif db_status.status == "degraded" or redis_status.status == "unhealthy":
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.monotonic() - _start_time, 2),
        services=services,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe — indicates whether the service can accept traffic."""
    db_status = await _check_database()

    checks = {"database": db_status}
    ready = db_status.status == "healthy"

    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        checks=checks,
    )


@router.get("/live", response_model=LivenessResponse)
async def liveness_check() -> LivenessResponse:
    """Liveness probe — indicates whether the process is alive."""
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
