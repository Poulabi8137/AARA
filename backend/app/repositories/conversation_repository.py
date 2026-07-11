from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai import (
    ChatMessageResponse,
    ConversationResponse,
)


class ConversationRepository:
    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
        data: dict[str, Any],
    ) -> ConversationResponse:
        from app.models.conversation import Conversation
        from app.models.message import Message

        now = datetime.now(UTC)
        conversation = Conversation(
            id=f"conv_{__import__('uuid').uuid4().hex}",
            workspace_id=workspace_id,
            user_id=user_id,
            title=data.get("title") or "New Conversation",
            model=data.get("model") or "gpt-4o-mini",
            system_prompt=data.get("system_prompt"),
            is_public=data.get("is_public", False),
            created_at=now,
            updated_at=now,
        )
        db.add(conversation)
        await db.flush()

        messages: list[ChatMessageResponse] = []
        if data.get("system_prompt"):
            system_message = Message(
                id=f"msg_{__import__('uuid').uuid4().hex}",
                conversation_id=conversation.id,
                user_id=user_id,
                role="system",
                content=data["system_prompt"],
                timestamp=now,
            )
            db.add(system_message)
            await db.flush()
            messages.append(
                ChatMessageResponse(
                    id=system_message.id,
                    conversation_id=system_message.conversation_id,
                    role=system_message.role,
                    content=system_message.content,
                    timestamp=system_message.timestamp,
                    metadata=system_message.extra,
                )
            )

        return ConversationResponse(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            title=conversation.title,
            model=conversation.model,
            system_prompt=conversation.system_prompt,
            messages=messages,
            is_public=conversation.is_public,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ConversationResponse]:
        from app.models.conversation import Conversation
        from app.models.message import Message

        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if workspace_id:
            stmt = stmt.where(Conversation.workspace_id == workspace_id)
        stmt = stmt.offset(skip).limit(limit).order_by(Conversation.created_at.desc())

        result = await db.execute(stmt)
        conversations = result.scalars().all()

        response_list: list[ConversationResponse] = []
        for conversation in conversations:
            message_result = await db.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            )
            messages = message_result.scalars().all()
            response_list.append(
                ConversationResponse(
                    id=conversation.id,
                    workspace_id=conversation.workspace_id,
                    title=conversation.title,
                    model=conversation.model,
                    system_prompt=conversation.system_prompt,
                    messages=[
                        ChatMessageResponse(
                            id=msg.id,
                            conversation_id=msg.conversation_id,
                            role=msg.role,
                            content=msg.content,
                            timestamp=msg.timestamp,
                            metadata=msg.extra,
                        )
                        for msg in messages
                    ],
                    is_public=conversation.is_public,
                    created_at=conversation.created_at,
                    updated_at=conversation.updated_at,
                )
            )
        return response_list

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> ConversationResponse | None:
        from app.models.conversation import Conversation
        from app.models.message import Message

        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return None

        message_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = message_result.scalars().all()

        return ConversationResponse(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            title=conversation.title,
            model=conversation.model,
            system_prompt=conversation.system_prompt,
            messages=[
                ChatMessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.extra,
                )
                for msg in messages
            ],
            is_public=conversation.is_public,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    async def update_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> ConversationResponse | None:
        from app.models.conversation import Conversation
        from app.models.message import Message

        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return None

        for field in ("title", "model", "system_prompt", "is_public"):
            if field in data and data[field] is not None:
                setattr(conversation, field, data[field])
        conversation.updated_at = datetime.now(UTC)

        message_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = message_result.scalars().all()

        return ConversationResponse(
            id=conversation.id,
            workspace_id=conversation.workspace_id,
            title=conversation.title,
            model=conversation.model,
            system_prompt=conversation.system_prompt,
            messages=[
                ChatMessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    metadata=msg.extra,
                )
                for msg in messages
            ],
            is_public=conversation.is_public,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> None:
        from app.models.conversation import Conversation

        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            await db.delete(conversation)

    async def get_conversation_count(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
    ) -> int:
        from app.models.conversation import Conversation

        stmt = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )
        if workspace_id:
            stmt = stmt.where(Conversation.workspace_id == workspace_id)
        result = await db.execute(stmt)
        return result.scalar_one()
