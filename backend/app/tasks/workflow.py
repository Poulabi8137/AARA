from __future__ import annotations

from app.workers.dramatiq_worker import run_workflow_actor, cancel_workflow_actor
from app.core.logging import get_logger

logger = get_logger("tasks.workflow")


async def run_research_workflow_task(
    execution_id: str,
    user_id: str,
    query: str,
    project_id: str = "",
    objective: str = "",
) -> dict:
    """Enqueue a research workflow execution as a background task.

    Returns immediately with the execution ID for status polling.
    The actual workflow runs in a Dramatiq worker.
    """
    logger.info(
        "enqueuing workflow task",
        extra={"execution_id": execution_id, "query": query[:50]},
    )

    run_workflow_actor.send(
        execution_id=execution_id,
        user_id=user_id,
        query=query,
        project_id=project_id,
        objective=objective,
    )

    return {
        "status": "queued",
        "execution_id": execution_id,
        "message": "Workflow queued for background execution",
    }


async def cancel_workflow_task(execution_id: str) -> dict:
    """Cancel a running workflow."""
    cancel_workflow_actor.send(execution_id=execution_id)
    return {"status": "cancelling", "execution_id": execution_id}
