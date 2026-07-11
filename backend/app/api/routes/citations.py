from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.citation import (
    CitationCreate,
    CitationExportRequest,
    CitationExportResponse,
    CitationLibrarySummary,
    CitationResponse,
    CitationUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/api/v1/citations", tags=["Citations"])


def _get_citation_service():
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.services.citation_service import CitationService

    return CitationService(CitationRepository(), PaperRepository())


@router.get("", response_model=PaginatedResponse[CitationResponse])
async def list_citations(
    workspace_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    items, total = await service.list_citations(
        db, workspace_id, current_user.id, (page - 1) * page_size, page_size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.post("", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
async def create_citation(
    body: CitationCreate,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    citation = await service.create_citation(db, workspace_id, current_user.id, body)
    return CitationResponse.model_validate(citation)


@router.get("/summary", response_model=CitationLibrarySummary)
async def get_citation_summary(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    return await service.get_library_summary(db, workspace_id, current_user.id)


@router.get("/{citation_id}", response_model=CitationResponse)
async def get_citation(
    citation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    citation = await service.get_citation(db, citation_id, current_user.id)
    return CitationResponse.model_validate(citation)


@router.patch("/{citation_id}", response_model=CitationResponse)
async def update_citation(
    citation_id: str,
    body: CitationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    citation = await service.update_citation(db, citation_id, current_user.id, body)
    return CitationResponse.model_validate(citation)


@router.delete("/{citation_id}", response_model=MessageResponse)
async def delete_citation(
    citation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    await service.delete_citation(db, citation_id, current_user.id)
    return MessageResponse(message="Citation deleted")


@router.post("/export", response_model=CitationExportResponse)
async def export_citations(
    body: CitationExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_citation_service()
    return await service.export_citations(db, current_user.id, body)
