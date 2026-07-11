from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.observability.logging import get_logger

ScheduledHandler = Callable[[], Any]


@dataclass
class Schedule:
    name: str
    cron_expression: str = ""
    interval_seconds: float = 0.0
    handler: ScheduledHandler | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class Scheduler:
    def __init__(self) -> None:
        self._schedules: list[Schedule] = []
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._running = False

    def register(self, schedule: Schedule) -> None:
        self._schedules.append(schedule)

    async def start(self) -> None:
        self._running = True
        for schedule in self._schedules:
            if schedule.enabled and schedule.interval_seconds > 0:
                task = asyncio.create_task(
                    self._run_interval(schedule)
                )
                self._tasks[schedule.name] = task

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self._tasks.clear()

    async def _run_interval(self, schedule: Schedule) -> None:
        logger = get_logger("aara.jobs.scheduler")
        while self._running:
            try:
                if schedule.handler:
                    await schedule.handler()
                await asyncio.sleep(schedule.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "scheduler_handler_failed",
                    name=schedule.name,
                    error=str(exc),
                )
                await asyncio.sleep(schedule.interval_seconds)

    def list_schedules(self) -> list[Schedule]:
        return list(self._schedules)
