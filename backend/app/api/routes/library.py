from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.library import (
    DuplicateCheckResponse,
    PaperResponse,
    PaperUpdate,
    PaperUploadResponse,
    PaperVersionResponse,
)

router = APIRouter(prefix="/api/v1/library", tags=["Paper Library"])


@router.get("", response_model=PaginatedResponse[PaperResponse])
async def list_papers(
    workspace_id: str | None = Query(None),
    project_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    if workspace_id is None:
        raise HTTPException(
            status_code=422,
            detail="workspace_id is required",
        )

    service = PaperService(PaperRepository())
    items, total = await service.list_papers(
        db, workspace_id, current_user.id, (page - 1) * page_size, page_size, status
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.post("/upload", response_model=PaperUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile,
    workspace_id: str = Query(...),
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    paper = await service.upload_paper(db, current_user.id, file, workspace_id, project_id)
    return PaperUploadResponse.model_validate(paper)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    paper = await service.get_paper(db, paper_id, current_user.id)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return PaperResponse.model_validate(paper)


@router.patch("/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: str,
    body: PaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    paper = await service.update_paper(db, paper_id, current_user.id, body)
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return PaperResponse.model_validate(paper)


@router.delete("/{paper_id}", response_model=MessageResponse)
async def delete_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    await service.delete_paper(db, paper_id, current_user.id)
    return MessageResponse(message="Paper deleted")


@router.post("/{paper_id}/replace", response_model=PaperUploadResponse)
async def replace_paper(
    paper_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    paper = await service.replace_paper(db, paper_id, current_user.id, file)
    return PaperUploadResponse.model_validate(paper)


@router.get("/{paper_id}/versions", response_model=list[PaperVersionResponse])
async def get_paper_versions(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    versions = await service.get_paper_versions(db, paper_id, current_user.id)
    return versions


@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(
    workspace_id: str = Query(...),
    content_hash: str | None = Query(None),
    doi: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.paper_repository import PaperRepository
    from app.services.paper_service import PaperService

    service = PaperService(PaperRepository())
    result = await service.check_duplicate(db, workspace_id, current_user.id, content_hash, doi)
    return result
