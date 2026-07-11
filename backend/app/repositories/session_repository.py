from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[ResearchSession]):
    def __init__(self) -> None:
        super().__init__(ResearchSession)

    async def get_by_project(
        self, db: AsyncSession, project_id: str, skip: int = 0, limit: int = 100
    ) -> list[ResearchSession]:
        return await self.get_many(db, skip=skip, limit=limit, project_id=project_id)

    async def get_active_sessions(
        self, db: AsyncSession, project_id: str
    ) -> list[ResearchSession]:
        stmt = (
            select(ResearchSession)
            .where(ResearchSession.project_id == project_id)
            .where(ResearchSession.status.in_(["running", "pending"]))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_workflow_id(
        self, db: AsyncSession, workflow_id: str
    ) -> ResearchSession | None:
        stmt = select(ResearchSession).where(ResearchSession.workflow_id == workflow_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent_by_workspace(
        self, db: AsyncSession, workspace_id: str, limit: int = 10
    ) -> list[ResearchSession]:
        stmt = (
            select(ResearchSession)
            .join(
                ResearchProject,
                ResearchProject.id == ResearchSession.project_id,
            )
            .where(ResearchProject.workspace_id == workspace_id)
            .order_by(ResearchSession.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_project_ids(
        self, db: AsyncSession, project_ids: list[str], limit: int = 1000
    ) -> list[ResearchSession]:
        if not project_ids:
            return []
        stmt = (
            select(ResearchSession)
            .where(ResearchSession.project_id.in_(project_ids))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_by_workspace_ids(
        self, db: AsyncSession, workspace_ids: list[str], limit: int = 20
    ) -> list[ResearchSession]:
        if not workspace_ids:
            return []
        stmt = (
            select(ResearchSession)
            .join(
                ResearchProject,
                ResearchProject.id == ResearchSession.project_id,
            )
            .where(ResearchProject.workspace_id.in_(workspace_ids))
            .order_by(ResearchSession.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())
