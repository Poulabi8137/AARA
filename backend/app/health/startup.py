from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.observability.logging import get_logger


@dataclass
class StartupValidationResult:
    name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class StartupValidator:
    def __init__(self) -> None:
        self._validations: list[Any] = []
        self._results: list[StartupValidationResult] = []
        self._startup_time: datetime | None = None

    def register(self, name: str, validation_fn: Any) -> None:
        self._validations.append((name, validation_fn))

    async def validate_all(self) -> list[StartupValidationResult]:
        self._startup_time = datetime.now(UTC)
        self._results.clear()
        logger = get_logger("aara.startup")
        for name, fn in self._validations:
            try:
                result = await fn()
                if isinstance(result, StartupValidationResult):
                    self._results.append(result)
                elif isinstance(result, bool):
                    self._results.append(StartupValidationResult(
                        name=name, passed=result,
                    ))
            except Exception as exc:
                self._results.append(StartupValidationResult(
                    name=name, passed=False, message=str(exc),
                ))
                logger.error("startup_validation_failed", name=name, error=str(exc))
        return self._results

    def all_passed(self) -> bool:
        return all(r.passed for r in self._results)

    def get_results(self) -> list[StartupValidationResult]:
        return list(self._results)

    def get_failures(self) -> list[StartupValidationResult]:
        return [r for r in self._results if not r.passed]
