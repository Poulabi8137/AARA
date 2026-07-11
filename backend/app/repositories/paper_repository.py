from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_paper import ResearchPaper
from app.repositories.base import BaseRepository


class PaperRepository(BaseRepository[ResearchPaper]):
    def __init__(self) -> None:
        super().__init__(ResearchPaper)

    async def get_by_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[ResearchPaper]:
        filters: dict = {"workspace_id": workspace_id}
        if status is not None:
            filters["status"] = status
        return await self.get_many(db, skip=skip, limit=limit, **filters)

    async def get_by_project(
        self, db: AsyncSession, project_id: str, skip: int = 0, limit: int = 100
    ) -> list[ResearchPaper]:
        return await self.get_many(db, skip=skip, limit=limit, project_id=project_id)

    async def get_by_workspace_ids(
        self, db: AsyncSession, workspace_ids: list[str], limit: int = 1000
    ) -> list[ResearchPaper]:
        if not workspace_ids:
            return []
        stmt = (
            select(ResearchPaper)
            .where(ResearchPaper.workspace_id.in_(workspace_ids))
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_content_hash(
        self, db: AsyncSession, content_hash: str, workspace_id: str
    ) -> ResearchPaper | None:
        stmt = select(ResearchPaper).where(
            ResearchPaper.content_hash == content_hash,
            ResearchPaper.workspace_id == workspace_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_doi(
        self, db: AsyncSession, doi: str, workspace_id: str
    ) -> ResearchPaper | None:
        stmt = select(ResearchPaper).where(
            ResearchPaper.doi == doi,
            ResearchPaper.workspace_id == workspace_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        db: AsyncSession,
        query: str,
        workspace_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ResearchPaper]:
        pattern = f"%{query}%"
        stmt = (
            select(ResearchPaper)
            .where(ResearchPaper.workspace_id == workspace_id)
            .where(
                or_(
                    ResearchPaper.title.ilike(pattern),
                    ResearchPaper.abstract.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_doi(
        self, db: AsyncSession, doi: str, workspace_id: str
    ) -> ResearchPaper | None:
        return await self.find_by_doi(db, doi, workspace_id)
