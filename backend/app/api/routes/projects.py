from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.research import (
    ResearchProjectCreate,
    ResearchProjectResponse,
    ResearchProjectUpdate,
)

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


def _get_project_service():
    from app.repositories.project_repository import ProjectRepository
    from app.repositories.workspace_repository import WorkspaceRepository
    from app.services.project_service import ProjectService

    return ProjectService(ProjectRepository(), WorkspaceRepository())


@router.get("", response_model=PaginatedResponse[ResearchProjectResponse])
async def list_projects(
    workspace_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    items, total = await service.list_projects(
        db, workspace_id, current_user.id, (page - 1) * page_size, page_size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.post("", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ResearchProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    project = await service.create_project(db, current_user.id, body)
    return ResearchProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ResearchProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    project = await service.get_project(db, project_id, current_user.id)
    return ResearchProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ResearchProjectResponse)
async def update_project(
    project_id: str,
    body: ResearchProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    project = await service.update_project(db, project_id, current_user.id, body)
    return ResearchProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    await service.delete_project(db, project_id, current_user.id)
    return MessageResponse(message="Project deleted")


@router.post("/{project_id}/archive", response_model=ResearchProjectResponse)
async def archive_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    project = await service.archive_project(db, project_id, current_user.id)
    return ResearchProjectResponse.model_validate(project)


@router.post("/{project_id}/duplicate", response_model=ResearchProjectResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_project_service()
    project = await service.duplicate_project(db, project_id, current_user.id)
    return ResearchProjectResponse.model_validate(project)
