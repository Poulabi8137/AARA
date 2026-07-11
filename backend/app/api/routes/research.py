from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_research_service
from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.common import PaginatedResponse
from app.schemas.research import (
    ResearchSessionResponse,
    ResearchSubmission,
    ResearchSubmissionResponse,
)
from app.services.research_service import ResearchService

router = APIRouter(prefix="/api/v1/research", tags=["Research"])


@router.get("/overview", response_model=dict)
async def get_research_overview(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_overview(db, current_user.id)


@router.get("/activity", response_model=dict)
async def get_research_activity(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_activity(db, current_user.id)


@router.get("/cards", response_model=list[dict])
async def get_research_cards(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_cards(db, current_user.id)


@router.get("/recent-activity", response_model=list[dict])
async def get_research_recent_activity(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_recent_activity(db, current_user.id)


@router.get("/notes", response_model=list[dict])
async def get_research_notes(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_notes(db, current_user.id)


@router.get("/reading-queue", response_model=list[dict])
async def get_research_reading_queue(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_reading_queue(db, current_user.id)


@router.get("/saved-papers", response_model=list[dict])
async def get_research_saved_papers(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.get_saved_papers(db, current_user.id)


@router.post("/queries", response_model=ResearchSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_research_query(
    body: ResearchSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.submit_query(db, current_user.id, body)


@router.get("/sessions", response_model=PaginatedResponse[ResearchSessionResponse])
async def list_sessions(
    project_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    items, total = await service.list_sessions(
        db,
        project_id,  # project_id first (ISSUE-09 fix)
        current_user.id,
        (page - 1) * page_size,
        page_size,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    session = await service.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/retrieval", response_model=ResearchSessionResponse)
async def trigger_retrieval(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.trigger_retrieval(db, session_id, current_user.id)


@router.post("/sessions/{session_id}/analysis", response_model=ResearchSessionResponse)
async def trigger_analysis(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.trigger_analysis(db, session_id, current_user.id)


@router.post("/sessions/{session_id}/writing", response_model=ResearchSessionResponse)
async def trigger_writing(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.trigger_writing(db, session_id, current_user.id)


@router.post("/sessions/{session_id}/ideas", response_model=ResearchSessionResponse)
async def trigger_ideas(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    return await service.trigger_ideas(db, session_id, current_user.id)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile,
    workspace_id: str = Query(...),
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: ResearchService = Depends(get_research_service),
):
    # ISSUE-08 fix: method is upload_paper, not upload_pdf
    return await service.upload_paper(db, workspace_id, current_user.id, file)
