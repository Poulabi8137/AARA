from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimerResult:
    name: str
    duration_ms: float
    tags: dict[str, str] = field(default_factory=dict)
    success: bool = True


class PerformanceTimer:
    def __init__(self, metrics_collector: Any | None = None) -> None:
        self._measurements: list[TimerResult] = []
        self._metrics = metrics_collector

    @asynccontextmanager
    async def measure(
        self, name: str, tags: dict[str, str] | None = None
    ) -> AsyncGenerator[None, Any]:
        start = time.time()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration_ms = (time.time() - start) * 1000
            result = TimerResult(
                name=name,
                duration_ms=duration_ms,
                tags=tags or {},
                success=success,
            )
            self._measurements.append(result)
            if self._metrics:
                self._metrics.observe(
                    f"timer.{name}",
                    duration_ms,
                    tags={"success": str(success).lower(), **(tags or {})},
                )

    def get_measurements(self, name: str | None = None) -> list[TimerResult]:
        if name:
            return [m for m in self._measurements if m.name == name]
        return list(self._measurements)

    def get_average(self, name: str) -> float:
        measurements = [m for m in self._measurements if m.name == name]
        if not measurements:
            return 0.0
        return sum(m.duration_ms for m in measurements) / len(measurements)

    def clear(self) -> None:
        self._measurements.clear()
