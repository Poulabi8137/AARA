from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


def _get_search_service():
    from app.repositories import CitationRepository, PaperRepository, ProjectRepository
    from app.services.search_service import SearchService

    return SearchService(PaperRepository(), CitationRepository(), ProjectRepository())


@router.post("", response_model=SearchResponse)
async def unified_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_search_service()
    return await service.search(db, current_user.id, body)
