from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.research_project import ResearchProject
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    ContextRequest,
    ContextResponse,
)
from app.services.auth_service import get_current_user
from app.ingestion.ingestion_service import IngestionService
from app.ingestion.document_loader import UnsupportedFormatError, SUPPORTED_EXTENSIONS
from app.vectorstore.collections import CollectionName, list_collections
from app.vectorstore.retrieval import similarity_search, multi_collection_search

router = APIRouter(tags=["Documents & Retrieval"])


@router.post("/documents/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str | None = Query(None),
    collection: str = Query(CollectionName.KNOWLEDGE_BASE.value),
    author: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a document for ingestion into the vector store.

    Supported formats: PDF, DOCX, TXT, Markdown.
    """
    ext = f".{file.filename.rsplit('.', 1)[-1].lower()}" if "." in (file.filename or "") else ""

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    service = IngestionService(db)
    try:
        document = await service.ingest_document(
            file_content=content,
            filename=file.filename or "unknown",
            project_id=project_id,
            collection=collection,
            author=author,
        )
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return DocumentResponse.model_validate(document)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    project_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    service = IngestionService(db)
    docs, total = await service.list_documents(
        project_id=project_id, skip=skip, limit=limit
    )
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    from app.models.document import Document

    doc = await db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if doc.project_id:
        project_check = await db.execute(
            select(ResearchProject).where(
                ResearchProject.id == doc.project_id,
                ResearchProject.created_by == current_user.id,
            )
        )
        if project_check.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    service = IngestionService(db)
    await service.delete_document(document_id)


@router.post("/retrieval/search", response_model=SearchResponse)
async def search_documents(
    body: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Semantic search across a single vector collection with optional metadata filter."""
    collection = body.collection or CollectionName.KNOWLEDGE_BASE.value
    filter = {"project_id": body.project_id} if body.project_id else None

    result = await similarity_search(
        collection=collection,
        query=body.query,
        top_k=body.top_k,
        filter=filter,
    )

    items = [
        SearchResultItem(
            content=r.content,
            source=r.source,
            score=r.score,
            metadata=r.metadata,
            chunk_id=r.chunk_id,
        )
        for r in result.results
    ]

    return SearchResponse(
        query=body.query,
        results=items,
        total=result.total,
        collection=collection,
    )


@router.post("/retrieval/context", response_model=ContextResponse)
async def retrieve_context(
    body: ContextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContextResponse:
    """Multi-collection context retrieval for LangGraph agents.

    Returns results grouped by collection so agents can prioritise sources.
    """
    collections = body.collections or [c.value for c in CollectionName]
    filter = {"project_id": body.project_id} if body.project_id else None

    results = await multi_collection_search(
        query=body.query,
        collections=collections,
        project_id=body.project_id,
        top_k_per_collection=body.top_k,
    )

    grouped: dict[str, list[SearchResultItem]] = {}
    total = 0
    for col_name, col_result in results.items():
        items = [
            SearchResultItem(
                content=r.content,
                source=r.source,
                score=r.score,
                metadata=r.metadata,
                chunk_id=r.chunk_id,
            )
            for r in col_result.results
        ]
        grouped[col_name] = items
        total += len(items)

    return ContextResponse(
        query=body.query,
        collections=grouped,
        total=total,
    )
