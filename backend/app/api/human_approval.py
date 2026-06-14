from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.user import User
from app.models.human_approval import HumanApproval, ApprovalStatus
from app.models.agent_execution import AgentExecution
from app.models.research_project import ResearchProject
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/approvals", tags=["Human Approval"])
logger = get_logger("api.human_approval")


async def _get_approval_or_404(
    execution_id: str, current_user: User, db: AsyncSession
) -> HumanApproval:
    result = await db.execute(
        select(HumanApproval).where(HumanApproval.execution_id == uuid.UUID(execution_id))
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    exec_obj = await db.get(AgentExecution, approval.execution_id)
    if exec_obj:
        project_check = await db.execute(
            select(ResearchProject).where(
                ResearchProject.id == exec_obj.project_id,
                ResearchProject.created_by == current_user.id,
            )
        )
        if project_check.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.get("/pending")
async def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all pending human approvals for the current user's projects."""
    user_project_ids = select(ResearchProject.id).where(
        ResearchProject.created_by == current_user.id
    ).scalar_subquery()
    user_exec_ids = select(AgentExecution.id).where(
        AgentExecution.project_id.in_(user_project_ids)
    ).scalar_subquery()
    result = await db.execute(
        select(HumanApproval)
        .where(
            HumanApproval.execution_id.in_(user_exec_ids),
            HumanApproval.status == ApprovalStatus.PENDING,
        )
        .order_by(HumanApproval.requested_at.desc())
    )
    approvals = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "execution_id": str(a.execution_id),
            "status": a.status.value,
            "requested_at": a.requested_at.isoformat() if a.requested_at else None,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "reviewed_by": a.reviewed_by,
            "feedback": a.feedback,
        }
        for a in approvals
    ]


@router.get("/{execution_id}")
async def get_approval_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get the approval status for an execution."""
    approval = await _get_approval_or_404(execution_id, current_user, db)
    return {
        "id": str(approval.id),
        "execution_id": str(approval.execution_id),
        "status": approval.status.value,
        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
        "reviewed_by": approval.reviewed_by,
        "feedback": approval.feedback,
    }


@router.post("/{execution_id}/approve")
async def approve_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feedback: str = "",
    reviewed_by: str = "",
) -> dict[str, Any]:
    """Approve an execution to proceed to report generation."""
    approval = await _get_approval_or_404(execution_id, current_user, db)
    approval.status = ApprovalStatus.APPROVED
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.reviewed_by = reviewed_by or current_user.name or str(current_user.id)
    approval.feedback = feedback
    await db.flush()
    logger.info("execution approved", extra={"execution_id": execution_id})
    return {"status": "approved", "execution_id": execution_id}


@router.post("/{execution_id}/reject")
async def reject_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feedback: str = "",
    reviewed_by: str = "",
) -> dict[str, Any]:
    """Reject an execution with feedback."""
    approval = await _get_approval_or_404(execution_id, current_user, db)
    approval.status = ApprovalStatus.REJECTED
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.reviewed_by = reviewed_by or current_user.name or str(current_user.id)
    approval.feedback = feedback
    await db.flush()
    logger.info("execution rejected", extra={"execution_id": execution_id, "feedback": feedback})
    return {"status": "rejected", "execution_id": execution_id}


@router.post("/{execution_id}/rerun")
async def rerun_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feedback: str = "",
    reviewed_by: str = "",
) -> dict[str, Any]:
    """Request a re-run with feedback for gap detection to address."""
    approval = await _get_approval_or_404(execution_id, current_user, db)
    approval.status = ApprovalStatus.RERUN_REQUESTED
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.reviewed_by = reviewed_by or current_user.name or str(current_user.id)
    approval.feedback = feedback
    await db.flush()
    logger.info("execution rerun requested", extra={"execution_id": execution_id, "feedback": feedback})
    return {"status": "rerun_requested", "execution_id": execution_id}
