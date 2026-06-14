from __future__ import annotations

import json
import pytest
from typing import Any

from app.agents.state import make_initial_state
from app.agents.summarizer_agent import SummarizerAgent
from app.agents.summarizer_citations import (
    extract_key_phrases,
    extract_statistics,
    detect_contradictory_language,
    build_citation_index,
    compute_compression_ratio,
)
from app.agents.summarizer_scoring import compute_summary_quality
from app.llm.mock_provider import MockProvider
from app.schemas.summarizer import (
    SectionSummary,
    CitationRecord,
    Contradiction,
    SummarizerMetrics,
)


# ── Fixtures ──────────────────────────────────────────────

def _sample_bundle(subtopic: str = "Architecture security", n: int = 5) -> dict[str, Any]:
    return {
        "subtopic": subtopic,
        "title": f"Evidence for: {subtopic}",
        "evidence": [
            {
                "query": "AI security",
                "source": "arxiv",
                "content": f"Agentic AI systems introduce novel security challenges in {subtopic.lower()}. "
                           f"Research shows that 73% of organisations report concerns about autonomous agent risks. "
                           f"However, some studies suggest current frameworks are adequate for known threats.",
                "relevance_score": 85.0 - i * 5,
                "collection": "research_papers",
                "metadata": {"source": "arxiv", "year": 2025},
                "retrieval_reason": "matched query",
                "chunk_id": f"chunk-{subtopic}-{i}",
            }
            for i in range(n)
        ],
        "sources": ["arxiv", "springer"],
        "confidence_score": 82.0,
        "coverage": True,
    }


def _sample_bundles() -> list[dict[str, Any]]:
    return [
        _sample_bundle("Architecture security", 5),
        _sample_bundle("Threat models", 4),
        _sample_bundle("Governance compliance", 3),
    ]


def _state_with_bundles() -> Any:
    state = make_initial_state(query="agentic AI security")
    state["planner_output"] = json.dumps({"subtopics": ["Architecture security", "Threat models", "Governance compliance"]})
    state["retrieved_documents"] = _sample_bundles()
    return state


# ── Citation / Extraction Tests ──────────────────────────

class TestExtraction:
    def test_key_phrases_extracted(self) -> None:
        text = "Agentic AI systems security vulnerabilities threats autonomous agents research"
        phrases = extract_key_phrases(text, top_n=3)
        assert len(phrases) >= 1
        assert all(len(p) > 3 for p in phrases)

    def test_key_phrases_empty(self) -> None:
        assert extract_key_phrases("", top_n=5) == []

    def test_statistics_extracted(self) -> None:
        text = "73% of organisations report concerns. Over 2 million incidents in 2025."
        stats = extract_statistics(text)
        assert len(stats) >= 1
        assert any("73%" in s for s in stats)

    def test_statistics_none(self) -> None:
        assert extract_statistics("no numbers here") == []

    def test_contradictory_language_detected(self) -> None:
        text = "However, some studies disagree. On the other hand, newer research suggests otherwise."
        signals = detect_contradictory_language(text)
        assert len(signals) >= 2
        assert any("however" in s.lower() for s in signals)

    def test_no_contradictory_language(self) -> None:
        assert detect_contradictory_language("plain consistent text") == []

    def test_citation_index_built(self) -> None:
        evidence = [
            {"chunk_id": "c1", "content": "doc1", "source": "src1", "query": "q1", "collection": "col1"},
            {"chunk_id": "c2", "content": "doc2", "source": "src2", "query": "q2", "collection": "col2"},
        ]
        index = build_citation_index(evidence)
        assert "c1" in index
        assert index["c1"]["source"] == "src1"

    def test_compression_ratio(self) -> None:
        r = compute_compression_ratio(1000, 150)
        assert r == 15.0
        r2 = compute_compression_ratio(0, 0)
        assert r2 == 0.0


# ── Quality Scoring Tests ────────────────────────────────

