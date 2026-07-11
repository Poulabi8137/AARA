from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.streaming.events import (
    AgentEvent,
    BaseEvent,
    EventType,
    ProgressEvent,
    TokenStreamEvent,
    WorkflowEvent,
)
from app.streaming.manager import EventStreamManager


class TestEventTypeEnum:
    def test_enum_has_15_values(self) -> None:
        assert len(EventType) == 15

    def test_enum_member_values(self) -> None:
        assert EventType.AGENT_STARTED == "agent.started"
        assert EventType.AGENT_COMPLETED == "agent.completed"
        assert EventType.AGENT_FAILED == "agent.failed"
        assert EventType.AGENT_RETRYING == "agent.retrying"
        assert EventType.WORKFLOW_STARTED == "workflow.started"
        assert EventType.WORKFLOW_COMPLETED == "workflow.completed"
        assert EventType.WORKFLOW_FAILED == "workflow.failed"
        assert EventType.WORKFLOW_PAUSED == "workflow.paused"
        assert EventType.WORKFLOW_RESUMED == "workflow.resumed"
        assert EventType.WORKFLOW_CANCELLED == "workflow.cancelled"
        assert EventType.PROGRESS_UPDATED == "progress.updated"
        assert EventType.TOKEN_STREAM == "token.stream"
        assert EventType.CHECKPOINT_CREATED == "checkpoint.created"
        assert EventType.CHECKPOINT_RESOLVED == "checkpoint.resolved"
        assert EventType.ERROR == "error"

    def test_enum_members_are_unique(self) -> None:
        values = [m.value for m in EventType]
        assert len(values) == len(set(values))


class TestBaseEvent:
    def test_default_creation(self) -> None:
        event = BaseEvent()
        assert event.event_id
        assert event.type == EventType.ERROR
        assert event.workflow_id == ""
        assert isinstance(event.timestamp, datetime)
        assert event.data == {}

    def test_auto_generates_event_id(self) -> None:
        event = BaseEvent()
        UUID(event.event_id)

    def test_auto_sets_timestamp(self) -> None:
        event = BaseEvent()
        assert event.timestamp is not None
        assert event.timestamp.tzinfo is UTC

    def test_creation_with_all_fields(self) -> None:
        ts = datetime.now(UTC)
        event = BaseEvent(
            event_id="custom-id",
            type=EventType.WORKFLOW_STARTED,
            workflow_id="wf-1",
            timestamp=ts,
            data={"key": "val"},
        )
        assert event.event_id == "custom-id"
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == "wf-1"
        assert event.timestamp == ts
        assert event.data == {"key": "val"}

    def test_data_is_mutable(self) -> None:
        event = BaseEvent(data={"a": 1})
        event.data["b"] = 2
        assert event.data == {"a": 1, "b": 2}


class TestAgentEvent:
    def test_creation_with_fields(self) -> None:
        event = AgentEvent(
            type=EventType.AGENT_STARTED,
            workflow_id="wf-1",
            agent_id="agent-1",
            agent_name="test-agent",
            status="running",
            output_summary="doing work",
            error=None,
            duration_ms=100,
        )
        assert event.type == EventType.AGENT_STARTED
        assert event.workflow_id == "wf-1"
        assert event.agent_id == "agent-1"
        assert event.agent_name == "test-agent"
        assert event.status == "running"
        assert event.output_summary == "doing work"
        assert event.error is None
        assert event.duration_ms == 100

    def test_inherits_base_event_fields(self) -> None:
        event = AgentEvent()
        assert event.event_id
        assert isinstance(event.timestamp, datetime)
        assert event.data == {}

    def test_optional_fields_default(self) -> None:
        event = AgentEvent()
        assert event.agent_id == ""
        assert event.agent_name == ""
        assert event.status == ""
        assert event.output_summary is None
        assert event.error is None
        assert event.duration_ms is None


class TestWorkflowEvent:
    def test_creation_with_fields(self) -> None:
        event = WorkflowEvent(
            type=EventType.WORKFLOW_COMPLETED,
            workflow_id="wf-1",
            status="completed",
            current_phase="phase-2",
            completed_steps=5,
            total_steps=10,
            error=None,
        )
        assert event.type == EventType.WORKFLOW_COMPLETED
        assert event.workflow_id == "wf-1"
        assert event.status == "completed"
        assert event.current_phase == "phase-2"
        assert event.completed_steps == 5
        assert event.total_steps == 10
        assert event.error is None

    def test_inherits_base_event_fields(self) -> None:
        event = WorkflowEvent()
        assert event.event_id
        assert isinstance(event.timestamp, datetime)

    def test_partial_fields(self) -> None:
        event = WorkflowEvent(workflow_id="wf-x", status="running")
        assert event.workflow_id == "wf-x"
        assert event.status == "running"
        assert event.current_phase == ""
        assert event.completed_steps == 0
        assert event.total_steps == 0


