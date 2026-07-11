from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self) -> None:
        super().__init__(Document)

    async def get_by_workspace(
        self, db: AsyncSession, workspace_id: str, skip: int = 0, limit: int = 100
    ) -> list[Document]:
        return await self.get_many(db, skip=skip, limit=limit, workspace_id=workspace_id)

    async def get_by_session(
        self, db: AsyncSession, session_id: str
    ) -> list[Document]:
        return await self.get_many(db, session_id=session_id)

    async def get_latest_by_workspace(
        self, db: AsyncSession, workspace_id: str, limit: int = 10
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