class TestScoring:
    def test_full_summary_scores_high(self) -> None:
        summary = SectionSummary(
            subtopic="test",
            executive_summary="A" * 100,
            key_findings=["finding 1", "finding 2", "finding 3"],
            supporting_evidence=["evidence 1", "evidence 2"],
            important_statistics=["73%", "2 million"],
            consensus_points=["consensus point"],
            citations=[CitationRecord(claim="c1", supporting_chunk_ids=["c1"])],
            contradictions=[],
            confidence_score=80.0,
            citation_count=1,
            source_count=2,
        )
        summary = compute_summary_quality(summary, {"evidence": [{"chunk_id": "c1"}]})
        assert summary.coverage_score > 50
        assert summary.summary_score > 50

    def test_empty_summary_scores_low(self) -> None:
        summary = SectionSummary(subtopic="test", executive_summary="short")
        summary = compute_summary_quality(summary, {"evidence": []})
        assert summary.summary_score < 50

    def test_contradictions_penalise_consistency(self) -> None:
        summary = SectionSummary(
            subtopic="test",
            executive_summary="A" * 100,
            key_findings=["f1", "f2", "f3"],
            supporting_evidence=["e1"],
            important_statistics=["s1"],
            consensus_points=["c1"],
            citations=[CitationRecord(claim="c1", supporting_chunk_ids=["c1"])],
            contradictions=[Contradiction(topic="t1", statements=["s1"])],
            confidence_score=80.0,
            citation_count=1,
            source_count=1,
        )
        summary = compute_summary_quality(summary, {"evidence": [{"chunk_id": "c1"}]})
        assert summary.consistency_score < 100
        assert summary.consistency_score == 80.0

    def test_evidence_density(self) -> None:
        summary = SectionSummary(
            subtopic="test",
            executive_summary="A" * 100,
            key_findings=["f1", "f2", "f3", "f4", "f5"],
            supporting_evidence=["e1", "e2"],
            important_statistics=["s1", "s2"],
            consensus_points=["c1", "c2", "c3"],
            citations=[CitationRecord(claim="c1", supporting_chunk_ids=["c1"])],
            contradictions=[],
            confidence_score=80.0,
            citation_count=1,
            source_count=1,
        )
        summary = compute_summary_quality(summary, {"evidence": [{"chunk_id": "c1"}]})
        assert summary.evidence_density > 50


# ── SummarizerAgent Tests ────────────────────────────────

class TestSummarizerAgent:
    @pytest.mark.asyncio
    async def test_summarizes_bundles(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        result = await agent.run(state)
        assert result.success is True
        assert len(state.get("summaries", [])) == 3

    @pytest.mark.asyncio
    async def test_each_summary_has_required_fields(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        for s in state["summaries"]:
            assert "subtopic" in s
            assert "executive_summary" in s
            assert len(s["key_findings"]) >= 1
            assert "citations" in s
            assert "citation_count" in s
            assert "summary_score" in s

    @pytest.mark.asyncio
    async def test_citations_tracked(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        total = sum(s.get("citation_count", 0) for s in state["summaries"])
        assert total > 0

    @pytest.mark.asyncio
    async def test_statistics_extracted(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        all_stats = []
        for s in state["summaries"]:
            all_stats.extend(s.get("important_statistics", []))
        assert len(all_stats) >= 1

    @pytest.mark.asyncio
    async def test_contradictions_detected(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        found = any(s.get("contradictions") for s in state["summaries"])

    @pytest.mark.asyncio
    async def test_metrics_populated(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        metrics = state["agent_metrics"]["summarizer"]
        assert metrics["bundles_processed"] == 3
        assert metrics["total_evidence_chunks"] > 0
        assert metrics["total_citations"] > 0
        assert metrics["latency_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_empty_bundles_fallback(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        state["retrieved_documents"] = []
        result = await agent.run(state)
        assert result.success is True
        assert len(state.get("summaries", [])) == 1
        assert "Insufficient evidence" in state["summaries"][0]["executive_summary"]

    @pytest.mark.asyncio
    async def test_partially_empty_bundles(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        bundles = _sample_bundles()
        bundles.append({"subtopic": "empty", "evidence": [], "sources": [], "confidence_score": 0.0, "coverage": False})
        state = _state_with_bundles()
        state["retrieved_documents"] = bundles
        await agent.run(state)
        assert len(state["summaries"]) == 4
        empty = [s for s in state["summaries"] if s["subtopic"] == "empty"]
        assert empty[0]["citation_count"] == 0

    @pytest.mark.asyncio
    async def test_state_updates(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        assert state["status"] in ("summarizer_complete", "completed")
        assert "summarizer" in state["agent_metrics"]

    @pytest.mark.asyncio
    async def test_compression_metric(self) -> None:
        provider = MockProvider()
        agent = SummarizerAgent(llm_provider=provider)
        state = _state_with_bundles()
        await agent.run(state)
        metrics = state["agent_metrics"]["summarizer"]
        assert metrics["compression_ratio"] > 0.0


# ── Debug Endpoint Test ──────────────────────────────────

class TestDebugEndpoint:
    def test_debug_request_model(self) -> None:
        from app.api.summarizer_debug import DebugSummarizerRequest
        req = DebugSummarizerRequest(retrieved_documents=_sample_bundles(), query="test")
        assert len(req.retrieved_documents) == 3
        assert req.query == "test"
