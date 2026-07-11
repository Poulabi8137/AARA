from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.ai import (
    ConversationResponse,
    CreateConversationRequest,
    CreateMessageRequest,
    GenerateRequest,
    GenerateResponse,
    MessageResponse,
)
from app.schemas.auth import UserResponse
from app.schemas.common import PaginatedResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def get_ai_service() -> AIService:
    return AIService(
        conversation_repo=ConversationRepository(),
        message_repo=MessageRepository(),
    )


@router.get("/conversations", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    workspace_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    items, total = await service.list_conversations(
        db, current_user.id, workspace_id, (page - 1) * page_size, page_size
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    return await service.create_conversation(db, current_user.id, body)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    conversation = await service.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    body: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    conversation = await service.update_conversation(db, conversation_id, current_user.id, body)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    await service.delete_conversation(db, conversation_id, current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    return await service.list_messages(db, conversation_id, current_user.id)


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    body: CreateMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    return await service.create_message(db, current_user.id, body)


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
    service: AIService = Depends(get_ai_service),
):
    return await service.generate(db, current_user.id, body)
