from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self) -> None:
        super().__init__(PasswordResetToken)

    async def get_by_token_hash(
        self, db: AsyncSession, token_hash: str
    ) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def invalidate_active_tokens_for_user(self, db: AsyncSession, user_id: str) -> None:
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
        await db.execute(stmt)

    async def mark_used(self, db: AsyncSession, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(UTC)
        db.add(token)
        await db.flush()
