from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    model: str
    system_prompt: str | None = None
    messages: list[ChatMessageResponse]
    is_public: bool = False
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: datetime
    metadata: dict[str, object] | None = None


class CreateConversationRequest(BaseModel):
    workspace_id: str
    title: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    is_public: bool = False


class CreateMessageRequest(BaseModel):
    conversation_id: str
    role: str  # "user", "assistant", or "system"
    content: str
    metadata: dict[str, object] | None = None


MessageResponse = ChatMessageResponse


class GenerateRequest(BaseModel):
    prompt: str
    context: str | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False


class GenerateResponse(BaseModel):
    text: str
    tokens: int | None = None
    model: str | None = None
    finish_reason: str | None = None
    stream: bool = False
