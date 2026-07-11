from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai import ChatMessageResponse


class MessageRepository:
    async def create_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> ChatMessageResponse:
        from app.models.message import Message

        message = Message(
            id=f"msg_{__import__('uuid').uuid4().hex}",
            conversation_id=conversation_id,
            user_id=user_id,
            role=data["role"],
            content=data["content"],
            timestamp=datetime.now(UTC),
            extra=data.get("metadata"),
        )
        db.add(message)
        await db.flush()

        return ChatMessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            timestamp=message.timestamp,
            metadata=message.metadata,
        )

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> list[ChatMessageResponse]:
        from app.models.message import Message

        result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
            )
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()

        return [
            ChatMessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                metadata=msg.extra,
            )
            for msg in messages
        ]