class TestProgressEvent:
    def test_creation_with_fraction_and_message(self) -> None:
        event = ProgressEvent(
            type=EventType.PROGRESS_UPDATED,
            workflow_id="wf-1",
            step_id="step-1",
            agent_id="agent-1",
            percentage=0.75,
            message="Processing batch 3 of 4",
        )
        assert event.type == EventType.PROGRESS_UPDATED
        assert event.workflow_id == "wf-1"
        assert event.step_id == "step-1"
        assert event.agent_id == "agent-1"
        assert event.percentage == 0.75
        assert event.message == "Processing batch 3 of 4"

    def test_default_values(self) -> None:
        event = ProgressEvent()
        assert event.step_id == ""
        assert event.agent_id == ""
        assert event.percentage == 0.0
        assert event.message == ""


class TestTokenStreamEvent:
    def test_creation_with_token_text(self) -> None:
        event = TokenStreamEvent(
            type=EventType.TOKEN_STREAM,
            workflow_id="wf-1",
            agent_id="agent-1",
            content="Hello",
            finish_reason=None,
        )
        assert event.type == EventType.TOKEN_STREAM
        assert event.workflow_id == "wf-1"
        assert event.agent_id == "agent-1"
        assert event.content == "Hello"
        assert event.finish_reason is None

    def test_creation_with_finish_reason(self) -> None:
        event = TokenStreamEvent(
            type=EventType.TOKEN_STREAM,
            workflow_id="wf-1",
            agent_id="agent-1",
            content="",
            finish_reason="stop",
        )
        assert event.finish_reason == "stop"

    def test_default_values(self) -> None:
        event = TokenStreamEvent()
        assert event.agent_id == ""
        assert event.content == ""
        assert event.finish_reason is None


