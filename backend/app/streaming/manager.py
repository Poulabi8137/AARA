from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from app.streaming.events import (
    AgentEvent,
    BaseEvent,
    EventType,
    ProgressEvent,
    TokenStreamEvent,
    WorkflowEvent,
)

Callback = Callable[[BaseEvent], Coroutine[Any, Any, None]]


class EventStreamManager:
    MAX_HISTORY = 1000

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue[BaseEvent]]] = {}
        self._callbacks: dict[str, list[Callback]] = {}
        self._history: dict[str, list[BaseEvent]] = {}

    async def publish_event(self, event: BaseEvent) -> None:
        wf_id = event.workflow_id
        if wf_id not in self._history:
            self._history[wf_id] = []
        self._history[wf_id].append(event)
        if len(self._history[wf_id]) > self.MAX_HISTORY:
            self._history[wf_id] = self._history[wf_id][-self.MAX_HISTORY:]

        queues = self._subscribers.get(wf_id, [])
        for queue in queues:
            await queue.put(event)

        callbacks = self._callbacks.get(wf_id, [])
        for cb in callbacks:
            await cb(event)

    async def subscribe(self, workflow_id: str, callback: Callback) -> None:
        if workflow_id not in self._callbacks:
            self._callbacks[workflow_id] = []
        self._callbacks[workflow_id].append(callback)

    async def unsubscribe(self, workflow_id: str, callback: Callback) -> None:
        callbacks = self._callbacks.get(workflow_id, [])
        if callback in callbacks:
            callbacks.remove(callback)

    async def get_event_history(self, workflow_id: str) -> list[BaseEvent]:
        return list(self._history.get(workflow_id, []))

    async def stream_events(self, workflow_id: str) -> AsyncGenerator[BaseEvent, None]:
        queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        if workflow_id not in self._subscribers:
            self._subscribers[workflow_id] = []
        self._subscribers[workflow_id].append(queue)

        try:
            for event in self._history.get(workflow_id, []):
                yield event
            while True:
                event = await queue.get()
                yield event
        except asyncio.CancelledError:
            pass
        finally:
            queues = self._subscribers.get(workflow_id, [])
            if queue in queues:
                queues.remove(queue)

    async def publish_agent_event(
        self,
        agent_id: str,
        workflow_id: str,
        status: str,
        **kwargs: Any,
    ) -> AgentEvent:
        event = AgentEvent(
            type=EventType.AGENT_STARTED,
            workflow_id=workflow_id,
            agent_id=agent_id,
            status=status,
            **kwargs,
        )
        await self.publish_event(event)
        return event

    async def publish_workflow_event(
        self,
        workflow_id: str,
        status: str,
        **kwargs: Any,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            status=status,
            **kwargs,
        )
        await self.publish_event(event)
        return event

    async def publish_progress(
        self,
        workflow_id: str,
        step_id: str,
        agent_id: str,
        percentage: float,
        message: str,
    ) -> ProgressEvent:
        event = ProgressEvent(
            type=EventType.PROGRESS_UPDATED,
            workflow_id=workflow_id,
            step_id=step_id,
            agent_id=agent_id,
            percentage=percentage,
            message=message,
        )
        await self.publish_event(event)
        return event

    async def publish_token(
        self,
        workflow_id: str,
        agent_id: str,
        content: str,
    ) -> TokenStreamEvent:
        event = TokenStreamEvent(
            type=EventType.TOKEN_STREAM,
            workflow_id=workflow_id,
            agent_id=agent_id,
            content=content,
        )
        await self.publish_event(event)
        return event
