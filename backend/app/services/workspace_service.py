from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceSettings
from app.repositories import (
    CitationRepository,
    PaperRepository,
    ProjectRepository,
    WorkspaceRepository,
)
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate


class WorkspaceService:
    def __init__(
        self,
        repo: WorkspaceRepository,
        project_repo: ProjectRepository,
        paper_repo: PaperRepository,
        citation_repo: CitationRepository,
    ) -> None:
        self._repo = repo
        self._project_repo = project_repo
        self._paper_repo = paper_repo
        self._citation_repo = citation_repo

    async def create_workspace(
        self, db: AsyncSession, user_id: str, data: WorkspaceCreate
    ) -> WorkspaceResponse:
        workspace = await self._repo.create(
            db,
            owner_id=user_id,
            name=data.name,
            description=data.description,
            research_topic=data.research_topic,
        )

        settings = WorkspaceSettings(workspace_id=workspace.id)
        db.add(settings)

        await self._repo.add_member(db, workspace.id, user_id, role="owner")
        await db.flush()

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            research_topic=workspace.research_topic,
            status=workspace.status,
            owner_id=workspace.owner_id,
            member_count=1,
            paper_count=0,
            workflow_count=0,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    async def get_workspace(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> WorkspaceResponse:
        workspace = await self._repo.get(db, workspace_id)
        await self._verify_access(db, workspace, user_id)

        member_count = await self._repo.get_member_count(db, workspace_id)
        paper_count = len(await self._paper_repo.get_by_workspace(db, workspace_id))
        workflow_count = await self._count_sessions(db, workspace_id)

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            research_topic=workspace.research_topic,
            status=workspace.status,
            owner_id=workspace.owner_id,
            member_count=member_count,
            paper_count=paper_count,
            workflow_count=workflow_count,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    async def update_workspace(
        self, db: AsyncSession, workspace_id: str, user_id: str, data: WorkspaceUpdate
    ) -> WorkspaceResponse:
        workspace = await self._repo.get(db, workspace_id)
        await self._verify_ownership(workspace, user_id)

        update_kwargs = data.model_dump(exclude_unset=True)
        if update_kwargs:
            workspace = await self._repo.update(db, workspace_id, **update_kwargs)

        member_count = await self._repo.get_member_count(db, workspace_id)
        paper_count = len(await self._paper_repo.get_by_workspace(db, workspace_id))
        workflow_count = await self._count_sessions(db, workspace_id)

        return WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            research_topic=workspace.research_topic,
            status=workspace.status,
            owner_id=workspace.owner_id,
            member_count=member_count,
            paper_count=paper_count,
            workflow_count=workflow_count,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )

    async def delete_workspace(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> None:
        workspace = await self._repo.get(db, workspace_id)
        await self._verify_ownership(workspace, user_id)
        await self._repo.delete(db, workspace_id)

    async def list_workspaces(
        self, db: AsyncSession, user_id: str, skip: int, limit: int
    ) -> tuple[list[WorkspaceResponse], int]:
        workspaces = await self._repo.get_for_user(db, user_id, skip=skip, limit=limit)
        total = len(await self._repo.get_for_user(db, user_id))

        results = []
        for ws in workspaces:
            member_count = await self._repo.get_member_count(db, ws.id)
            paper_count = len(await self._paper_repo.get_by_workspace(db, ws.id))
            workflow_count = await self._count_sessions(db, ws.id)
            results.append(
                WorkspaceResponse(
                    id=ws.id,
                    name=ws.name,
                    description=ws.description,
                    research_topic=ws.research_topic,
                    status=ws.status,
                    owner_id=ws.owner_id,
                    member_count=member_count,
                    paper_count=paper_count,
                    workflow_count=workflow_count,
                    created_at=ws.created_at,
                    updated_at=ws.updated_at,
                )
            )

        return results, total

    async def add_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        member_user_id: str,
        role: str,
    ) -> WorkspaceMember:
        workspace = await self._repo.get(db, workspace_id)
        await self._verify_ownership(workspace, user_id)
        return await self._repo.add_member(db, workspace_id, member_user_id, role=role)

    async def remove_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        member_user_id: str,
    ) -> None:
        workspace = await self._repo.get(db, workspace_id)
        await self._verify_ownership(workspace, user_id)
        await self._repo.remove_member(db, workspace_id, member_user_id)

    async def get_member_role(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> str | None:
        return await self._repo.get_member_role(db, workspace_id, user_id)

    async def _verify_access(
        self, db: AsyncSession, workspace: Workspace, user_id: str
    ) -> None:
        if workspace.owner_id == user_id:
            return
        role = await self._repo.get_member_role(db, workspace.id, user_id)
        if role is None:
            raise AuthorizationError("User does not have access to this workspace")

    async def _verify_ownership(self, workspace: Workspace, user_id: str) -> None:
        if workspace.owner_id != user_id:
            raise AuthorizationError("Only the workspace owner can perform this action")

    async def _count_sessions(self, db: AsyncSession, workspace_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(ResearchSession)
            .join(
                ResearchProject,
                ResearchProject.id == ResearchSession.project_id,
            )
            .where(ResearchProject.workspace_id == workspace_id)
        )
        result = await db.execute(stmt)
        return result.scalar() or 0
