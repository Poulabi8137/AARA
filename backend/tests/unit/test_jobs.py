from __future__ import annotations

import asyncio

import pytest

from app.jobs.queue import MemoryQueueBackend, QueueItem
from app.jobs.scheduler import Schedule, Scheduler
from app.jobs.task_manager import TaskManager
from app.jobs.worker import Worker


class TestTaskManager:
    @pytest.mark.asyncio
    async def test_submit_and_get(self):
        tm = TaskManager()

        async def my_task():
            pass

        task_id = await tm.submit("test", my_task())
        await asyncio.sleep(0.1)
        task = await tm.get_task(task_id)
        assert task is not None
        assert task.name == "test"
        assert task.status in ("completed", "running")

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        tm = TaskManager()

        async def my_task():
            await asyncio.sleep(0.01)

        await tm.submit("t1", my_task())
        await tm.submit("t2", my_task())
        await asyncio.sleep(0.1)
        tasks = tm.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_cancel(self):
        tm = TaskManager()

        async def slow_task():
            await asyncio.sleep(10)

        task_id = await tm.submit("slow", slow_task())
        cancelled = await tm.cancel(task_id)
        assert cancelled is True
        await asyncio.sleep(0.1)
        task = await tm.get_task(task_id)
        assert task is not None
        assert task.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        tm = TaskManager()
        cancelled = await tm.cancel("nonexistent")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_active_count(self):
        tm = TaskManager()

        async def my_task():
            await asyncio.sleep(0.5)

        await tm.submit("t1", my_task())
        assert tm.active_count == 1
        await asyncio.sleep(0.6)

    def test_clear_completed(self):
        tm = TaskManager()
        tm._tasks = {
            "1": type("T", (), {"status": "completed"})(),
            "2": type("T", (), {"status": "pending"})(),
        }
        tm.clear_completed()
        assert "2" in tm._tasks
        assert "1" not in tm._tasks


class TestMemoryQueueBackend:
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        q = MemoryQueueBackend()
        item = QueueItem(job_id="1", payload={"test": True})
        await q.enqueue(item)
        result = await q.dequeue(timeout=0.1)
        assert result is not None
        assert result.job_id == "1"

    @pytest.mark.asyncio
    async def test_dequeue_empty(self):
        q = MemoryQueueBackend()
        result = await q.dequeue(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_acknowledge(self):
        q = MemoryQueueBackend()
        item = QueueItem(job_id="1", payload={})
        await q.enqueue(item)
        await q.dequeue(timeout=0.1)
        await q.acknowledge("1")

    @pytest.mark.asyncio
    async def test_requeue(self):
        q = MemoryQueueBackend()
        item = QueueItem(job_id="1", payload={})
        await q.enqueue(item)
        await q.dequeue(timeout=0.1)
        await q.requeue("1")

    @pytest.mark.asyncio
    async def test_size(self):
        q = MemoryQueueBackend()
        assert await q.size() == 0
        await q.enqueue(QueueItem(job_id="1", payload={}))
        assert await q.size() == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        q = MemoryQueueBackend()
        await q.enqueue(QueueItem(job_id="1", payload={}))
        await q.clear()
        assert await q.size() == 0


class TestWorker:
    @pytest.mark.asyncio
    async def test_start_stop(self):
        q = MemoryQueueBackend()
        results = []

        async def handler(item: QueueItem):
            results.append(item.job_id)

        worker = Worker(q, handler, concurrency=1)
        await worker.start()
        await asyncio.sleep(0.05)
        await q.enqueue(QueueItem(job_id="1", payload={}))
        await asyncio.sleep(0.3)
        await worker.stop()
        assert len(results) >= 1


class TestScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        scheduler = Scheduler()
        calls = []

        async def my_task():
            calls.append(1)

        scheduler.register(Schedule(
            name="test", interval_seconds=0.05, handler=my_task,
        ))
        await scheduler.start()
        await asyncio.sleep(0.2)
        await scheduler.stop()
        assert len(calls) >= 1

    def test_list_schedules(self):
        scheduler = Scheduler()
        scheduler.register(Schedule(name="s1", interval_seconds=10))
        assert len(scheduler.list_schedules()) == 1
