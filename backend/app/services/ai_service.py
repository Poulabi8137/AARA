from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import BaseLLMProvider, LLMMessage
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.ai import (
    ChatMessageResponse,
    ConversationResponse,
    CreateConversationRequest,
    CreateMessageRequest,
    GenerateRequest,
    GenerateResponse,
)


class AIService:
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo or MessageRepository()
        self._llm_provider = llm_provider

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ConversationResponse], int]:
        conversations = await self._conversation_repo.list_conversations(
            db, user_id, workspace_id, skip, limit
        )
        total = await self._conversation_repo.get_conversation_count(
            db, user_id, workspace_id
        )
        return conversations, total

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        body: CreateConversationRequest,
    ) -> ConversationResponse:
        return await self._conversation_repo.create_conversation(
            db,
            user_id,
            body.workspace_id,
            {
                "title": body.title,
                "model": body.model,
                "system_prompt": body.system_prompt,
                "is_public": body.is_public,
            },
        )

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> ConversationResponse | None:
        return await self._conversation_repo.get_conversation(db, conversation_id, user_id)

    async def update_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        body: CreateConversationRequest,
    ) -> ConversationResponse | None:
        return await self._conversation_repo.update_conversation(
            db,
            conversation_id,
            user_id,
            {
                "title": body.title,
                "model": body.model,
                "system_prompt": body.system_prompt,
                "is_public": body.is_public,
            },
        )

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> None:
        await self._conversation_repo.delete_conversation(db, conversation_id, user_id)

    async def list_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> list[ChatMessageResponse]:
        return await self._message_repo.get_messages(db, conversation_id, user_id)

    async def create_message(
        self,
        db: AsyncSession,
        user_id: str,
        body: CreateMessageRequest,
    ) -> ChatMessageResponse:
        return await self._message_repo.create_message(
            db,
            body.conversation_id,
            user_id,
            {
                "role": body.role,
                "content": body.content,
                "metadata": body.metadata,
            },
        )

    async def generate(
        self,
        db: AsyncSession,
        user_id: str,
        body: GenerateRequest,
    ) -> GenerateResponse:
        if not self._llm_provider:
            return GenerateResponse(
                text="No LLM provider is configured. Set an API key for OpenAI, Gemini, Groq, or Ollama.",
                model=None,
                tokens=None,
                finish_reason="error",
            )

        messages = [LLMMessage(role="user", content=body.prompt)]
        if body.context:
            messages.insert(0, LLMMessage(role="system", content=body.context))

        response = await self._llm_provider.chat(messages)

        return GenerateResponse(
            text=response.content,
            tokens=response.usage.total_tokens if response.usage else None,
            model=response.model or None,
            finish_reason=response.finish_reason or None,
        )
