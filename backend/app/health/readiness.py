from __future__ import annotations

from dataclasses import dataclass

from app.health.framework import HealthChecker, HealthCheckResult


@dataclass
class ReadinessState:
    db_ready: bool = False
    cache_ready: bool = False
    event_bus_ready: bool = False
    providers_ready: bool = False
    startup_complete: bool = False


class ReadinessProbe:
    def __init__(self, health_checker: HealthChecker) -> None:
        self._checker = health_checker
        self._state = ReadinessState()

    def mark_ready(self, component: str) -> None:
        if hasattr(self._state, component):
            setattr(self._state, component, True)

    def mark_not_ready(self, component: str) -> None:
        if hasattr(self._state, component):
            setattr(self._state, component, False)

    async def is_ready(self) -> bool:
        checks = await self._checker.run_all()
        return all(c.healthy for c in checks)

    async def check(self) -> HealthCheckResult:
        ready = await self.is_ready()
        return HealthCheckResult(
            name="readiness",
            healthy=ready,
            message="system is ready" if ready else "system is not ready",
        )

    def get_state(self) -> ReadinessState:
        return self._state
