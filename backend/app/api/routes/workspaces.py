from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspaces"])


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "editor"


@router.get("", response_model=PaginatedResponse[WorkspaceResponse])
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    items, total = await service.list_workspaces(db, current_user.id, (page - 1) * page_size, page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    workspace = await service.create_workspace(db, current_user.id, body)
    return WorkspaceResponse.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    workspace = await service.get_workspace(db, workspace_id, current_user.id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    workspace = await service.update_workspace(db, workspace_id, current_user.id, body)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspace_id}", response_model=MessageResponse)
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    await service.delete_workspace(db, workspace_id, current_user.id)
    return MessageResponse(message="Workspace deleted")


@router.post("/{workspace_id}/members", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    workspace_id: str,
    body: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    await service.add_member(db, workspace_id, current_user.id, body.user_id, body.role)
    return MessageResponse(message="Member added")


@router.delete("/{workspace_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    workspace_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    from app.repositories.citation_repository import CitationRepository
    from app.repositories.paper_repository import PaperRepository
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.workspace_service import WorkspaceService

    service = WorkspaceService(WorkspaceRepository(), ProjectRepository(), PaperRepository(), CitationRepository())
    await service.remove_member(db, workspace_id, current_user.id, user_id)
    return MessageResponse(message="Member removed")
