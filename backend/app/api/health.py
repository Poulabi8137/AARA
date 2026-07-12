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


async def _check_chromadb() -> ServiceStatus:
    """Check ChromaDB connectivity if configured."""
    settings = get_settings()
    if not hasattr(settings, "chroma_host") or not settings.chroma_host:
        return ServiceStatus(status="healthy", error="not configured")

    try:
        import httpx
        from urllib.parse import urljoin

        chroma_url = (
            f"http://{settings.chroma_host}:{getattr(settings, 'chroma_port', 8000)}"
        )
        health_url = urljoin(chroma_url, "/api/v1/heartbeat")

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
            latency = (time.monotonic() - start) * 1000
            if response.status_code == 200:
                return ServiceStatus(
                    status="healthy",
                    latency_ms=round(latency, 2),
                    extra={"version": response.json().get("version", "unknown")},
                )
            else:
                return ServiceStatus(
                    status="unhealthy",
                    error=f"HTTP {response.status_code}",
                    latency_ms=round(latency, 2),
                )
    except Exception as exc:
        return ServiceStatus(status="unhealthy", error=str(exc))


async def _check_llm_provider() -> ServiceStatus:
    """Check LLM provider connectivity if configured."""
    settings = get_settings()

    if settings.llm_provider == "mock":
        return ServiceStatus(status="healthy", error="mock provider")

    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key or settings.gemini_api_key == "":
            return ServiceStatus(status="degraded", error="no API key configured")

        try:
            import httpx

            start = time.monotonic()
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "AARA-Health-Check",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test with a minimal Gemini request
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                payload = {"contents": [{"parts": [{"text": "test"}]}]}

                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    params={"key": settings.gemini_api_key},
                )
                latency = (time.monotonic() - start) * 1000

                if response.status_code == 200:
                    return ServiceStatus(
                        status="healthy",
                        latency_ms=round(latency, 2),
                        extra={
                            "provider": settings.llm_provider,
                            "model": settings.llm_model,
                        },
                    )
                elif response.status_code == 429:
                    return ServiceStatus(
                        status="degraded",
                        error="API quota exceeded",
                        latency_ms=round(latency, 2),
                    )
                else:
                    return ServiceStatus(
                        status="unhealthy",
                        error=f"HTTP {response.status_code}",
                        latency_ms=round(latency, 2),
                    )
        except Exception as exc:
            return ServiceStatus(status="unhealthy", error=str(exc))

    return ServiceStatus(status="healthy", error="not tested")


async def _check_disk_space() -> ServiceStatus:
    """Check available disk space."""
    try:
        import shutil
        import os

        # Check current directory disk space
        disk_usage = shutil.disk_usage(os.getcwd())
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        used_percent = (1 - disk_usage.free / disk_usage.total) * 100

        if free_gb < 1.0:  # Less than 1 GB free
            return ServiceStatus(
                status="degraded",
                error=f"Low disk space: {free_gb:.1f} GB free",
                extra={
                    "free_gb": round(free_gb, 1),
                    "total_gb": round(total_gb, 1),
                    "used_percent": round(used_percent, 1),
                },
            )

        return ServiceStatus(
            status="healthy",
            extra={
                "free_gb": round(free_gb, 1),
                "total_gb": round(total_gb, 1),
                "used_percent": round(used_percent, 1),
            },
        )
    except Exception as exc:
        return ServiceStatus(status="unhealthy", error=str(exc))


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Detailed health check — verifies all service dependencies."""
    db_status = await _check_database()
    redis_status = await _check_redis()
    chromadb_status = await _check_chromadb()
    llm_provider_status = await _check_llm_provider()
    disk_space_status = await _check_disk_space()

    services: dict[str, ServiceStatus] = {
        "database": db_status,
        "redis": redis_status,
        "chromadb": chromadb_status,
        "llm_provider": llm_provider_status,
        "disk_space": disk_space_status,
    }

    if any(s.status == "unhealthy" for s in services.values()):
        overall = "unhealthy"
    elif any(s.status == "degraded" for s in services.values()):
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.monotonic() - _start_time, 2),
        services=services,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness probe — indicates whether the service can accept traffic."""
    db_status = await _check_database()
    redis_status = await _check_redis()

    checks = {
        "database": db_status,
        "redis": redis_status,
    }

    # Ready if both database and redis are healthy (redis can be not configured)
    ready = db_status.status == "healthy" and (
        redis_status.status == "healthy" or not redis_status.error
    )

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
