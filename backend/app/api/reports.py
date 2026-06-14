from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.research_project import ResearchProject
from app.schemas.report import ReportCreate, ReportResponse, ReportListResponse
from app.services.auth_service import get_current_user
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    from app.models.research_report import ResearchReport

    user_project_ids = select(ResearchProject.id).where(
        ResearchProject.created_by == current_user.id
    ).scalar_subquery()

    count_q = select(func.count(ResearchReport.id)).where(
        ResearchReport.project_id.in_(user_project_ids)
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    q = (
        select(ResearchReport)
        .where(ResearchReport.project_id.in_(user_project_ids))
        .order_by(ResearchReport.generated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    reports = list(result.scalars().all())

    return ReportListResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        total=total,
    )


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    project_check = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == body.project_id,
            ResearchProject.created_by == current_user.id,
        )
    )
    if project_check.scalar_one_or_none() is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    service = ReportService(db)
    report = await service.create_report(data=body)
    return ReportResponse.model_validate(report)
