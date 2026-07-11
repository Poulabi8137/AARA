# Document 10 — Embedding Pipeline

## Architecture

```mermaid
graph TD
    subgraph "Input"
        CHUNKS[Paper Chunks]
        QUERY[Search Query]
    end

    subgraph "Embedding Provider Interface"
        EP[BaseEmbedder]
    end

    subgraph "Implementations"
        ST[sentence-transformers]
        OA[OpenAI Embeddings]
    end

    subgraph "Vector Storage"
        QC[Qdrant Collection<br/>papers_{model_id}]
    end

    CHUNKS -->|chunk.text| EP
    QUERY -->|query.text| EP
    EP --> ST
    EP --> OA
    ST -->|384-dim vectors| QC
    OA -->|1536-dim vectors| QC
```

## Embedder Interface

```python
class BaseEmbedder(ABC):
    provider_id: str
    model_id: str
    dimension: int
    max_input_tokens: int
    is_local: bool
    cost_per_1k_tokens: Decimal = Decimal("0")

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call.
        Default implementation calls embed() per text for providers
        that don't support batching. Override for batch-capable providers."""
        return [await self.embed(t) for t in texts]
    @abstractmethod
    async def embed_query(self, query: str) -> list[float]: ...
```

## Implementations

### Sentence Transformers (Default, Free)
```python
class SentenceTransformerEmbedder(BaseEmbedder):
    provider_id = "sentence_transformers"
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    dimension = 384
    max_input_tokens = 256
    is_local = True
    cost_per_1k_tokens = Decimal("0")

    def __init__(self):
        self.model = SentenceTransformer(self.model_id)

    async def embed(self, text: str) -> list[float]:
        return await asyncio.to_thread(
            self.model.encode, text, normalize_embeddings=True
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(
            self.model.encode, texts, normalize_embeddings=True
        )
```

### OpenAI (Cloud, Higher Quality)
```python
class OpenAIEmbedder(BaseEmbedder):
    provider_id = "openai"
    model_id = "text-embedding-3-small"
    dimension = 1536
    max_input_tokens = 8192
    is_local = False
    cost_per_1k_tokens = Decimal("0.00002")
```

## Collection Naming Convention

```python
def get_collection_name(model_id: str) -> str:
    # sentence-transformers/all-MiniLM-L6-v2 → papers_sentence-transformers_all-MiniLM-L6-v2
    safe = model_id.replace("/", "_").replace("-", "_")
    return f"papers_{safe}"
```

## Embedding Pipeline Flow (Batch)

```python
class EmbeddingPipeline:
    """Coordinates batch embedding of paper chunks."""

    BATCH_SIZE = 32  # Number of chunks to embed in a single batch call

    async def process_paper(self, paper_id: UUID, workspace: Workspace):
        model_id = workspace.settings.embedding_model
        embedder = self.embedder_registry.get(model_id)
        collection = get_collection_name(model_id)

        chunks = await self.db.query(PaperChunk).where(paper_id=paper_id).all()

        existing = await self.db.query(PaperEmbedding).where(
            paper_id=paper_id, model_id=model_id
        ).all()
        existing_chunk_ids = {e.chunk_id for e in existing}

        # Batch: filter out already-embedded chunks, then embed in batches
        new_chunks = [c for c in chunks if c.id not in existing_chunk_ids]
        if not new_chunks:
            return

        points = []
        for i in range(0, len(new_chunks), self.BATCH_SIZE):
            batch = new_chunks[i:i + self.BATCH_SIZE]
            texts = [c.content for c in batch]
            vectors = await embedder.embed_batch(texts)  # Single API call per batch

            for chunk, vector in zip(batch, vectors):
                point_id = str(uuid4())
                points.append(PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "paper_id": str(paper_id),
                        "chunk_index": chunk.chunk_index,
                        "section_name": chunk.section_name,
                        "model_id": model_id,
                    }
                ))

        if points:
            await self.qdrant.upsert(collection, points)
            await self.db.execute(
                insert(PaperEmbedding),
                [{"paper_id": paper_id, "chunk_id": chunk.id,
                  "model_id": model_id, "vector_id": point_id}
                 for chunk, point_id in zip(new_chunks, points)]
            )
            await self.db.commit()

    # Also update OverlapAnalysisService in idea generation to use batch embedding:

    async def _calculate_overlap_batch(self, ideas: list[ResearchIdea],
                                        workspace_id: UUID) -> list[OverlapResult]:
        """Batch overlap analysis: embed all ideas at once."""
        descriptions = [idea.description for idea in ideas]
        idea_vectors = await self.embedder.embed_batch(descriptions)

        results = []
        for idea, vector in zip(ideas, idea_vectors):
            search_results = await self.vector_db.search(
                collection=get_collection_name(self.embedder.model_id),
                query_vector=vector,
                limit=10,
                score_threshold=0.6,
                query_filter=Filter(must=[
                    FieldCondition(key="workspace_id",
                                   match=MatchValue(value=str(workspace_id)))
                ])
            )
            # ... process results as before
        return results
```

## Trade-offs

| Decision | Alternative | Rationale |
|---|---|---|
| Sentence Transformers default | Always use OpenAI | $0 cost, offline-capable; OpenAI is upgrade path |
| 512-token chunks with overlap | Variable-length chunks | Predictable storage, consistent search quality |
| Collection per model | Single collection with model_id filter | Qdrant filtering on payload is slower than dedicated collections for large datasets |
| Lazy re-embedding (on access) | Batch re-embed all papers | Avoids expensive batch jobs; user triggers re-embed when changing models |
| Batch embedding (batch_size=32) | Single embedding per chunk | 5-10x throughput improvement; Sentence Transformers and OpenAI both batch efficiently |
