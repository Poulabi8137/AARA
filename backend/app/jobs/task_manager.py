from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.observability.logging import get_logger


@dataclass
class Task:
    task_id: str
    name: str
    status: str = "pending"
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._running: dict[str, asyncio.Task[Any]] = {}

    async def submit(self, name: str, coro: Any, metadata: dict[str, Any] | None = None) -> str:
        task_id = str(uuid4())
        task = Task(
            task_id=task_id,
            name=name,
            status="pending",
            created_at=datetime.now(UTC),
            metadata=metadata or {},
        )
        self._tasks[task_id] = task

        async def wrapper() -> None:
            task.status = "running"
            task.started_at = datetime.now(UTC)
            try:
                await coro
                task.status = "completed"
            except Exception as exc:
                task.status = "failed"
                task.error = str(exc)
                logger = get_logger("aara.jobs")
                logger.error("task_failed", task_id=task_id, name=name, error=str(exc))
            finally:
                task.completed_at = datetime.now(UTC)
                self._running.pop(task_id, None)

        self._running[task_id] = asyncio.create_task(wrapper())
        return task_id

    async def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: str | None = None) -> list[Task]:
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())

    async def cancel(self, task_id: str) -> bool:
        runner = self._running.get(task_id)
        if runner:
            runner.cancel()
            task = self._tasks.get(task_id)
            if task:
                task.status = "cancelled"
            return True
        return False

    async def wait_for(self, task_id: str, timeout: float | None = None) -> Task:
        runner = self._running.get(task_id)
        if runner:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(runner, timeout=timeout)
        task = self._tasks.get(task_id)
        assert task is not None
        return task

    @property
    def active_count(self) -> int:
        return len(self._running)

    def clear_completed(self) -> None:
        self._tasks = {
            tid: t for tid, t in self._tasks.items()
            if t.status in ("pending", "running")
        }
