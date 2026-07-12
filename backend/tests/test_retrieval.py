from __future__ import annotations

import json
import pytest
from typing import Any

from app.agents.state import make_initial_state
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.retrieval_ranking import (
    compute_relevance_score,
    compute_source_quality,
    compute_content_hash,
    is_near_duplicate,
    _keyword_overlap,
)
from app.agents.retrieval_dedup import deduplicate_chunks
from app.llm.mock_provider import MockProvider
from app.schemas.retrieval import RetrievalBundle, RetrievedChunkSchema


# ── Fixtures ──────────────────────────────────────────────

_SAMPLE_PLANNER_OUTPUT = json.dumps(
    {
        "research_goal": "Study agentic AI security.",
        "research_questions": [
            "What are agentic AI vulnerabilities?",
            "What mitigation frameworks exist?",
        ],
        "keywords": ["agentic AI", "security"],
        "search_queries": [
            "agentic AI security vulnerabilities 2025",
            "autonomous agent threat modeling",
            "multi-agent system attack surfaces",
            "AI agent governance compliance",
            "emerging threats agentic systems",
        ],
        "subtopics": [
            "Architecture security",
            "Threat models",
            "Governance compliance",
        ],
        "methodology": "literature review",
        "expected_deliverables": ["security report"],
        "priority_areas": ["architecture", "threats"],
        "risk_areas": ["limited data"],
        "estimated_steps": 5,
    }
)


def _state_with_planner(query: str = "agentic AI security") -> Any:
    state = make_initial_state(query=query)
    state["planner_output"] = _SAMPLE_PLANNER_OUTPUT
    return state


# ── Ranking Tests ─────────────────────────────────────────


class TestRanking:
    def test_keyword_overlap_full(self) -> None:
        score = _keyword_overlap(
            "AI security threats in agentic systems", "AI security threats"
        )
        assert score > 0.5

    def test_keyword_overlap_none(self) -> None:
        score = _keyword_overlap("quantum physics", "AI security")
        assert score == 0.0

    def test_keyword_overlap_empty_query(self) -> None:
        score = _keyword_overlap("some content", "")
        assert score == 0.0

    def test_relevance_score_range(self) -> None:
        score = compute_relevance_score(
            "content about AI", "AI query", semantic_score=0.8
        )
        assert 0.0 <= score <= 100.0
        assert score > 20.0

    def test_relevance_semantic_boost(self) -> None:
        low = compute_relevance_score(
            "content", "AI", semantic_score=0.2, source_quality=10.0
        )
        high = compute_relevance_score(
            "content", "AI", semantic_score=0.9, source_quality=10.0
        )
        assert high > low

    def test_source_quality_basic(self) -> None:
        score = compute_source_quality({"source": "arxiv"})
        assert score >= 50.0

    def test_source_quality_unknown(self) -> None:
        score = compute_source_quality({"source": "unknown"})
        assert score == 50.0

    def test_source_quality_rich_metadata(self) -> None:
        score = compute_source_quality(
            {
                "source": "arxiv",
                "author": "Smith",
                "page_number": 5,
                "filename": "paper.pdf",
                "content": "x" * 600,
            }
        )
        assert score > 70.0

    def test_content_hash_consistency(self) -> None:
        h1 = compute_content_hash("The quick brown fox")
        h2 = compute_content_hash("The quick brown fox")
        assert h1 == h2

    def test_content_hash_different(self) -> None:
        h1 = compute_content_hash("The quick brown fox")
        h2 = compute_content_hash("The lazy dog")
        assert h1 != h2

    def test_near_duplicate_identical(self) -> None:
        assert is_near_duplicate("same content here", "same content here")

    def test_near_duplicate_similar(self) -> None:
        a = "the quick brown fox jumps over the lazy dog near the river"
        b = "the quick brown fox leaps over the lazy dog by the river"
        assert is_near_duplicate(a, b)

    def test_near_duplicate_different(self) -> None:
        a = "quantum physics is fascinating"
        b = "the weather today is sunny"
        assert not is_near_duplicate(a, b)


# ── Dedup Tests ───────────────────────────────────────────


class TestDedup:
    def test_no_duplicates(self) -> None:
        chunks = [
            {
                "content": "doc A",
                "chunk_id": "a",
                "source": "src1",
                "relevance_score": 50.0,
            },
            {
                "content": "doc B",
                "chunk_id": "b",
                "source": "src2",
                "relevance_score": 40.0,
            },
            {
                "content": "doc C",
                "chunk_id": "c",
                "source": "src3",
                "relevance_score": 30.0,
            },
        ]
        result = list(deduplicate_chunks(chunks))
        assert len(result) == 3

    def test_identical_chunks_removed(self) -> None:
        chunks = [
            {
                "content": "same content",
                "chunk_id": "a",
                "source": "src1",
                "relevance_score": 50.0,
            },
            {
                "content": "same content",
                "chunk_id": "b",
                "source": "src2",
                "relevance_score": 40.0,
            },
        ]
        result = list(deduplicate_chunks(chunks))
        assert len(result) == 1

    def test_same_chunk_id_removed(self) -> None:
        chunks = [
            {
                "content": "doc A",
                "chunk_id": "dup",
                "source": "src1",
                "relevance_score": 50.0,
            },
            {
                "content": "doc B",
                "chunk_id": "dup",
                "source": "src2",
                "relevance_score": 40.0,
            },
        ]
        result = list(deduplicate_chunks(chunks))
        assert len(result) == 1

    def test_near_duplicates_removed(self) -> None:
        a = "the quick brown fox jumps over the lazy dog near the river bank"
        b = "the quick brown fox leaps over the lazy dog near the river bank"
        chunks = [
            {"content": a, "chunk_id": "a", "source": "src1", "relevance_score": 50.0},
            {"content": b, "chunk_id": "b", "source": "src2", "relevance_score": 40.0},
        ]
        result = list(deduplicate_chunks(chunks))
        assert len(result) == 1


