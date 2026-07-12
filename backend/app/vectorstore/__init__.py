from app.vectorstore.chroma_client import get_chroma_client, reset_chroma_client
from app.vectorstore.collections import (
    CollectionName,
    get_collection,
    delete_collection,
    list_collections,
)
from app.vectorstore.embeddings import (
    EmbeddingProvider,
    MiniLMEmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from app.vectorstore.retrieval import (
    RetrievedChunk,
    RetrievalResult,
    add_document,
    add_documents_batch,
    update_document,
    delete_document,
    delete_documents_by_filter,
    similarity_search,
    multi_collection_search,
)
from app.vectorstore.memory_indexer import MemoryIndexer
from app.vectorstore.memory_search import (
    MemorySearch,
    MemorySearchHit,
    MemorySearchResult,
)
from app.vectorstore.provider_factory import (
    get_embedding_provider,
    register_provider,
    list_providers,
)

__all__ = [
    "get_chroma_client",
    "reset_chroma_client",
    "CollectionName",
    "get_collection",
    "delete_collection",
    "list_collections",
    "EmbeddingProvider",
    "MiniLMEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "RetrievedChunk",
    "RetrievalResult",
    "add_document",
    "add_documents_batch",
    "update_document",
    "delete_document",
    "delete_documents_by_filter",
    "similarity_search",
    "multi_collection_search",
    "MemoryIndexer",
    "MemorySearch",
    "MemorySearchHit",
    "MemorySearchResult",
    "get_embedding_provider",
    "register_provider",
    "list_providers",
]
