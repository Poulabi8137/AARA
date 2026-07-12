from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.schemas.session import SessionCreate, SessionResponse, SessionListResponse
from app.services.auth_service import get_current_user
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Research Sessions"])


async def _check_project_owner(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> None:
    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.created_by == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    user_project_ids = (
        select(ResearchProject.id)
        .where(ResearchProject.created_by == current_user.id)
        .scalar_subquery()
    )

    count_q = select(func.count(ResearchSession.id)).where(
        ResearchSession.project_id.in_(user_project_ids)
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    q = (
        select(ResearchSession)
        .where(ResearchSession.project_id.in_(user_project_ids))
        .order_by(ResearchSession.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    sessions = list(result.scalars().all())

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    await _check_project_owner(body.project_id, current_user, db)
    service = SessionService(db)
    session = await service.create_session(data=body)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    service = SessionService(db)
    session = await service.get_session(session_id=session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    await _check_project_owner(session.project_id, current_user, db)
    return SessionResponse.model_validate(session)
