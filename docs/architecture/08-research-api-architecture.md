# Document 08 — Research API Architecture

## Provider Abstraction

All research APIs are accessed through a uniform interface. Agents never directly call APIs.

```python
class BaseResearchProvider(ABC):
    """Interface for all research API providers."""

    provider_id: str
    provider_name: str
    rate_limit: int  # requests per minute
    is_free: bool = True

    @abstractmethod
    async def search(self, query: str, limit: int = 20,
                     filters: SearchFilters | None = None) -> SearchResults:
        """Search for papers matching the query."""
        ...

    @abstractmethod
    async def get_paper(self, identifier: str,
                        id_type: Literal["doi", "id", "arxiv_id"]) -> Paper:
        """Fetch a single paper by identifier."""
        ...

    @abstractmethod
    async def get_references(self, paper_id: str) -> list[Reference]:
        """Get references for a paper."""
        ...

    @abstractmethod
    async def get_citations(self, paper_id: str) -> list[Citation]:
        """Get papers that cite this paper."""
        ...
```

## Supported Providers

| Provider | Free Tier | Rate Limit | Strength | Weakness |
|---|---|---|---|---|
| Semantic Scholar | Unlimited (no key) | 100 req/sec | Rich metadata, embeddings, TLDRs | Limited pre-2020 coverage |
| arXiv | Unlimited | 1 req/3 sec | Full-text access, preprints | Metadata only, no citations |
| Crossref | Unlimited | 50 req/sec | DOI resolution, citation counts | No abstracts in many cases |
| PubMed | Unlimited (E-utilities) | 10 req/sec | Biomedical coverage | Domain-specific |
| OpenAlex | Unlimited | 100 req/sec | Largest open research graph | Newer, smaller community |

## Source Selection Strategy

```python
class ResearchSourceRouter:
    def select_sources(self, query: str, filters: SearchFilters) -> list[BaseResearchProvider]:
        sources = []

        # Always search Semantic Scholar (broadest coverage)
        sources.append(self.providers["semantic_scholar"])

        # Add domain-specific sources
        if filters.domain == "biomedical":
            sources.append(self.providers["pubmed"])

        # Always search Crossref (DOI validation)
        sources.append(self.providers["crossref"])

        # Add arXiv if query matches CS/Physics/Math
        if self._matches_arxiv_domain(query):
            sources.append(self.providers["arxiv"])

        return sources
```

## Result Normalization

Each provider returns differently shaped data. The normalization layer converts to a canonical `Paper` schema:

```python
class Paper(BaseModel):
    external_id: dict[str, str]  # {semantic_scholar: "id", arxiv: "id", doi: "10.xxx"}
    title: str
    authors: list[Author]
    abstract: str | None
    publication_date: date | None
    venue: str | None
    citation_count: int | None
    pdf_url: str | None
    source: str  # which API returned it
    raw_metadata: dict  # original API response for caching
```

## Deduplication Strategy

```python
class DeduplicationService:
    """Multi-pass paper deduplication."""

    def deduplicate(self, papers: list[Paper]) -> list[Paper]:
        # Pass 1: Exact DOI match (fastest, ~70% of cases)
        doi_groups = self._group_by_doi(papers)

        # Pass 2: Title similarity for remaining
        remaining = [p for p in papers if p not in doi_groups]
        title_groups = self._cluster_by_title(remaining, threshold=0.9)

        # Pass 3: Author + Year for stragglers (preprint vs published)
        stragglers = [p for p in remaining if p not in title_groups]
        final_groups = self._match_by_author_year(stragglers)

        # Merge: keep the most complete record per group
        merged = self._merge_groups(doi_groups + title_groups + final_groups)

        # Rank by relevance score
        return sorted(merged, key=lambda p: p.relevance_score, reverse=True)

    def _group_by_doi(self, papers: list[Paper]) -> list[list[Paper]]:
        by_doi: dict[str, list[Paper]] = {}
        for p in papers:
            if p.doi:
                by_doi.setdefault(p.doi, []).append(p)
        return list(by_doi.values())

    def _merge_groups(self, groups: list[list[Paper]]) -> list[Paper]:
        """Keep the paper with the most complete metadata."""
        merged = []
        for group in groups:
            best = max(group, key=lambda p: (
                int(p.abstract is not None) +
                int(p.publication_date is not None) +
                int(p.pmid is not None) +
                (p.citation_count or 0)
            ))
            for p in group:
                best.external_id.update(p.external_id)
            merged.append(best)
        return merged
```

## Ranking Formula

```python
def calculate_relevance_score(paper: Paper, query: str) -> float:
    semantic = cosine_similarity(embed_query(query), embed_text(paper.abstract or ""))

    citations = math.log10(paper.citation_count + 1) / 5.0

    if paper.publication_date:
        years_ago = (datetime.now() - paper.publication_date).days / 365.0
        recency = max(0, 1 - years_ago / 10)
    else:
        recency = 0.5

    venue_quality = VENUE_SCORES.get(paper.venue, 0.3)

    return (
        0.5 * semantic +
        0.25 * min(citations, 1.0) +
        0.15 * recency +
        0.10 * venue_quality
    )
```

## Trade-offs

| Decision | Alternative | Rationale |
|---|---|---|
| Query all sources in parallel | Sequential with fallback | Parallel is faster; dedup handles duplicates |
| Normalization layer per source | Single schema per provider | Uniform output means agents don't know which source provided data |
| Title similarity dedup | Only DOI dedup | Catches preprint/published duplicates (up to 20% of results) |
| Heuristic relevance scoring | Learned ranking model | Simpler to implement; no training data required |
