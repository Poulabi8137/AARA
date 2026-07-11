from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueueItem:
    job_id: str
    payload: dict[str, Any]
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class QueueBackend(ABC):
    @abstractmethod
    async def enqueue(self, item: QueueItem) -> None: ...

    @abstractmethod
    async def dequeue(self, timeout: float = 1.0) -> QueueItem | None: ...

    @abstractmethod
    async def acknowledge(self, job_id: str) -> None: ...

    @abstractmethod
    async def requeue(self, job_id: str) -> None: ...

    @abstractmethod
    async def size(self) -> int: ...

    @abstractmethod
    async def clear(self) -> None: ...


class MemoryQueueBackend(QueueBackend):
    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, int, QueueItem]] = asyncio.PriorityQueue()
        self._counter = 0
        self._in_flight: dict[str, QueueItem] = {}

    async def enqueue(self, item: QueueItem) -> None:
        self._counter += 1
        priority = -item.priority
        await self._queue.put((priority, self._counter, item))

    async def dequeue(self, timeout: float = 1.0) -> QueueItem | None:
        try:
            _, _, item = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            self._in_flight[item.job_id] = item
            return item
        except TimeoutError:
            return None

    async def acknowledge(self, job_id: str) -> None:
        self._in_flight.pop(job_id, None)

    async def requeue(self, job_id: str) -> None:
        item = self._in_flight.pop(job_id, None)
        if item:
            await self.enqueue(item)

    async def size(self) -> int:
        return self._queue.qsize()

    async def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._in_flight.clear()
