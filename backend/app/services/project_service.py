from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.research_session import ResearchSession
from app.repositories import ProjectRepository, WorkspaceRepository
from app.schemas.research import (
    ResearchProjectCreate,
    ResearchProjectResponse,
    ResearchProjectUpdate,
)


class ProjectService:
    def __init__(
        self,
        repo: ProjectRepository,
        workspace_repo: WorkspaceRepository,
    ) -> None:
        self._repo = repo
        self._workspace_repo = workspace_repo

    async def create_project(
        self, db: AsyncSession, user_id: str, data: ResearchProjectCreate
    ) -> ResearchProjectResponse:
        workspace = await self._workspace_repo.get(db, data.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        project = await self._repo.create(
            db,
            workspace_id=data.workspace_id,
            name=data.name,
            description=data.description,
            research_goal=data.research_goal,
            key_questions=data.key_questions,
        )

        return ResearchProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            research_goal=project.research_goal,
            key_questions=project.key_questions,
            session_count=0,
            paper_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def get_project(
        self, db: AsyncSession, project_id: str, user_id: str
    ) -> ResearchProjectResponse:
        project = await self._repo.get(db, project_id)
        workspace = await self._workspace_repo.get(db, project.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        session_count = await self._count_sessions(db, project_id)
        paper_count = 0

        return ResearchProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            research_goal=project.research_goal,
            key_questions=project.key_questions,
            session_count=session_count,
            paper_count=paper_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def update_project(
        self, db: AsyncSession, project_id: str, user_id: str, data: ResearchProjectUpdate
    ) -> ResearchProjectResponse:
        project = await self._repo.get(db, project_id)
        workspace = await self._workspace_repo.get(db, project.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        update_kwargs = data.model_dump(exclude_unset=True)
        if update_kwargs:
            project = await self._repo.update(db, project_id, **update_kwargs)

        session_count = await self._count_sessions(db, project_id)

        return ResearchProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            research_goal=project.research_goal,
            key_questions=project.key_questions,
            session_count=session_count,
            paper_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def delete_project(
        self, db: AsyncSession, project_id: str, user_id: str
    ) -> None:
        project = await self._repo.get(db, project_id)
        workspace = await self._workspace_repo.get(db, project.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)
        await self._repo.delete(db, project_id)

    async def archive_project(
        self, db: AsyncSession, project_id: str, user_id: str
    ) -> ResearchProjectResponse:
        project = await self._repo.get(db, project_id)
        workspace = await self._workspace_repo.get(db, project.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        project = await self._repo.archive(db, project_id)

        return ResearchProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            research_goal=project.research_goal,
            key_questions=project.key_questions,
            session_count=await self._count_sessions(db, project_id),
            paper_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def duplicate_project(
        self, db: AsyncSession, project_id: str, user_id: str, new_name: str | None = None
    ) -> ResearchProjectResponse:
        original = await self._repo.get(db, project_id)
        workspace = await self._workspace_repo.get(db, original.workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        name = new_name or f"{original.name} (Copy)"
        project = await self._repo.duplicate(db, project_id, name)

        return ResearchProjectResponse(
            id=project.id,
            workspace_id=project.workspace_id,
            name=project.name,
            description=project.description,
            status=project.status,
            research_goal=project.research_goal,
            key_questions=project.key_questions,
            session_count=0,
            paper_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    async def list_projects(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        skip: int,
        limit: int,
    ) -> tuple[list[ResearchProjectResponse], int]:
        workspace = await self._workspace_repo.get(db, workspace_id)
        await self._verify_workspace_access(db, workspace, user_id)

        projects = await self._repo.get_by_workspace(db, workspace_id, skip=skip, limit=limit)
        total = len(await self._repo.get_by_workspace(db, workspace_id))

        results = []
        for proj in projects:
            session_count = await self._count_sessions(db, proj.id)
            results.append(
                ResearchProjectResponse(
                    id=proj.id,
                    workspace_id=proj.workspace_id,
                    name=proj.name,
                    description=proj.description,
                    status=proj.status,
                    research_goal=proj.research_goal,
                    key_questions=proj.key_questions,
                    session_count=session_count,
                    paper_count=0,
                    created_at=proj.created_at,
                    updated_at=proj.updated_at,
                )
            )

        return results, total

    async def _verify_workspace_access(
        self, db: AsyncSession, workspace: Any, user_id: str
    ) -> None:
        if workspace.owner_id == user_id:
            return
        role = await self._workspace_repo.get_member_role(db, workspace.id, user_id)
        if role is None:
            raise AuthorizationError("User does not have access to this workspace")

    async def _count_sessions(self, db: AsyncSession, project_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(ResearchSession)
            .where(ResearchSession.project_id == project_id)
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