# ── RetrievalBundle Schema Tests ──────────────────────────


class TestRetrievalBundle:
    def test_minimal_bundle(self) -> None:
        bundle = RetrievalBundle(subtopic="AI", title="test")
        assert bundle.subtopic == "AI"
        assert bundle.evidence == []
        assert bundle.sources == []
        assert bundle.confidence_score == 0.0
        assert bundle.coverage is False

    def test_bundle_with_evidence(self) -> None:
        evidence = [
            RetrievedChunkSchema(
                query="q",
                source="s",
                content="c",
                collection="col",
                relevance_score=80.0,
            ),
        ]
        bundle = RetrievalBundle(
            subtopic="security",
            title="Security evidence",
            evidence=evidence,
            sources=["s"],
            confidence_score=80.0,
            coverage=True,
        )
        assert bundle.coverage is True
        assert bundle.confidence_score == 80.0
        assert len(bundle.evidence) == 1


# ── RetrievalAgent Tests ──────────────────────────────────


class TestRetrievalAgent:
    @pytest.mark.asyncio
    async def test_retrieval_success(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner("agentic AI security")
        result = await agent.run(state)
        assert result.success is True
        assert "retrieval" in state.get("agent_metrics", {})
        assert "retrieval_debug" in state.get("agent_metrics", {})
        bundles = state.get("retrieved_documents", [])
        assert len(bundles) > 0

    @pytest.mark.asyncio
    async def test_retrieved_documents_are_bundles(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        bundles = state.get("retrieved_documents", [])
        for b in bundles:
            assert "subtopic" in b
            assert "evidence" in b
            assert "sources" in b
            assert "confidence_score" in b

    @pytest.mark.asyncio
    async def test_metrics_on_success(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        metrics = state["agent_metrics"]["retrieval"]
        assert metrics["latency_seconds"] >= 0
        assert metrics["total_collections_searched"] == 5
        assert metrics["documents_before_dedup"] >= 0
        assert metrics["documents_after_dedup"] >= 0
        assert metrics["duplicates_removed"] >= 0

    @pytest.mark.asyncio
    async def test_state_updates(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        assert state["status"] in ("retrieval_complete", "completed")
        assert len(state.get("retrieved_documents", [])) > 0

    @pytest.mark.asyncio
    async def test_no_planner_still_works(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = make_initial_state(query="test query")
        result = await agent.run(state)
        assert result.success is True
        bundles = state.get("retrieved_documents", [])
        assert len(bundles) > 0

    @pytest.mark.asyncio
    async def test_debug_info_present(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        debug = state["agent_metrics"].get("retrieval_debug", {})
        assert "search_queries_used" in debug
        assert "total_collections_searched" in debug
        assert "duplicates_removed" in debug

    @pytest.mark.asyncio
    async def test_each_bundle_has_evidence(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        bundles = state.get("retrieved_documents", [])
        for b in bundles:
            assert len(b["evidence"]) > 0, f"bundle {b['subtopic']} has no evidence"

    @pytest.mark.asyncio
    async def test_bundle_subtopics_from_planner(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        bundles = state.get("retrieved_documents", [])
        subtopics_in_bundles = [b["subtopic"] for b in bundles]
        assert "Architecture security" in subtopics_in_bundles
        assert "Threat models" in subtopics_in_bundles

    @pytest.mark.asyncio
    async def test_evidence_scored(self) -> None:
        provider = MockProvider()
        agent = RetrievalAgent(llm_provider=provider)
        state = _state_with_planner()
        await agent.run(state)
        bundles = state.get("retrieved_documents", [])
        for b in bundles:
            for e in b["evidence"]:
                assert 0.0 <= e.get("relevance_score", -1) <= 100.0


# ── Debug Endpoint Schema Test ────────────────────────────


class TestDebugEndpoint:
    def test_debug_request_model(self) -> None:
        from app.api.retrieval_debug import DebugRetrievalRequest

        req = DebugRetrievalRequest(
            query="AI security", planner_output_json=_SAMPLE_PLANNER_OUTPUT
        )
        assert req.query == "AI security"
        assert req.planner_output_json == _SAMPLE_PLANNER_OUTPUT
