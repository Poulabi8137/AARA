from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_project import ResearchProject
from app.models.workspace import Workspace
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[ResearchProject]):
    def __init__(self) -> None:
        super().__init__(ResearchProject)

    async def get_by_workspace(
        self, db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100
    ) -> list[ResearchProject]:
        return await self.get_many(db, skip=skip, limit=limit, workspace_id=workspace_id)

    async def get_by_workspace_ids(
        self, db: AsyncSession, workspace_ids: list[str], limit: int = 1000
    ) -> list[ResearchProject]:
        if not workspace_ids:
            return []
        stmt = (
            select(ResearchProject)
            .where(ResearchProject.workspace_id.in_(workspace_ids))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[ResearchProject]:
        stmt = (
            select(ResearchProject)
            .join(Workspace, Workspace.id == ResearchProject.workspace_id)
            .where(Workspace.owner_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def archive(self, db: AsyncSession, project_id: str) -> ResearchProject:
        return await self.update(db, project_id, status="archived")

    async def duplicate(
        self, db: AsyncSession, project_id: str, new_name: str
    ) -> ResearchProject:
        original = await self.get(db, project_id)
        return await self.create(
            db,
            workspace_id=original.workspace_id,
            name=new_name,
            description=original.description,
            research_goal=original.research_goal,
            key_questions=original.key_questions,
        )