class TestEventStreamManager:
    pytestmark = pytest.mark.asyncio
    async def test_publish_event_adds_to_history(self) -> None:
        manager = EventStreamManager()
        event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        await manager.publish_event(event)
        history = await manager.get_event_history("wf-1")
        assert len(history) == 1
        assert history[0].event_id == event.event_id

    async def test_subscribe_callback_receives_events(self) -> None:
        manager = EventStreamManager()
        received: list[BaseEvent] = []

        async def cb(event: BaseEvent) -> None:
            received.append(event)

        await manager.subscribe("wf-1", cb)
        event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        await manager.publish_event(event)
        assert len(received) == 1
        assert received[0].event_id == event.event_id

    async def test_unsubscribe_removes_callback(self) -> None:
        manager = EventStreamManager()
        received: list[BaseEvent] = []

        async def cb(event: BaseEvent) -> None:
            received.append(event)

        await manager.subscribe("wf-1", cb)
        await manager.unsubscribe("wf-1", cb)
        event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        await manager.publish_event(event)
        assert len(received) == 0

    async def test_unsubscribe_nonexistent_does_not_raise(self) -> None:
        manager = EventStreamManager()

        async def cb(event: BaseEvent) -> None:
            pass

        await manager.unsubscribe("wf-none", cb)

    async def test_event_history_buffer_capped_at_1000(self) -> None:
        manager = EventStreamManager()
        for i in range(1050):
            event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
            await manager.publish_event(event)
        history = await manager.get_event_history("wf-1")
        assert len(history) == 1000

    async def test_event_history_returns_most_recent_events(self) -> None:
        manager = EventStreamManager()
        ids: list[str] = []
        for i in range(1050):
            event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
            ids.append(event.event_id)
            await manager.publish_event(event)
        history = await manager.get_event_history("wf-1")
        assert history[0].event_id == ids[50]
        assert history[-1].event_id == ids[-1]

    async def test_stream_events_yields_existing_history(self) -> None:
        manager = EventStreamManager()
        event1 = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        event2 = BaseEvent(type=EventType.AGENT_COMPLETED, workflow_id="wf-1")
        await manager.publish_event(event1)
        await manager.publish_event(event2)

        collected: list[BaseEvent] = []
        async for ev in manager.stream_events("wf-1"):
            collected.append(ev)
            if len(collected) == 2:
                break

        assert len(collected) == 2
        assert collected[0].event_id == event1.event_id
        assert collected[1].event_id == event2.event_id

    async def test_stream_events_yields_new_events(self) -> None:
        manager = EventStreamManager()
        collected: list[BaseEvent] = []
        stream = manager.stream_events("wf-1")

        async def collect() -> None:
            async for ev in stream:
                collected.append(ev)
                if len(collected) == 1:
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        event = BaseEvent(type=EventType.TOKEN_STREAM, workflow_id="wf-1")
        await manager.publish_event(event)
        await task

        assert len(collected) == 1
        assert collected[0].event_id == event.event_id

    async def test_multiple_subscribers_receive_same_event(self) -> None:
        manager = EventStreamManager()
        received1: list[BaseEvent] = []
        received2: list[BaseEvent] = []

        async def cb1(event: BaseEvent) -> None:
            received1.append(event)

        async def cb2(event: BaseEvent) -> None:
            received2.append(event)

        await manager.subscribe("wf-1", cb1)
        await manager.subscribe("wf-1", cb2)
        event = BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        await manager.publish_event(event)

        assert len(received1) == 1
        assert len(received2) == 1
        assert received1[0].event_id == event.event_id
        assert received2[0].event_id == event.event_id

    async def test_subscribe_filters_by_event_type(self) -> None:
        manager = EventStreamManager()
        agent_events: list[BaseEvent] = []
        workflow_events: list[BaseEvent] = []

        async def agent_cb(event: BaseEvent) -> None:
            if event.type == EventType.AGENT_STARTED:
                agent_events.append(event)

        async def workflow_cb(event: BaseEvent) -> None:
            if event.type == EventType.WORKFLOW_STARTED:
                workflow_events.append(event)

        await manager.subscribe("wf-1", agent_cb)
        await manager.subscribe("wf-1", workflow_cb)

        await manager.publish_event(
            BaseEvent(type=EventType.AGENT_STARTED, workflow_id="wf-1")
        )
        await manager.publish_event(
            BaseEvent(type=EventType.AGENT_COMPLETED, workflow_id="wf-1")
        )
        await manager.publish_event(
            BaseEvent(type=EventType.WORKFLOW_STARTED, workflow_id="wf-1")
        )

        assert len(agent_events) == 1
        assert agent_events[0].type == EventType.AGENT_STARTED
        assert len(workflow_events) == 1
        assert workflow_events[0].type == EventType.WORKFLOW_STARTED

    async def test_event_history_empty_for_unknown_workflow(self) -> None:
        manager = EventStreamManager()
        history = await manager.get_event_history("nonexistent")
        assert history == []

    async def test_publish_agent_event(self) -> None:
        manager = EventStreamManager()
        event = await manager.publish_agent_event(
            agent_id="agent-1",
            workflow_id="wf-1",
            status="running",
            agent_name="test-agent",
        )
        assert isinstance(event, AgentEvent)
        assert event.type == EventType.AGENT_STARTED
        assert event.agent_id == "agent-1"
        assert event.workflow_id == "wf-1"
        assert event.status == "running"
        assert event.agent_name == "test-agent"

        history = await manager.get_event_history("wf-1")
        assert len(history) == 1
        assert history[0].event_id == event.event_id

    async def test_publish_workflow_event(self) -> None:
        manager = EventStreamManager()
        event = await manager.publish_workflow_event(
            workflow_id="wf-1",
            status="started",
            current_phase="init",
        )
        assert isinstance(event, WorkflowEvent)
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == "wf-1"
        assert event.status == "started"
        assert event.current_phase == "init"

        history = await manager.get_event_history("wf-1")
        assert len(history) == 1

    async def test_publish_progress(self) -> None:
        manager = EventStreamManager()
        event = await manager.publish_progress(
            workflow_id="wf-1",
            step_id="step-1",
            agent_id="agent-1",
            percentage=0.5,
            message="Halfway there",
        )
        assert isinstance(event, ProgressEvent)
        assert event.type == EventType.PROGRESS_UPDATED
        assert event.workflow_id == "wf-1"
        assert event.step_id == "step-1"
        assert event.agent_id == "agent-1"
        assert event.percentage == 0.5
        assert event.message == "Halfway there"

    async def test_publish_token(self) -> None:
        manager = EventStreamManager()
        event = await manager.publish_token(
            workflow_id="wf-1",
            agent_id="agent-1",
            content="Hello world",
        )
        assert isinstance(event, TokenStreamEvent)
        assert event.type == EventType.TOKEN_STREAM
        assert event.workflow_id == "wf-1"
        assert event.agent_id == "agent-1"
        assert event.content == "Hello world"
        assert event.finish_reason is None

    async def test_manager_cleanup_removes_subscriber_queue(self) -> None:
        manager = EventStreamManager()

        async def consume() -> None:
            async for _ in manager.stream_events("wf-1"):
                pass

        task = asyncio.create_task(consume())
        await asyncio.sleep(0.01)
        assert len(manager._subscribers.get("wf-1", [])) == 1
        task.cancel()
        await asyncio.sleep(0.01)
        assert len(manager._subscribers.get("wf-1", [])) == 0

    async def test_callback_not_invoked_after_unsubscribe(self) -> None:
        manager = EventStreamManager()
        received: list[BaseEvent] = []

        async def cb(event: BaseEvent) -> None:
            received.append(event)

        await manager.subscribe("wf-1", cb)
        await manager.unsubscribe("wf-1", cb)
        event = BaseEvent(type=EventType.ERROR, workflow_id="wf-1")
        await manager.publish_event(event)
        assert len(received) == 0
