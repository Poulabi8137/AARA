from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.health.framework import HealthCheckResult


@dataclass
class DependencyConfig:
    name: str
    required: bool = True
    timeout: float = 5.0


class DependencyHealthCheck(ABC):
    def __init__(self, config: DependencyConfig) -> None:
        self.config = config

    @abstractmethod
    async def check(self) -> HealthCheckResult: ...

    @property
    def name(self) -> str:
        return self.config.name


class DependencyHealthRegistry:
    def __init__(self) -> None:
        self._dependencies: dict[str, DependencyHealthCheck] = {}

    def register(self, check: DependencyHealthCheck) -> None:
        self._dependencies[check.name] = check

    async def check_all(self) -> dict[str, HealthCheckResult]:
        results: dict[str, HealthCheckResult] = {}
        for name, check in self._dependencies.items():
            try:
                results[name] = await check.check()
            except Exception as exc:
                results[name] = HealthCheckResult(
                    name=name, healthy=False, message=str(exc),
                )
        return results

    async def is_all_healthy(self) -> bool:
        results = await self.check_all()
        return all(r.healthy for r in results.values())

    def list_dependencies(self) -> list[str]:
        return list(self._dependencies.keys())
