from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.observability.logging import get_logger


@dataclass
class HealthCheckResult:
    name: str
    healthy: bool
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    def __init__(self) -> None:
        self._checks: dict[str, Any] = {}

    def register(self, name: str, check_fn: Any) -> None:
        self._checks[name] = check_fn

    def unregister(self, name: str) -> None:
        self._checks.pop(name, None)

    async def run_all(self) -> list[HealthCheckResult]:
        import time
        results: list[HealthCheckResult] = []
        logger = get_logger("aara.health")
        for name, check_fn in self._checks.items():
            start = time.time()
            try:
                result = await check_fn()
                latency = (time.time() - start) * 1000
                if isinstance(result, HealthCheckResult):
                    result.latency_ms = latency
                    results.append(result)
                elif isinstance(result, bool):
                    results.append(HealthCheckResult(
                        name=name,
                        healthy=result,
                        latency_ms=latency,
                    ))
                else:
                    results.append(HealthCheckResult(
                        name=name,
                        healthy=True,
                        message=str(result),
                        latency_ms=latency,
                    ))
            except Exception as exc:
                latency = (time.time() - start) * 1000
                results.append(HealthCheckResult(
                    name=name,
                    healthy=False,
                    message=str(exc),
                    latency_ms=latency,
                ))
                logger.error("health_check_failed", name=name, error=str(exc))
        return results

    async def is_healthy(self) -> bool:
        results = await self.run_all()
        return all(r.healthy for r in results)

    async def summary(self) -> dict[str, Any]:
        results = await self.run_all()
        return {
            "healthy": all(r.healthy for r in results),
            "checks": {
                r.name: {
                    "healthy": r.healthy,
                    "message": r.message,
                    "latency_ms": round(r.latency_ms, 2),
                }
                for r in results
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def list_checks(self) -> list[str]:
        return list(self._checks.keys())
