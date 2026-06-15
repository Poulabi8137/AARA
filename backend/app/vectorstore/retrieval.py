from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.vectorstore.collections import CollectionName, get_collection
from app.core.logging import get_logger

logger = get_logger("vectorstore.retrieval")


@dataclass
class RetrievedChunk:
    content: str
    source: str
    score: float
    metadata: dict[str, Any]
    chunk_id: str


@dataclass
class RetrievalResult:
    query: str
    results: list[RetrievedChunk]
    total: int


async def add_document(
    collection: CollectionName | str,
    doc_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Add a single document chunk to a Chroma collection.

    The doc_id should be unique per chunk (e.g. '{uuid}-chunk-{index}').
    """
    col = await get_collection(collection)
    await col.add(
        ids=[doc_id],
        documents=[content],
        metadatas=[metadata or {}],
    )
    logger.debug("added document to collection", extra={
        "collection": collection, "doc_id": doc_id,
    })


async def add_documents_batch(
    collection: CollectionName | str,
    ids: list[str],
    contents: list[str],
    metadatas: list[dict[str, Any]] | None = None,
) -> None:
    """Batch-add multiple chunks to a collection."""
    col = await get_collection(collection)
    await col.add(
        ids=ids,
        documents=contents,
        metadatas=metadatas or [{} for _ in contents],
    )
    logger.info("batch added documents", extra={
        "collection": collection, "count": len(ids),
    })


async def update_document(
    collection: CollectionName | str,
    doc_id: str,
    content: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Update an existing document chunk."""
    col = await get_collection(collection)
    update_kw: dict[str, Any] = {"ids": [doc_id]}
    if content is not None:
        update_kw["documents"] = [content]
    if metadata is not None:
        update_kw["metadatas"] = [metadata]
    await col.update(**update_kw)


async def delete_document(
    collection: CollectionName | str,
    doc_id: str,
) -> None:
    """Delete a single chunk by its ID."""
    col = await get_collection(collection)
    await col.delete(ids=[doc_id])


async def delete_documents_by_filter(
    collection: CollectionName | str,
    filter: dict[str, Any],
) -> None:
    """Delete all chunks matching a metadata filter.

    Example: {"project_id": "uuid-here"}
    """
    col = await get_collection(collection)
    results = await col.get(where=filter)
    if results["ids"]:
        await col.delete(ids=results["ids"])
        logger.info("deleted documents by filter", extra={
            "collection": collection,
            "filter": filter,
            "count": len(results["ids"]),
        })


async def similarity_search(
    collection: CollectionName | str,
    query: str,
    top_k: int = 10,
    filter: dict[str, Any] | None = None,
) -> RetrievalResult:
    """Perform semantic similarity search with optional metadata filtering."""
    col = await get_collection(collection)
    results = await col.query(
        query_texts=[query],
        n_results=top_k,
        where=filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    if results["ids"] and results["ids"][0]:
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for i in range(len(ids)):
            score = 1.0 - distances[i]  # convert distance to similarity
            meta = metadatas[i] or {}
            chunks.append(RetrievedChunk(
                content=documents[i],
                source=meta.get("source", "unknown"),
                score=round(score, 4),
                metadata=meta,
                chunk_id=ids[i],
            ))

    chunks.sort(key=lambda c: c.score, reverse=True)
    return RetrievalResult(query=query, results=chunks, total=len(chunks))


async def multi_collection_search(
    query: str,
    collections: list[CollectionName | str],
    project_id: str | None = None,
    top_k_per_collection: int = 5,
) -> dict[str, RetrievalResult]:
    """Search across multiple collections and return per-collection results."""
    results: dict[str, RetrievalResult] = {}
    filter = {"project_id": project_id} if project_id else None

    for col_name in collections:
        try:
            result = await similarity_search(
                collection=col_name,
                query=query,
                top_k=top_k_per_collection,
                filter=filter,
            )
            results[col_name if isinstance(col_name, str) else col_name.value] = result
        except Exception as e:
            logger.warning("search failed for collection", extra={
                "collection": col_name, "error": str(e),
            })
            results[col_name if isinstance(col_name, str) else col_name.value] = RetrievalResult(
                query=query, results=[], total=0
            )

    return results
