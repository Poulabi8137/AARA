from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self) -> None:
        super().__init__(Workspace)

    async def get_by_owner(
        self, db: AsyncSession, owner_id: str, skip: int = 0, limit: int = 100
    ) -> list[Workspace]:
        return await self.get_many(db, skip=skip, limit=limit, owner_id=owner_id)

    async def get_for_user(
        self, db: AsyncSession, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .outerjoin(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(
                (Workspace.owner_id == user_id)
                | (WorkspaceMember.user_id == user_id)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_member_count(self, db: AsyncSession, workspace_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def add_member(
        self, db: AsyncSession, workspace_id: str, user_id: str, role: str = "editor"
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id, user_id=user_id, role=role
        )
        db.add(member)
        await db.flush()
        return member

    async def remove_member(self, db: AsyncSession, workspace_id: str, user_id: str) -> None:
        member = await db.get(
            WorkspaceMember, (workspace_id, user_id)
        )
        if member:
            await db.delete(member)
            await db.flush()

    async def get_member_role(
        self, db: AsyncSession, workspace_id: str, user_id: str
    ) -> str | None:
        member = await db.get(
            WorkspaceMember, (workspace_id, user_id)
        )
        return member.role if member else None
