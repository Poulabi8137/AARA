from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citation import Citation
from app.repositories.base import BaseRepository


class CitationRepository(BaseRepository[Citation]):
    def __init__(self) -> None:
        super().__init__(Citation)

    async def get_by_workspace(
        self, db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100
    ) -> list[Citation]:
        return await self.get_many(db, skip=skip, limit=limit, workspace_id=workspace_id)

    async def get_by_paper(
        self, db: AsyncSession, paper_id: str
    ) -> list[Citation]:
        return await self.get_many(db, paper_id=paper_id)

    async def search(
        self,
        db: AsyncSession,
        query: str,
        workspace_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Citation]:
        pattern = f"%{query}%"
        stmt = (
            select(Citation)
            .where(Citation.workspace_id == workspace_id)
            .where(
                or_(
                    Citation.title.ilike(pattern),
                    Citation.formatted_citation.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_style(
        self, db: AsyncSession, workspace_id: str
    ) -> dict[str, int]:
        stmt = (
            select(Citation.style, func.count())
            .where(Citation.workspace_id == workspace_id)
            .group_by(Citation.style)
        )
        result = await db.execute(stmt)
        return dict(result.all())

    async def count_by_source_type(
        self, db: AsyncSession, workspace_id: str
    ) -> dict[str, int]:
        stmt = (
            select(Citation.source_type, func.count())
            .where(Citation.workspace_id == workspace_id)
            .group_by(Citation.source_type)
        )
        result = await db.execute(stmt)
        return dict(result.all())
