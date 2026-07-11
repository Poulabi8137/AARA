from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_dashboard_service
from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.dashboard import (
    DashboardResponse,
    EvaluationScoreResponse,
    ProviderUsageResponse,
    TokenUsageResponse,
    WorkflowStatusResponse,
)
from app.services.dashboard_service import DashboardService
from app.streaming.events import BaseEvent, EventType

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

_TERMINAL_EVENT_TYPES = {
    EventType.WORKFLOW_COMPLETED,
    EventType.WORKFLOW_FAILED,
    EventType.WORKFLOW_CANCELLED,
}


def _serialize_event(event: BaseEvent) -> str:
    event_type = event.type.value if hasattr(event.type, "value") else str(event.type)
    payload = {
        "event_id": event.event_id,
        "type": event_type,
        "workflow_id": event.workflow_id,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "data": event.data,
        "agent_id": getattr(event, "agent_id", None),
        "status": getattr(event, "status", None),
        "step_id": getattr(event, "step_id", None),
        "percentage": getattr(event, "percentage", None),
        "message": getattr(event, "message", None),
        "error": getattr(event, "error", None),
    }
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    dashboard = await service.get_dashboard_stats(db, current_user.id)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No workflow activity found")
    return dashboard


@router.get("/activity", response_model=list[dict])
async def get_dashboard_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_dashboard_activity(db, current_user.id, limit)


@router.get("/workflows/{workflow_id}", response_model=DashboardResponse)
async def get_workflow_dashboard(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_full_dashboard(db, workflow_id, current_user.id)


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_workflow_status(db, workflow_id, current_user.id)


@router.get("/workflows/{workflow_id}/stream")
async def stream_workflow_events(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Live Server-Sent Events feed of agent/workflow/progress events for a
    workflow, so the Agent Workspace can render execution as it happens
    instead of polling a snapshot. Access is checked before the stream opens;
    the stream itself closes on the workflow's terminal event so it doesn't
    hold the request open (and its DB session) indefinitely."""
    await service.verify_workflow_access(db, workflow_id, current_user.id)

    async def event_source():
        yield ": connected\n\n"
        async for event in service.stream_events(workflow_id):
            yield _serialize_event(event)
            if event.type in _TERMINAL_EVENT_TYPES:
                break

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/workflows/{workflow_id}/tokens", response_model=TokenUsageResponse)
async def get_token_usage(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_token_usage(db, workflow_id, current_user.id)


@router.get("/workflows/{workflow_id}/providers", response_model=list[ProviderUsageResponse])
async def get_provider_usage(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_provider_usage(db, workflow_id, current_user.id)


@router.get("/workflows/{workflow_id}/evaluation", response_model=list[EvaluationScoreResponse])
async def get_evaluation_scores(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_evaluation_scores(db, workflow_id, current_user.id)


@router.get("/workflows/{workflow_id}/timeline", response_model=list[dict])
async def get_event_timeline(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_event_timeline(db, workflow_id, current_user.id)


@router.get("/workspaces/{workspace_id}/papers", response_model=list[dict])
async def get_dashboard_papers(
    workspace_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_papers_for_dashboard(db, workspace_id, current_user.id, limit)


@router.get("/workspaces/{workspace_id}/citations", response_model=list[dict])
async def get_dashboard_citations(
    workspace_id: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_citations_for_dashboard(db, workspace_id, current_user.id, limit)


@router.get("/ai/stats", response_model=dict)
async def get_dashboard_ai_stats(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    return await service.get_ai_stats_for_dashboard(db, current_user.id)
