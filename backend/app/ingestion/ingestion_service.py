from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.ingestion.document_loader import extract_text_from_bytes
from app.ingestion.chunking import chunk_text, Chunk
from app.ingestion.metadata_extractor import extract_default_metadata
from app.models.document import Document, DocumentStatus
from app.vectorstore.collections import CollectionName
from app.vectorstore.retrieval import add_documents_batch, delete_documents_by_filter

logger = get_logger("ingestion.service")


class IngestionService:
    """Orchestrates the full document ingestion pipeline.

    Upload → Extract text → Chunk → Embed → Store vectors → Record metadata
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        project_id: str | None = None,
        collection: CollectionName | str = CollectionName.KNOWLEDGE_BASE,
        author: str | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> Document:
        """Run the full ingestion pipeline for a single file."""
        doc_id = uuid.uuid4()
        raw_text = await extract_text_from_bytes(file_content, filename)

        base_meta = extract_default_metadata(
            project_id=project_id,
            source=collection.value if isinstance(collection, CollectionName) else collection,
            filename=filename,
            author=author,
            **(metadata_extra or {}),
        )

        chunks = chunk_text(raw_text, metadata=base_meta)

        chunk_ids: list[str] = []
        chunk_contents: list[str] = []
        chunk_metadatas: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}-chunk-{i}"
            chunk_ids.append(chunk_id)
            chunk_contents.append(chunk.content)
            chunk.metadata["chunk_index"] = i
            chunk_metadatas.append(chunk.metadata)

        if chunk_ids:
            await add_documents_batch(
                collection=collection,
                ids=chunk_ids,
                contents=chunk_contents,
                metadatas=chunk_metadatas,
            )

        document = Document(
            id=doc_id,
            project_id=uuid.UUID(project_id) if project_id else None,
            filename=filename,
            collection=collection.value if isinstance(collection, CollectionName) else collection,
            status=DocumentStatus.INDEXED,
            chunk_count=len(chunks),
            char_count=len(raw_text),
            author=author,
        )
        self.db.add(document)
        await self.db.flush()

        logger.info("document ingested", extra={
            "doc_id": str(doc_id),
            "filename": filename,
            "chunks": len(chunks),
        })
        return document

    async def delete_document(self, document_id: uuid.UUID) -> None:
        """Delete a document's vectors and metadata record."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return

        await delete_documents_by_filter(
            collection=doc.collection,
            filter={"project_id": str(doc.id)},
        )
        await self.db.delete(doc)
        await self.db.flush()
        logger.info("document deleted", extra={"doc_id": str(document_id)})

    async def list_documents(
        self,
        project_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Document], int]:
        query = select(Document).order_by(Document.uploaded_at.desc())
        count_query = select(Document).order_by(Document.uploaded_at.desc())

        if project_id:
            query = query.where(Document.project_id == uuid.UUID(project_id))
            count_query = count_query.where(Document.project_id == uuid.UUID(project_id))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        docs = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        return docs, total
