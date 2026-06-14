from __future__ import annotations

import os
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
from dramatiq.middleware import TimeLimit, Retries, AgeLimit, ShutdownNotifications

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("workers.dramatiq")


def setup_worker() -> dramatiq.Broker:
    """Configure and return the Dramatiq broker.

    Falls back to StubBroker if Redis is unavailable (for testing/dev).
    """
    settings = get_settings()

    redis_url = os.environ.get("DRAMATIQ_REDIS_URL") or settings.redis_url

    if redis_url and redis_url != "memory":
        broker = RedisBroker(url=redis_url)
        result_backend = RedisBackend(url=redis_url)

        broker.add_middleware(TimeLimit(time_limit=600_000))
        broker.add_middleware(Retries(max_retries=settings.workflow_max_retries))
        broker.add_middleware(AgeLimit(age_limit=86_400_000))
        broker.add_middleware(ShutdownNotifications())

        broker.add_middleware(Results(backend=result_backend))

        logger.info("Dramatiq broker initialized with Redis", extra={"redis_url": redis_url.replace("://", "://...@") if "@" in redis_url else redis_url})
    else:
        from dramatiq.brokers.stub import StubBroker
        broker = StubBroker()
        logger.info("Dramatiq broker initialized with StubBroker (no Redis)")

    dramatiq.set_broker(broker)
    return broker


broker = setup_worker()


@dramatiq.actor(
    max_retries=3,
    time_limit=600_000,
    queue_name="workflows",
    priority=10,
)
def run_workflow_actor(
    execution_id: str,
    user_id: str,
    query: str,
    project_id: str = "",
    objective: str = "",
) -> dict:
    """Background actor that runs the full research workflow.

    This is called by the API and runs in a Dramatiq worker process.
    Progress is tracked via the execution database record.
    """
    import asyncio
    from app.core.logging import get_logger

    log = get_logger("workers.workflow")
    log.info("starting workflow execution", extra={"execution_id": execution_id, "query": query})

    result = asyncio.run(_execute_workflow(execution_id, query, project_id, objective))

    return result


async def _execute_workflow(
    execution_id: str,
    query: str,
    project_id: str,
    objective: str,
) -> dict:
    """Internal async workflow execution with DB progress tracking."""
    from datetime import datetime, timezone
    from app.agents.state import make_initial_state
    from app.models.agent_execution import ExecutionStatus
    from app.core.observability import record_workflow_duration, ACTIVE_WORKFLOWS
    import time

    state = make_initial_state(query=query, project_id=project_id, objective=objective)
    state["execution_id"] = execution_id
    start = time.monotonic()

    ACTIVE_WORKFLOWS.inc()

    try:
        await _update_execution_status(execution_id, ExecutionStatus.RUNNING)
        await _update_execution_node(execution_id, "planner")

        final_state = await run_research_workflow(state)

        elapsed = time.monotonic() - start
        record_workflow_duration(elapsed, "completed")

        await _update_execution_complete(execution_id, final_state)

        return {"status": "completed", "execution_id": execution_id}

    except Exception as exc:
        elapsed = time.monotonic() - start
        record_workflow_duration(elapsed, "failed")

        log = get_logger("workers.workflow")
        log.exception("workflow execution failed", extra={"execution_id": execution_id})

        await _update_execution_failed(execution_id, str(exc))
        return {"status": "failed", "execution_id": execution_id, "error": str(exc)}

    finally:
        ACTIVE_WORKFLOWS.dec()


async def _update_execution_status(execution_id: str, status: ExecutionStatus) -> None:
    """Update execution status in database."""
    from sqlalchemy import update
    from app.db.session import async_session_factory
    from app.models.agent_execution import AgentExecution

    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(execution_status=status, start_time=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()


async def _update_execution_node(execution_id: str, node_name: str) -> None:
    """Update current node progress in execution metadata."""
    from sqlalchemy import select, update
    from app.db.session import async_session_factory
    from app.models.agent_execution import AgentExecution

    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        exec_obj = result.scalar_one_or_none()
        if exec_obj is None:
            return
        meta = dict(exec_obj.execution_metadata or {})
        meta["current_node"] = node_name
        history = meta.get("execution_history", [])
        history.append({"node": node_name, "timestamp": datetime.now(timezone.utc).isoformat()})
        meta["execution_history"] = history
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(execution_metadata=meta)
        )
        await session.execute(stmt)
        await session.commit()


async def _update_execution_complete(execution_id: str, state: dict) -> None:
    """Store results on execution completion."""
    import json
    from sqlalchemy import update
    from app.db.session import async_session_factory
    from app.models.agent_execution import AgentExecution, ExecutionStatus
    from datetime import datetime, timezone

    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.COMPLETED,
                end_time=datetime.now(timezone.utc),
                output_report=json.dumps(state.get("generated_report", ""), default=str),
                execution_metadata={
                    "summary_count": len(state.get("summaries", [])),
                    "gap_count": len(state.get("research_gaps", [])),
                    "execution_history": state.get("execution_history", []),
                },
            )
        )
        await session.execute(stmt)
        await session.commit()


async def _update_execution_failed(execution_id: str, error: str) -> None:
    from sqlalchemy import select, update
    from app.db.session import async_session_factory
    from app.models.agent_execution import AgentExecution, ExecutionStatus
    from datetime import datetime, timezone

    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        exec_obj = result.scalar_one_or_none()
        retry_count = (exec_obj.retry_count + 1) if exec_obj else 0
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.FAILED,
                end_time=datetime.now(timezone.utc),
                error_message=error,
                retry_count=retry_count,
            )
        )
        await session.execute(stmt)
        await session.commit()


@dramatiq.actor(queue_name="workflows", max_retries=0)
def cancel_workflow_actor(execution_id: str) -> None:
    """Cancel a running workflow by execution ID."""
    import asyncio
    asyncio.run(_cancel_execution(execution_id))


async def _cancel_execution(execution_id: str) -> None:
    from sqlalchemy import update
    from app.db.session import async_session_factory
    from app.models.agent_execution import AgentExecution, ExecutionStatus
    from datetime import datetime, timezone

    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.CANCELLED,
                end_time=datetime.now(timezone.utc),
            )
        )
        await session.execute(stmt)
        await session.commit()
