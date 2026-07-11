from __future__ import annotations

import pytest

from app.streaming.dispatcher_adapter import StreamEventDispatcher
from app.streaming.events import EventType
from app.streaming.manager import EventStreamManager

pytestmark = pytest.mark.asyncio


async def test_dispatch_checkpoint_created_publishes_to_manager():
    # SupervisorAgent.handle_checkpoint calls this for every checkpoint phase
    # (Research/Analysis/Idea Gen/Writing) -- must not raise and must land
    # under the right workflow_id with the checkpoint fields intact.
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_checkpoint_created(
        "wf-1", "Research", "cp-1", "Section written",
    )

    events = await manager.get_event_history("wf-1")
    assert len(events) == 1
    assert events[0].type == EventType.CHECKPOINT_CREATED
    assert events[0].data["checkpoint_id"] == "cp-1"
    assert events[0].data["phase"] == "Research"
    assert events[0].data["output_summary"] == "Section written"


async def test_dispatch_workflow_started_publishes_to_manager():
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_workflow_started("wf-1", "research", metadata={"query": "q"})

    events = await manager.get_event_history("wf-1")
    assert len(events) == 1
    assert events[0].type == EventType.WORKFLOW_STARTED
    assert events[0].data["workflow_type"] == "research"
    assert events[0].data["query"] == "q"


async def test_dispatch_workflow_completed_publishes_to_manager():
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_workflow_completed("wf-1", result={"ok": True})

    events = await manager.get_event_history("wf-1")
    assert events[0].type == EventType.WORKFLOW_COMPLETED
    assert events[0].data == {"ok": True}


async def test_dispatch_agent_started_and_completed_are_scoped_per_workflow():
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_agent_started("Research", "wf-1")
    await dispatcher.dispatch_agent_completed("Research", "wf-1", output={"papers": 3})
    await dispatcher.dispatch_agent_started("Analysis", "wf-2")

    wf1_events = await manager.get_event_history("wf-1")
    wf2_events = await manager.get_event_history("wf-2")

    assert [e.type for e in wf1_events] == [EventType.AGENT_STARTED, EventType.AGENT_COMPLETED]
    assert all(e.agent_id == "Research" for e in wf1_events)
    assert wf1_events[1].data == {"papers": 3}

    assert len(wf2_events) == 1
    assert wf2_events[0].agent_id == "Analysis"


async def test_dispatch_agent_failed_and_workflow_failed():
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_agent_failed("Writing", "wf-1", "boom")
    await dispatcher.dispatch_workflow_failed("wf-1", "fatal")

    events = await manager.get_event_history("wf-1")
    assert events[0].type == EventType.AGENT_FAILED
    assert events[0].error == "boom"
    assert events[1].type == EventType.WORKFLOW_FAILED
    assert events[1].error == "fatal"


async def test_dispatch_error_uses_workflow_id_from_context():
    manager = EventStreamManager()
    dispatcher = StreamEventDispatcher(manager)

    await dispatcher.dispatch_error("planner", "bad input", context={"workflow_id": "wf-9"})

    events = await manager.get_event_history("wf-9")
    assert len(events) == 1
    assert events[0].type == EventType.ERROR
    assert events[0].data["source"] == "planner"
