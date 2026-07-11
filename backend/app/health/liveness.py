from __future__ import annotations

import time

from app.health.framework import HealthCheckResult


class LivenessProbe:
    def __init__(self, timeout: float = 30.0) -> None:
        self._last_activity: float = time.time()
        self._timeout = timeout
        self._alive = True

    def mark_activity(self) -> None:
        self._last_activity = time.time()

    async def is_alive(self) -> bool:
        if time.time() - self._last_activity > self._timeout:
            self._alive = False
        return self._alive

    async def check(self) -> HealthCheckResult:
        alive = await self.is_alive()
        return HealthCheckResult(
            name="liveness",
            healthy=alive,
            message="process is alive" if alive else "process heartbeat timeout",
        )
