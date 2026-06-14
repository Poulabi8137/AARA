from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.state import ResearchState
from app.core.logging import get_logger

logger = get_logger("graphs.human_approval")


async def human_approval_node(state: ResearchState) -> dict[str, Any]:
    """Human approval checkpoint between gap detection and report generation.

    Creates a HumanApproval record in PostgreSQL and pauses the workflow
    for human review. The workflow resumes when the API updates the record.

    If approval is skipped (configuration), passes through immediately.
    """
    from app.core.config import get_settings
    from app.db.session import async_session_factory
    from app.models.human_approval import HumanApproval, ApprovalStatus

    settings = get_settings()

    execution_id = state.get("execution_id", state.get("project_id", ""))
    gaps = state.get("research_gaps", [])
    critical_gaps = [g for g in gaps if isinstance(g, dict) and g.get("severity") == "critical"]

    logger.info(
        "human approval checkpoint",
        extra={
            "execution_id": execution_id or "unknown",
            "gap_count": len(gaps),
            "critical_gap_count": len(critical_gaps),
        },
    )

    if not settings.require_human_approval:
        state["approval_status"] = "skipped"
        return state

    state["approval_status"] = "awaiting_approval"

    # Persist approval record to PostgreSQL
    try:
        from sqlalchemy import select as _select

        exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id

        async with async_session_factory() as db_session:
            result = await db_session.execute(
                _select(HumanApproval).where(HumanApproval.execution_id == exec_uuid)
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                approval = HumanApproval(
                    id=uuid.uuid4(),
                    execution_id=exec_uuid,
                    status=ApprovalStatus.PENDING,
                    requested_at=datetime.now(timezone.utc),
                )
                db_session.add(approval)
                await db_session.flush()
                logger.info("human approval record created", extra={"execution_id": execution_id})
    except Exception as exc:
        logger.error("failed to persist human approval", extra={"error": str(exc)})

    state["approval_data"] = {
        "status": "pending",
        "gaps_summary": {
            "total": len(gaps),
            "critical": len(critical_gaps),
            "high": len([g for g in gaps if isinstance(g, dict) and g.get("severity") == "high"]),
            "medium": len([g for g in gaps if isinstance(g, dict) and g.get("severity") == "medium"]),
            "low": len([g for g in gaps if isinstance(g, dict) and g.get("severity") == "low"]),
        },
    }

    logger.info("workflow awaiting human approval", extra={"execution_id": execution_id})
    return state
