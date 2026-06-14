from __future__ import annotations

from enum import Enum

import chromadb
from chromadb.utils import embedding_functions

from app.core.logging import get_logger
from app.vectorstore.chroma_client import get_chroma_client

logger = get_logger("vectorstore.collections")


class CollectionName(str, Enum):
    RESEARCH_PAPERS = "research_papers"
    WEB_SEARCH_RESULTS = "web_search_results"
    CITATIONS = "citations"
    GENERATED_REPORTS = "generated_reports"
    KNOWLEDGE_BASE = "knowledge_base"


_COLLECTION_CACHE: dict[str, chromadb.Collection] = {}


def _default_ef() -> embedding_functions.SentenceTransformerEmbeddingFunction:
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


async def get_collection(
    name: CollectionName | str,
    embedding_function=None,
) -> chromadb.Collection:
    """Get or create a Chroma collection by name.

    Uses an in-memory cache so repeated calls return the same object
    within a process lifetime.
    """
    key = name.value if isinstance(name, CollectionName) else name

    if key in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[key]

    ef = embedding_function or _default_ef()
    client = await get_chroma_client()

    try:
        collection = await client.get_collection(
            name=key, embedding_function=ef
        )
        logger.debug("retrieved existing collection", extra={"collection": key})
    except Exception:
        collection = await client.create_collection(
            name=key,
            embedding_function=ef,
            metadata={"description": f"AgentWatch {key}"},
        )
        logger.info("created new collection", extra={"collection": key})

    _COLLECTION_CACHE[key] = collection
    return collection


async def delete_collection(name: CollectionName | str) -> None:
    key = name.value if isinstance(name, CollectionName) else name
    client = await get_chroma_client()
    try:
        await client.delete_collection(name=key)
        _COLLECTION_CACHE.pop(key, None)
        logger.info("deleted collection", extra={"collection": key})
    except Exception:
        logger.warning("collection not found for deletion", extra={"collection": key})


async def list_collections() -> list[str]:
    client = await get_chroma_client()
    collections = await client.list_collections()
    return [c.name for c in collections]
