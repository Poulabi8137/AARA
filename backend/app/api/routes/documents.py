from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
    DocumentExportRequest,
    DocumentGenerateRequest,
    DocumentResponse,
)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


def _get_document_service():
    from app.agents.writing import WritingAgent
    from app.repositories.document_repository import DocumentRepository
    from app.services.document_service import DocumentService

    return DocumentService(DocumentRepository(), WritingAgent())


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_document(
    body: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_document_service()
    document = await service.generate_document(db, current_user.id, body)
    return document


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    workspace_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_document_service()
    items, total = await service.list_documents(db, workspace_id, current_user.id, (page - 1) * page_size, page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=-(-total // page_size) if total > 0 else 0,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_document_service()
    document = await service.get_document(db, document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/{document_id}/export")
async def export_document(
    document_id: str,
    body: DocumentExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_active_user),
):
    service = _get_document_service()
    result = await service.export_document(db, document_id, current_user.id, body.format)
    return result
