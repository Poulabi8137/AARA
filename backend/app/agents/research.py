from __future__ import annotations

import hashlib
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import AgentContext, AgentOutput, AgentPhase, ConfidenceScore
from app.ai.retrieval.chunking import TextChunker
from app.ai.retrieval.citation import Citation, CitationPreserver
from app.ai.retrieval.retriever import BaseRetriever


class ResearchAgent(BaseAgent):
    agent_id: str = "research"
    agent_name: str = "Research Agent"
    version: str = "2.0"
    max_retries: int = 3
    timeout_seconds: int = 60

    def __init__(
        self,
        retriever: BaseRetriever | None = None,
        event_dispatcher: Any | None = None,
    ) -> None:
        super().__init__()
        self._retriever = retriever
        self._citation_preserver = CitationPreserver()
        self._chunker = TextChunker()
        self._event_dispatcher = event_dispatcher

    async def _emit_progress(self, context: AgentContext, percentage: float, message: str) -> None:
        if not self._event_dispatcher or not context.workflow_id:
            return
        await self._event_dispatcher.dispatch_progress(
            workflow_id=context.workflow_id,
            step_id="research",
            agent_id="Research",
            percentage=percentage,
            message=message,
        )

    async def execute(self, context: AgentContext) -> AgentOutput:
        self._lifecycle.transition(AgentPhase.PLANNING)
        start_time = time.monotonic()

        try:
            query = context.input.get("query", "")
            sources = context.input.get("sources", [])
            limit = context.input.get("limit", 10)

            expanded_queries = await self.expand_queries(query)
            all_queries = [query] + expanded_queries
            await self._emit_progress(
                context, 10.0,
                f"Expanded query into {len(all_queries)} search variants",
            )

            self._lifecycle.transition(AgentPhase.REASONING)
            self._lifecycle.transition(AgentPhase.TOOL_USE)
            all_results: list[dict[str, Any]] = []
            search_metadata: dict[str, Any] = {
                "original_query": query,
                "expanded_queries": expanded_queries,
                "sources_queried": sources,
                "total_searches": 0,
            }

            for i, q in enumerate(all_queries, start=1):
                results = await self._search_source(q, sources, limit)
                search_metadata["total_searches"] += 1
                for r in results:
                    self._citation_preserver.add_citation(Citation(
                        source_id=r.get("doi", hashlib.md5(r.get("title", "").encode()).hexdigest()[:8]),  # noqa: E501
                        source_title=r.get("title", "Untitled"),
                        text=r.get("abstract", ""),
                    ))
                all_results.extend(results)
                await self._emit_progress(
                    context, 10.0 + (i / len(all_queries)) * 50.0,
                    f"Searched {i}/{len(all_queries)} query variants — "
                    f"{len(all_results)} papers found so far",
                )

            papers = self._deduplicate(all_results)
            await self._emit_progress(
                context, 75.0,
                f"Deduplicated {len(all_results)} results into {len(papers)} unique papers",
            )

            self._lifecycle.transition(AgentPhase.REFLECTING)
            relevance_scores = await self.rate_relevance(papers)
            await self._emit_progress(
                context, 90.0,
                f"Scored relevance for {len(papers)} papers",
            )

            self._lifecycle.transition(AgentPhase.VALIDATING)
            paper_collection = {
                "papers": papers,
                "search_metadata": search_metadata,
                "relevance_scores": relevance_scores,
            }
            citation_support = sum(1 for p in papers if p.get("citation_count", 0) > 10) / max(len(papers), 1)
            has_abstract = sum(1 for p in papers if p.get("abstract")) / max(len(papers), 1)
            avg_relevance = sum(p.get("relevance_score", 0) for p in papers) / max(len(papers), 1)
            overall_confidence = (citation_support * 0.3 + has_abstract * 0.4 + avg_relevance * 0.3)

            output = AgentOutput(
                agent_id=self.agent_id,
                workflow_id=context.workflow_id,
                output={"paper_collection": paper_collection},
                summary=f"Researched {len(papers)} papers across {search_metadata['total_searches']} searches",  # noqa: E501
                duration_ms=int((time.monotonic() - start_time) * 1000),
                confidence=ConfidenceScore(
                    overall=round(min(overall_confidence, 1.0), 3),
                    citation_support=round(citation_support, 3),
                    factual_grounding=round(has_abstract, 3),
                    reasoning_coherence=round(avg_relevance, 3),
                ),
            )

            if not await self.validate_output(output):
                output.summary = "Validation failed for research output"
                output.output = {"error": "validation_failed", "paper_collection": paper_collection}

            self._lifecycle.transition(AgentPhase.OUTPUTTING)
            return output

        except Exception as e:
            return await self.handle_error(e, context)

    async def expand_queries(self, query: str) -> list[str]:
        words = query.split()
        expansions = [query]
        if len(words) > 2:
            expansions.append(f"{query} review")
            expansions.append(f"{query} recent advances")
            expansions.append(f"{query} methodology")
        elif len(words) > 1:
            expansions.append(f"{query} survey")
            expansions.append(f"{query} analysis")
        else:
            expansions.append(f"{query} research")
            expansions.append(f"{query} advances")
        return expansions[:5]

    async def rate_relevance(self, papers: list[dict]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for paper in papers:
            pid = paper.get("id", paper.get("doi", ""))
            score = 1.0
            if paper.get("citation_count", 0) > 100:
                score += 0.3
            if paper.get("relevance_score"):
                score = min(score * paper["relevance_score"], 1.0)
            if paper.get("abstract"):
                score = min(score + 0.1, 1.0)
            scores[pid] = round(score, 2)
        return scores

    async def validate_output(self, output: AgentOutput) -> bool:
        collection = output.output.get("paper_collection", {})
        if not isinstance(collection, dict):
            return False
        if "papers" not in collection:
            return False
        if not isinstance(collection["papers"], list):
            return False
        return "search_metadata" in collection

    def _deduplicate(self, papers: list[dict]) -> list[dict]:
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()
        unique: list[dict] = []
        for p in papers:
            doi = p.get("doi", "")
            title = p.get("title", "").lower().strip()
            if doi and doi in seen_dois:
                continue
            if title and title in seen_titles:
                continue
            if doi:
                seen_dois.add(doi)
            if title:
                seen_titles.add(title)
            unique.append(p)
        return unique

    async def _search_source(self, query: str, sources: list[str], limit: int) -> list[dict]:
        if self._retriever is not None:
            results = await self._retriever.retrieve(query, limit=limit)
            return [
                {
                    "title": r.metadata.get("title", f"Result from {r.source}"),
                    "abstract": r.content,
                    "source": r.source,
                    "score": r.score,
                    "doi": r.metadata.get("doi", ""),
                    "url": r.metadata.get("url", ""),
                    "authors": r.metadata.get("authors", []),
                    "year": r.metadata.get("year", 0),
                    "citation_count": r.metadata.get("citation_count", 0),
                    "relevance_score": r.score,
                    "id": r.metadata.get("id", hashlib.md5(r.content.encode()).hexdigest()[:12]),
                }
                for r in results
            ]
        return []
