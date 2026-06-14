from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.research_session import ResearchSession, SessionStatus
from app.schemas.session import SessionCreate


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sessions(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[list[ResearchSession], int]:
        query = (
            select(ResearchSession)
            .order_by(ResearchSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count(ResearchSession.id))

        result = await self.db.execute(query)
        sessions = list(result.scalars().all())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        return sessions, total

    async def get_session(self, session_id: uuid.UUID) -> ResearchSession:
        result = await self.db.execute(
            select(ResearchSession).where(ResearchSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        return session

    async def create_session(self, data: SessionCreate) -> ResearchSession:
        session = ResearchSession(
            project_id=data.project_id,
            session_name=data.session_name,
        )
        self.db.add(session)
        await self.db.flush()
        return session
