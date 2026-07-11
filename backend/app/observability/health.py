from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class HealthStatus:
    name: str
    status: str
    message: str
    timestamp: datetime
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    overall_status: str
    services: list[HealthStatus]
    timestamp: datetime
    version: str
    uptime: float


class HealthChecker:
    def __init__(self, version: str = "0.1.0", db_available: bool = True) -> None:
        self._start_time = time.time()
        self._version = version
        self._db_available = db_available

    def check_liveness(self) -> HealthReport:
        services: list[HealthStatus] = [
            HealthStatus(
                name="application",
                status="healthy",
                message="Application process is running",
                timestamp=datetime.now(UTC),
                details={"uptime_seconds": time.time() - self._start_time},
            )
        ]
        return HealthReport(
            overall_status="healthy",
            services=services,
            timestamp=datetime.now(UTC),
            version=self._version,
            uptime=time.time() - self._start_time,
        )

    async def check_readiness(self) -> HealthReport:
        services: list[HealthStatus] = []
        overall_status = "healthy"

        database_status = await self._check_database()
        if database_status.status != "healthy":
            overall_status = "unhealthy"
        services.append(database_status)

        return HealthReport(
            overall_status=overall_status,
            services=services,
            timestamp=datetime.now(UTC),
            version=self._version,
            uptime=time.time() - self._start_time,
        )

    async def check(self) -> HealthReport:
        services: list[HealthStatus] = []
        overall_status = "healthy"

        database_status = await self._check_database()
        if database_status.status != "healthy":
            overall_status = "unhealthy"
        services.append(database_status)

        cache_status = self._check_cache()
        if cache_status.status != "healthy":
            overall_status = "degraded"
        services.append(cache_status)

        return HealthReport(
            overall_status=overall_status,
            services=services,
            timestamp=datetime.now(UTC),
            version=self._version,
            uptime=time.time() - self._start_time,
        )

    async def _check_database(self) -> HealthStatus:
        if not self._db_available:
            return HealthStatus(
                name="database",
                status="unhealthy",
                message="Database service not available",
                timestamp=datetime.now(UTC),
                details={"error": "Database not configured"},
            )
        try:
            from sqlalchemy import text

            from app.core.database import get_db
            async for db in get_db():
                await db.execute(text("SELECT 1"))
                break
            return HealthStatus(
                name="database",
                status="healthy",
                message="Database connection OK",
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            return HealthStatus(
                name="database",
                status="unhealthy",
                message=f"Database error: {str(e)}",
                timestamp=datetime.now(UTC),
                details={"error": str(e)},
            )

    def _check_cache(self) -> HealthStatus:
        try:
            from app.services.cache import get_cache
            get_cache()
            return HealthStatus(
                name="cache",
                status="healthy",
                message="Cache service OK",
                timestamp=datetime.now(UTC),
            )
        except ImportError:
            return HealthStatus(
                name="cache",
                status="degraded",
                message="Cache service not configured",
                timestamp=datetime.now(UTC),
            )
        except Exception as e:
            return HealthStatus(
                name="cache",
                status="degraded",
                message=f"Cache service error: {str(e)}",
                timestamp=datetime.now(UTC),
                details={"error": str(e)},
            )
