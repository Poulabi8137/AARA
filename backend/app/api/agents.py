from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.registry import AgentRegistry
from app.models.agent_execution import AgentExecution, ExecutionStatus
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentExecutionResponse,
    ExecutionListResponse,
    CancelResponse,
    AgentInfoResponse,
    AgentListResponse,
    ExecutionStatusResponse,
)
from app.db.session import get_async_session
from app.core.logging import get_logger
from app.services.auth_service import get_current_user
from app.tasks.workflow import run_research_workflow_task, cancel_workflow_task

logger = get_logger("api.agents")
router = APIRouter(prefix="/agents", tags=["agents"])


async def _check_execution_owner(
    execution_id: uuid.UUID, user: User, session: AsyncSession
) -> AgentExecution:
    """Verify that the current user owns the execution's project."""
    exec_obj = await session.get(AgentExecution, execution_id)
    if exec_obj is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    result = await session.execute(
        select(ResearchProject).where(
            ResearchProject.id == exec_obj.project_id,
            ResearchProject.created_by == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_obj


@router.post("/run", response_model=AgentRunResponse, status_code=202)
async def run_workflow(
    request: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    execution_id = uuid.uuid4()

    execution = AgentExecution(
        id=execution_id,
        project_id=uuid.UUID(request.project_id) if request.project_id else uuid.uuid4(),
        agent_name="research_workflow",
        execution_status=ExecutionStatus.PENDING,
        input_query=request.query,
        thread_id=str(uuid.uuid4()),
        execution_metadata={"objective": request.objective or "", "user_id": str(current_user.id)},
        start_time=datetime.now(timezone.utc),
    )
    session.add(execution)
    await session.commit()

    result = await run_research_workflow_task(
        execution_id=str(execution_id),
        user_id=str(current_user.id),
        query=request.query,
        project_id=str(execution.project_id),
        objective=request.objective or "",
    )

    logger.info("workflow enqueued", extra={"execution_id": str(execution_id)})
    return AgentRunResponse(
        execution_id=execution_id,
        status=ExecutionStatus.PENDING.value,
        thread_id=execution.thread_id,
        message=result.get("message", "Workflow queued for background execution"),
    )


@router.get("/executions/{execution_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Poll the status of a workflow execution."""
    await _check_execution_owner(execution_id, current_user, session)

    q = select(
        AgentExecution.id,
        AgentExecution.execution_status,
        AgentExecution.thread_id,
        AgentExecution.start_time,
        AgentExecution.end_time,
        AgentExecution.error_message,
    ).where(AgentExecution.id == execution_id)

    result = await session.execute(q)
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionStatusResponse(
        id=row.id,
        execution_status=row.execution_status.value,
        thread_id=row.thread_id,
        start_time=row.start_time,
        end_time=row.end_time,
        error_message=row.error_message,
    )


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """List agent executions accessible to the current user."""
    from sqlalchemy import select, func

    user_project_ids = select(ResearchProject.id).where(
        ResearchProject.created_by == current_user.id
    ).scalar_subquery()

    count_q = select(func.count()).select_from(AgentExecution).where(
        AgentExecution.project_id.in_(user_project_ids)
    )
    total_result = await session.execute(count_q)
    total = total_result.scalar_one()

    q = (
        select(AgentExecution)
        .where(AgentExecution.project_id.in_(user_project_ids))
        .order_by(AgentExecution.start_time.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(q)
    executions = result.scalars().all()

    return ExecutionListResponse(
        executions=[AgentExecutionResponse.model_validate(e) for e in executions],
        total=total,
    )


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Get a specific execution's full details."""
    exec_obj = await _check_execution_owner(execution_id, current_user, session)
    return AgentExecutionResponse.model_validate(exec_obj)


@router.post("/cancel/{execution_id}", response_model=CancelResponse)
async def cancel_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Cancel a running or pending execution via Dramatiq cancel actor."""
    exec_obj = await _check_execution_owner(execution_id, current_user, session)

    if exec_obj.execution_status not in (ExecutionStatus.PENDING, ExecutionStatus.RUNNING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel execution with status: {exec_obj.execution_status.value}",
        )

    await cancel_workflow_task(str(execution_id))

    logger.info("cancel enqueued", extra={"execution_id": str(execution_id)})
    return CancelResponse(
        execution_id=execution_id,
        status=ExecutionStatus.CANCELLED.value,
        message="Cancel enqueued for background execution",
    )


@router.get("/registry", response_model=AgentListResponse)
async def list_registered_agents() -> Any:
    """List all agents registered in the agent registry."""
    agents = AgentRegistry.list_agents()
    return AgentListResponse(
        agents=[AgentInfoResponse(**a) for a in agents]
    )
