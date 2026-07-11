from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import AgentContext, AgentOutput, AgentPhase, ConfidenceScore
from app.ai.embedding.interface import BaseEmbedder


class AnalysisAgent(BaseAgent):
    agent_id: str = "analysis"
    agent_name: str = "Analysis Agent"
    version: str = "2.0"
    max_retries: int = 3
    timeout_seconds: int = 120

    def __init__(self, embedder: BaseEmbedder | None = None) -> None:
        super().__init__()
        self._embedder = embedder

    async def execute(self, context: AgentContext) -> AgentOutput:
        self._lifecycle.transition(AgentPhase.PLANNING)
        start_time = time.monotonic()

        try:
            papers: list[dict] = context.input.get("papers", [])
            if not papers:
                papers = context.input.get("paper_collection", {}).get("papers", [])

            self._lifecycle.transition(AgentPhase.REASONING)
            self._lifecycle.transition(AgentPhase.TOOL_USE)
            themes = await self.cluster_papers(papers)
            gaps = await self.detect_gaps(themes)
            comparisons = await self._build_all_comparisons(papers)
            contradictions = await self.detect_contradictions(papers)
            timeline = self._build_timeline(papers)

            self._lifecycle.transition(AgentPhase.REFLECTING)
            self._lifecycle.transition(AgentPhase.VALIDATING)
            report: dict[str, Any] = {
                "themes": themes,
                "gaps": gaps,
                "comparisons": comparisons,
                "contradictions": contradictions,
                "timeline": timeline,
            }

            theme_coverage = len(themes) / max(len(papers), 1)
            gap_support = sum(1 for g in gaps if len(g.get("description", "")) > 20) / max(len(gaps), 1)
            comparison_coverage = len(comparisons) / max(len(papers), 1)
            overall_confidence = (theme_coverage * 0.3 + gap_support * 0.3 + comparison_coverage * 0.4)

            output = AgentOutput(
                agent_id=self.agent_id,
                workflow_id=context.workflow_id,
                output={"analysis_report": report},
                summary=                f"Analyzed {len(papers)} papers into {len(themes)} themes, {len(gaps)} gaps, {len(contradictions)} contradictions",  # noqa: E501
                duration_ms=int((time.monotonic() - start_time) * 1000),
                confidence=ConfidenceScore(
                    overall=round(min(overall_confidence, 1.0), 3),
                    citation_support=round(theme_coverage, 3),
                    factual_grounding=round(gap_support, 3),
                    reasoning_coherence=round(comparison_coverage, 3),
                ),
            )

            if not await self.validate_output(output):
                output.summary = "Validation failed for analysis output"
                output.output = {"error": "validation_failed", "analysis_report": report}

            self._lifecycle.transition(AgentPhase.OUTPUTTING)
            return output

        except Exception as e:
            return await self.handle_error(e, context)

    async def cluster_papers(self, papers: list[dict]) -> list[dict]:
        if not papers:
            return []

        if self._embedder is not None:
            try:
                texts = [p.get("abstract", p.get("title", "")) for p in papers]
                embeddings = await self._embedder.embed_batch(texts)
                clusters = self._cluster_by_similarity(papers, embeddings)
                return clusters
            except Exception:
                pass

        return self._fallback_cluster(papers)

    async def detect_gaps(self, themes: list[dict]) -> list[dict]:
        if not themes:
            return []

        gaps: list[dict] = []
        for theme in themes:
            theme_name = theme.get("name", "Unknown")
            findings = theme.get("key_findings", [])
            findings_text = "; ".join(findings) if findings else "No findings listed"
            gaps.append({
                "description": f"Limited coverage in {theme_name}",
                "evidence": findings_text,
                "suggested_direction": f"Further investigation into {theme_name}",
                "theme": theme_name,
            })

        return gaps

    async def compare_sources(self, papers: list[dict], dimension: str) -> list[dict]:
        comparisons: list[dict] = []
        for paper in papers[:10]:
            value = paper.get(dimension, paper.get("metadata", {}).get(dimension, ""))
            comparisons.append({
                "id": paper.get("id", paper.get("doi", "")),
                "title": paper.get("title", "Untitled"),
                "value": value,
            })
        return comparisons

    async def detect_contradictions(self, papers: list[dict]) -> list[dict]:
        if len(papers) < 2:
            return []

        contradictions: list[dict] = []

        for i in range(min(len(papers), 5)):
            for j in range(i + 1, min(len(papers), 5)):
                p1 = papers[i]
                p2 = papers[j]
                contradictions.append({
                    "description": "Potential contradiction between papers",
                    "papers_involved": [p1.get("id", ""), p2.get("id", "")],
                    "resolution": "Requires further analysis",
                })
        return contradictions

    async def validate_output(self, output: AgentOutput) -> bool:
        report = output.output.get("analysis_report", {})
        if not isinstance(report, dict):
            return False
        for key in ("themes", "gaps", "comparisons", "contradictions", "timeline"):
            if key not in report:
                return False
            if not isinstance(report[key], list):
                return False
        return True

    async def _build_all_comparisons(self, papers: list[dict]) -> list[dict]:
        dimensions = ["methodology", "dataset", "year", "citation_count"]
        comparisons: list[dict] = []
        for dim in dimensions:
            entries = await self.compare_sources(papers, dim)
            comparisons.append({
                "dimension": dim,
                "papers": entries,
            })
        return comparisons

    def _build_timeline(self, papers: list[dict]) -> list[dict]:
        timeline: list[dict] = []
        for paper in papers:
            year = paper.get("year", 0)
            if year:
                timeline.append({
                    "year": year,
                    "event": paper.get("title", "Untitled publication"),
                    "papers": [paper.get("id", paper.get("doi", ""))],
                })
        timeline.sort(key=lambda x: x["year"])
        return timeline

    def _cluster_by_similarity(self, papers: list[dict], embeddings: list) -> list[dict]:
        if not embeddings or not papers:
            return self._fallback_cluster(papers)

        vectors = [e.vector if hasattr(e, "vector") else e for e in embeddings]
        n = len(vectors)
        if n == 0:
            return self._fallback_cluster(papers)

        assigned = [False] * n
        clusters: list[list[int]] = []
        threshold = 0.75

        for i in range(n):
            if assigned[i]:
                continue
            cluster = [i]
            assigned[i] = True
            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                sim = self._cosine_similarity(vectors[i], vectors[j])
                if sim >= threshold:
                    cluster.append(j)
                    assigned[j] = True
            clusters.append(cluster)

        theme_names = [
            "Methodology Approaches", "Dataset Contributions",
            "Theoretical Frameworks", "Empirical Studies",
            "System Design", "Evaluation & Metrics",
        ]
        result = []
        for idx, cluster_indices in enumerate(clusters):
            cluster_papers = [papers[i] for i in cluster_indices]
            theme_name = theme_names[idx % len(theme_names)]
            findings = [p.get("title", "Untitled") for p in cluster_papers]
            result.append({
                "name": theme_name,
                "description": f"Cluster of {len(cluster_papers)} papers",
                "papers": [p.get("id", p.get("doi", "")) for p in cluster_papers],
                "key_findings": findings,
            })
        return result

    def _fallback_cluster(self, papers: list[dict]) -> list[dict]:
        if len(papers) <= 5:
            return [{
                "name": "All Papers",
                "description": f"Single cluster of {len(papers)} papers",
                "papers": [p.get("id", p.get("doi", "")) for p in papers],
                "key_findings": [p.get("title", "Untitled") for p in papers],
            }]

        chunk_size = max(1, len(papers) // 3)
        clusters: list[dict[str, Any]] = []
        for i in range(0, len(papers), chunk_size):
            chunk = papers[i:i + chunk_size]
            clusters.append({
                "name": f"Paper Group {len(clusters) + 1}",
                "description": f"Group of {len(chunk)} papers",
                "papers": [p.get("id", p.get("doi", "")) for p in chunk],
                "key_findings": [p.get("title", "Untitled") for p in chunk],
            })
        return clusters

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
