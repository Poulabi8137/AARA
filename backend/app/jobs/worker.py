from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.jobs.queue import QueueBackend, QueueItem
from app.observability.logging import get_logger

WorkerHandler = Callable[[QueueItem], Any]


class WorkerBackend(ABC):
    @abstractmethod
    async def process(self, item: QueueItem) -> None: ...


class Worker:
    def __init__(
        self,
        queue: QueueBackend,
        handler: WorkerHandler,
        concurrency: int = 1,
    ) -> None:
        self._queue = queue
        self._handler = handler
        self._concurrency = concurrency
        self._running = False
        self._tasks: list[asyncio.Task[Any]] = []

    async def start(self) -> None:
        self._running = True
        for _ in range(self._concurrency):
            task = asyncio.create_task(self._worker_loop())
            self._tasks.append(task)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _worker_loop(self) -> None:
        logger = get_logger("aara.jobs.worker")
        while self._running:
            try:
                item = await self._queue.dequeue(timeout=1.0)
                if item is None:
                    continue
                try:
                    await self._handler(item)
                    await self._queue.acknowledge(item.job_id)
                except Exception as exc:
                    logger.error(
                        "worker_handler_failed",
                        job_id=item.job_id,
                        error=str(exc),
                    )
                    await self._queue.requeue(item.job_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("worker_loop_error", error=str(exc))
