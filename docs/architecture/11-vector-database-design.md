# Document 11 — Vector Database Design

## Qdrant Configuration

```python
class QdrantConfig:
    url: str = "http://localhost:6333"
    api_key: str | None = None
    prefer_grpc: bool = True
    timeout_seconds: int = 30

    hnsw_config = HnswConfigDiff(
        m=16,
        ef_construct=100,
        full_scan_threshold=10000,
    )

    quantization_config = ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            always_ram=True,
        )
    )

    collection_config = VectorParams(
        size=384,
        distance=Distance.COSINE,
        hnsw_config=hnsw_config,
        quantization_config=quantization_config,
    )
```

## Collection Management

```python
class VectorDBManager:
    """Manages Qdrant collections, including model versioning."""

    def __init__(self, qdrant_client: QdrantClient):
        self.client = qdrant_client

    async def ensure_collection(self, model_id: str, dimension: int) -> str:
        collection = get_collection_name(model_id)
        if not await self.client.collection_exists(collection):
            await self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(type=ScalarType.INT8)
                ),
            )
        return collection

    async def migrate_embeddings(self, old_model: str, new_model: str,
                                  re_embed_fn: callable) -> int:
        """Migrate ALL embeddings from one model to another."""
        old_collection = get_collection_name(old_model)
        new_collection = get_collection_name(new_model)

        await self.ensure_collection(new_model, dimension=re_embed_fn.dimension)

        count = 0
        next_offset = None
        while True:
            records, next_offset = await self.client.scroll(
                collection_name=old_collection,
                limit=100,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            for record in records:
                text = await self._get_chunk_text(record.id)
                new_vector = await re_embed_fn(text)
                await self.client.upsert(
                    collection_name=new_collection,
                    points=[PointStruct(id=record.id, vector=new_vector, payload=record.payload)]
                )
                count += 1
            if next_offset is None:
                break
        return count
```

## Payload Indexing Strategy

Qdrant payload filtering is O(n) without indexes. For frequently filtered fields, payload indexes are required.

```python
class VectorDBManager:
    """Manages Qdrant collections, including payload indexing."""

    # Payload fields that must be indexed for every collection
    REQUIRED_FIELD_INDEXES = {
        "workspace_id": KeywordIndexConfig(
            type=FieldType.KEYWORD,
            is_tenant=True,  # Tenant-level isolation field
        ),
        "paper_id": KeywordIndexConfig(
            type=FieldType.KEYWORD,
        ),
        "model_id": KeywordIndexConfig(
            type=FieldType.KEYWORD,
        ),
        "section_name": KeywordIndexConfig(
            type=FieldType.KEYWORD,
        ),
    }

    async def ensure_collection(self, model_id: str, dimension: int) -> str:
        collection = get_collection_name(model_id)
        if not await self.client.collection_exists(collection):
            await self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(type=ScalarType.INT8)
                ),
            )
            # Create payload indexes after collection creation
            for field, config in self.REQUIRED_FIELD_INDEXES.items():
                await self.client.create_payload_index(
                    collection_name=collection,
                    field_name=field,
                    field_type=config.type,
                    is_tenant=config.is_tenant,
                )
            # Keyword index for workspace_id (frequent filter)
            await self.client.create_payload_index(
                collection_name=collection,
                field_name="workspace_id",
                field_type=PayloadSchemaType.KEYWORD,
            )
        return collection
```

**Index specification:**

| Field | Index Type | Filter Pattern | Estimated Speedup |
|---|---|---|---|
| `workspace_id` | Keyword | `workspace_id == X` (every search) | 100x on 100K vectors |
| `paper_id` | Keyword | `paper_id == X` (detail lookups) | 10x |
| `model_id` | Keyword | `model_id == X` (collection selection) | 10x |
| `section_name` | Keyword | `section_name IN [...]` (section filtering) | 5x |

Indexes are created at collection creation time. No retroactive indexing needed.

## Search Interface
    """Performs semantic search across the paper collection."""

    async def search(
        self,
        query: str,
        workspace_id: UUID,
        embedder: BaseEmbedder,
        limit: int = 20,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        collection = get_collection_name(embedder.model_id)
        query_vector = await embedder.embed_query(query)

        results = await self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="workspace_id",
                        match=MatchValue(value=str(workspace_id)),
                    )
                ]
            ),
        )

        enriched = []
        for result in results:
            paper = await self._get_paper_metadata(result.payload["paper_id"])
            enriched.append(SearchResult(
                paper=paper,
                chunk=result.payload,
                score=result.score,
                section=result.payload.get("section_name"),
            ))
        return enriched
```

## Trade-offs

| Decision | Alternative | Rationale |
|---|---|---|
| Cosine distance | Dot product, Euclidean | Normalized embeddings work best with cosine |
| Scalar quantization (INT8) | Float32 vectors | 4x memory reduction with <2% accuracy loss |
| HNSW index (M=16, ef=100) | Flat search | ~50ms search at 99% recall on 100K vectors |
| Collection-per-model | Single collection with model_id filter | Filter filtering is O(n); dedicated collections are O(log n) |
| gRPC for batch | REST | 2-5x faster for batch upsert |
| Payload indexes on workspace_id, paper_id, model_id | No indexes | 10-100x speedup for filtered searches; created at collection init |

## pgvector Alternative (Documented Fallback)

For local development without Docker:

```python
class PgVectorProvider(BaseVectorDB):
    """pgvector implementation using PostgreSQL."""

    async def search(self, collection: str, query_vector: list[float], ...):
        async with self.db.execute(
            text(f"""
                SELECT paper_id, chunk_index, section_name, content,
                       1 - (embedding <=> :query) AS score
                FROM paper_embeddings
                WHERE model_id = :model_id
                  AND workspace_id = :workspace_id
                  AND 1 - (embedding <=> :query) > :threshold
                ORDER BY embedding <=> :query
                LIMIT :limit
            """),
            {"query": query_vector, "model_id": model_id, ...}
        ) as cursor:
            return await cursor.fetchall()
```
