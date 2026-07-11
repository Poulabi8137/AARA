from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.analysis import AnalysisAgent
from app.agents.idea_generation import IdeaGenerationAgent
from app.agents.models import (
    AgentContext,
    AgentOutput,
    AgentPhase,
    AgentStep,
    ExecutionPlan,
    WorkflowResult,
)
from app.agents.planning import PlanningAgent
from app.agents.research import ResearchAgent
from app.agents.review import ReviewAgent
from app.agents.supervisor import RetryableError, SupervisorAgent
from app.agents.writing import WritingAgent
from app.ai.embedding.interface import EmbeddingResult
from app.ai.retrieval.retriever import RetrieverResult
from app.core.exceptions import AARAError, ErrorCode


# ---------------------------------------------------------------------------
# Fixtures (shared)
# ---------------------------------------------------------------------------

@pytest.fixture
def agent_context() -> AgentContext:
    return AgentContext(
        workflow_id="wf-1",
        step_id="step-1",
        trace_id="trace-1",
        input={"query": "deep learning for NLP", "workspace_id": "ws-1"},
    )


@pytest.fixture
def agent_output() -> AgentOutput:
    return AgentOutput(
        agent_id="test",
        workflow_id="wf-1",
        output={"result": "ok"},
        summary="test output",
        duration_ms=100,
    )


@pytest.fixture
def mock_registry() -> MagicMock:
    registry = MagicMock()
    registry.get = MagicMock(return_value=AsyncMock())
    return registry


@pytest.fixture
def sample_papers() -> list[dict]:
    return [
        {
            "id": "p1",
            "doi": "10.1000/p1",
            "title": "Deep Learning Advances",
            "abstract": "Advances in deep learning for NLP tasks.",
            "year": 2024,
            "citation_count": 150,
            "relevance_score": 0.9,
            "authors": ["Alice"],
            "source": "arxiv",
            "score": 0.95,
            "url": "https://example.com/p1",
        },
        {
            "id": "p2",
            "doi": "10.1000/p2",
            "title": "Transformers in NLP",
            "abstract": "Transformer models for NLP.",
            "year": 2023,
            "citation_count": 80,
            "relevance_score": 0.85,
            "authors": ["Bob"],
            "source": "pubmed",
            "score": 0.88,
            "url": "https://example.com/p2",
        },
    ]


# ===========================================================================
# PlanningAgent Tests
# ===========================================================================


class TestPlanningAgent:
    @pytest.fixture
    def agent(self) -> PlanningAgent:
        return PlanningAgent()

    @pytest.mark.asyncio
    async def test_create_plan_decomposes_query(self, agent: PlanningAgent):
        context = AgentContext(
            workflow_id="w1",
            step_id="s1",
            trace_id="t1",
            input={"query": "transformer attention mechanisms in NLP", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        plan: ExecutionPlan = output.output["plan"]
        decomposition = output.output["decomposition"]
        assert len(plan.steps) == 5
        assert decomposition["original_query"] == "transformer attention mechanisms in NLP"
        assert "transformer" in decomposition["key_concepts"]

    @pytest.mark.asyncio
    async def test_create_plan_contains_required_steps(self, agent: PlanningAgent):
        context = AgentContext(
            workflow_id="w2", step_id="s1", trace_id="t1",
            input={"query": "few-shot learning", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        plan: ExecutionPlan = output.output["plan"]
        step_ids = {s.agent_id for s in plan.steps}
        expected = {"research", "analysis", "idea_gen", "writing", "review"}
        assert expected.issubset(step_ids)

    @pytest.mark.asyncio
    async def test_create_plan_sets_priorities(self, agent: PlanningAgent):
        context = AgentContext(
            workflow_id="w3", step_id="s1", trace_id="t1",
            input={"query": "reinforcement learning", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        plan: ExecutionPlan = output.output["plan"]
        assert plan.steps[0].priority == 1
        assert plan.steps[-1].priority == 5

    @pytest.mark.asyncio
    async def test_create_plan_dependencies(self, agent: PlanningAgent):
        context = AgentContext(
            workflow_id="w4", step_id="s1", trace_id="t1",
            input={"query": "graph neural networks", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        plan: ExecutionPlan = output.output["plan"]
        analysis = plan.steps[1]
        assert "research" in analysis.depends_on

    @pytest.mark.asyncio
    async def test_validate_plan_valid(self, agent: PlanningAgent):
        output = AgentOutput(
            agent_id="planner",
            workflow_id="w1",
            output={
                "plan": ExecutionPlan(
                    steps=[
                        AgentStep(agent_id="research", input={}, priority=1),
                        AgentStep(agent_id="analysis", input={}, priority=2, depends_on=["research"]),
                        AgentStep(agent_id="idea_gen", input={}, priority=3, depends_on=["analysis"]),
                        AgentStep(agent_id="writing", input={}, priority=4, depends_on=["idea_gen"]),
                        AgentStep(agent_id="review", input={}, priority=5, depends_on=["writing"]),
                    ],
                    estimated_cost={"total_tokens": 100.0, "search_calls": 2.0, "llm_calls": 5.0},
                    requires_approval=["research", "analysis", "idea_gen", "writing"],
                ),
            },
        )
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_plan_invalid_no_steps(self, agent: PlanningAgent):
        output = AgentOutput(
            agent_id="planner",
            workflow_id="w1",
            output={
                "plan": ExecutionPlan(
                    steps=[],
                    estimated_cost={"total_tokens": 0.0, "search_calls": 0.0, "llm_calls": 0.0},
                ),
            },
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_validate_plan_invalid_missing_required(self, agent: PlanningAgent):
        output = AgentOutput(
            agent_id="planner",
            workflow_id="w1",
            output={
                "plan": ExecutionPlan(
                    steps=[AgentStep(agent_id="research", input={}, priority=1)],
                    estimated_cost={"total_tokens": 0.0, "search_calls": 0.0, "llm_calls": 1.0},
                ),
            },
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_generate_research_directions(self, agent: PlanningAgent):
        output = await agent.execute(
            AgentContext(
                workflow_id="w1", step_id="s1", trace_id="t1",
                input={"query": "prompt engineering", "workspace_id": "ws-1"},
            )
        )
        decomposition = output.output["decomposition"]
        directions = decomposition["research_directions"]
        assert len(directions) >= 1
        assert any("prompt engineering" in d for d in directions)

    @pytest.mark.asyncio
    async def test_plan_estimated_cost(self, agent: PlanningAgent):
        output = await agent.execute(
            AgentContext(
                workflow_id="w1", step_id="s1", trace_id="t1",
                input={"query": "model compression techniques", "workspace_id": "ws-1"},
            )
        )
        plan: ExecutionPlan = output.output["plan"]
        cost = plan.estimated_cost
        assert cost["total_tokens"] > 0
        assert cost["search_calls"] > 0
        assert cost["llm_calls"] == 5


# ===========================================================================
# ResearchAgent Tests
# ===========================================================================


class TestResearchAgent:
    @pytest.fixture
    def agent(self) -> ResearchAgent:
        return ResearchAgent()

    async def _mock_lifecycle(self, agent: ResearchAgent) -> None:
        agent._lifecycle.transition = MagicMock()  # type: ignore[method-assign]

    @pytest.mark.asyncio
    async def test_execute_retrieves_papers(self, agent: ResearchAgent, sample_papers):
        await self._mock_lifecycle(agent)
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(
                    content=p["abstract"],
                    score=p["relevance_score"],
                    source=p["source"],
                    metadata={
                        "title": p["title"],
                        "doi": p["doi"],
                        "id": p["id"],
                        "citation_count": p["citation_count"],
                        "year": p["year"],
                        "authors": p["authors"],
                        "url": p["url"],
                        "relevance_score": p["relevance_score"],
                    },
                )
                for p in sample_papers
            ]
        )
        agent._retriever = retriever
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={"query": "deep learning", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        assert "paper_collection" in output.output
        assert len(output.output["paper_collection"]["papers"]) == 2

    @pytest.mark.asyncio
    async def test_execute_no_retriever_returns_empty(self, agent: ResearchAgent):
        await self._mock_lifecycle(agent)
        agent._retriever = None
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={"query": "nlp", "workspace_id": "ws-1"},
        )
        output = await agent.execute(context)
        assert len(output.output["paper_collection"]["papers"]) == 0

    @pytest.mark.asyncio
    async def test_expand_queries_returns_list(self, agent: ResearchAgent):
        result = await agent.expand_queries("transformer models")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "transformer models" in result

    @pytest.mark.asyncio
    async def test_expand_queries_short_query(self, agent: ResearchAgent):
        result = await agent.expand_queries("AI")
        assert "AI research" in result
        assert "AI advances" in result

    @pytest.mark.asyncio
    async def test_rate_relevance_scores_papers(self, agent: ResearchAgent, sample_papers):
        scores = await agent.rate_relevance(sample_papers)
        assert "p1" in scores
        assert scores["p1"] > 0

    @pytest.mark.asyncio
    async def test_rate_relevance_high_citation_boost(self, agent: ResearchAgent):
        papers = [{"id": "p1", "citation_count": 200, "relevance_score": 0.5, "abstract": "some text"}]
        scores = await agent.rate_relevance(papers)
        assert scores["p1"] > 0.5

    @pytest.mark.asyncio
    async def test_validate_output_valid(self, agent: ResearchAgent):
        output = AgentOutput(
            agent_id="research",
            workflow_id="w1",
            output={
                "paper_collection": {
                    "papers": [{"id": "p1"}],
                    "search_metadata": {"total_searches": 1},
                }
            },
        )
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_output_invalid_no_papers(self, agent: ResearchAgent):
        output = AgentOutput(
            agent_id="research",
            workflow_id="w1",
            output={"paper_collection": {"search_metadata": {}}},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_validate_output_invalid_not_dict(self, agent: ResearchAgent):
        output = AgentOutput(
            agent_id="research",
            workflow_id="w1",
            output={"paper_collection": "not_a_dict"},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_paper_collection_with_search(self, agent: ResearchAgent, sample_papers):
        await self._mock_lifecycle(agent)
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(
            return_value=[
                RetrieverResult(
                    content=p["abstract"],
                    score=p["relevance_score"],
                    source=p["source"],
                    metadata={"title": p["title"], "doi": p["doi"]},
                )
                for p in sample_papers
            ]
        )
        agent._retriever = retriever
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={"query": "deep learning for NLP", "sources": ["arxiv"], "limit": 5},
        )
        output = await agent.execute(context)
        meta = output.output["paper_collection"]["search_metadata"]
        assert meta["total_searches"] >= 1
        assert meta["original_query"] == "deep learning for NLP"

    @pytest.mark.asyncio
    async def test_deduplicate_removes_duplicates(self, agent: ResearchAgent):
        papers = [
            {"doi": "10.1000/dup", "title": "Duplicate Paper"},
            {"doi": "10.1000/dup", "title": "Duplicate Paper"},
            {"doi": "10.1000/unique", "title": "Unique Paper"},
        ]
        unique = agent._deduplicate(papers)
        assert len(unique) == 2


# ===========================================================================
# AnalysisAgent Tests
# ===========================================================================


class TestAnalysisAgent:
    @pytest.fixture
    def agent(self) -> AnalysisAgent:
        return AnalysisAgent()

    @pytest.mark.asyncio
    async def test_cluster_themes_groups_papers(self, agent: AnalysisAgent, sample_papers):
        themes = await agent.cluster_papers(sample_papers)
        assert isinstance(themes, list)
        assert len(themes) >= 1
        assert themes[0]["name"] == "All Papers"

    @pytest.mark.asyncio
    async def test_cluster_themes_with_embedder(self, agent: AnalysisAgent, sample_papers):
        embedder = AsyncMock()
        embedder.embed_batch = AsyncMock(
            return_value=[EmbeddingResult(vector=[0.1, 0.2, 0.3]) for _ in sample_papers]
        )
        agent._embedder = embedder
        themes = await agent.cluster_papers(sample_papers)
        assert len(themes) >= 1

    @pytest.mark.asyncio
    async def test_cluster_themes_empty(self, agent: AnalysisAgent):
        themes = await agent.cluster_papers([])
        assert themes == []

    @pytest.mark.asyncio
    async def test_detect_gaps_identifies_gaps(self, agent: AnalysisAgent):
        themes = [{"name": "NLP", "key_findings": ["Finding A"]}]
        gaps = await agent.detect_gaps(themes)
        assert len(gaps) == 1
        assert "Limited coverage in NLP" in gaps[0]["description"]

    @pytest.mark.asyncio
    async def test_detect_gaps_empty_themes(self, agent: AnalysisAgent):
        gaps = await agent.detect_gaps([])
        assert gaps == []

    @pytest.mark.asyncio
    async def test_detect_contradictions_finds_conflicts(self, agent: AnalysisAgent, sample_papers):
        contradictions = await agent.detect_contradictions(sample_papers)
        assert len(contradictions) >= 1
        assert contradictions[0]["description"] == "Potential contradiction between papers"

    @pytest.mark.asyncio
    async def test_detect_contradictions_single_paper(self, agent: AnalysisAgent):
        contradictions = await agent.detect_contradictions([{"id": "p1"}])
        assert contradictions == []

    @pytest.mark.asyncio
    async def test_compare_sources_by_dimension(self, agent: AnalysisAgent, sample_papers):
        comparisons = await agent.compare_sources(sample_papers, "year")
        assert len(comparisons) == 2
        assert comparisons[0]["value"] == 2024

    @pytest.mark.asyncio
    async def test_validate_output_valid(self, agent: AnalysisAgent):
        report = {
            "themes": [{"name": "T1"}],
            "gaps": [{"description": "G1"}],
            "comparisons": [{"dimension": "year", "papers": []}],
            "contradictions": [],
            "timeline": [{"year": 2024, "event": "Paper", "papers": ["p1"]}],
        }
        output = AgentOutput(agent_id="analysis", workflow_id="w1", output={"analysis_report": report})
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_output_missing_key(self, agent: AnalysisAgent):
        output = AgentOutput(
            agent_id="analysis",
            workflow_id="w1",
            output={"analysis_report": {"themes": [], "gaps": [], "comparisons": [], "contradictions": []}},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_cosine_similarity(self, agent: AnalysisAgent):
        sim = agent._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert sim == 1.0

    @pytest.mark.asyncio
    async def test_cosine_similarity_orthogonal(self, agent: AnalysisAgent):
        sim = agent._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_fallback_cluster_small_set(self, agent: AnalysisAgent):
        papers = [{"id": "p1"}, {"id": "p2"}]
        clusters = agent._fallback_cluster(papers)
        assert len(clusters) == 1
        assert clusters[0]["name"] == "All Papers"

    @pytest.mark.asyncio
    async def test_build_timeline_sorts_by_year(self, agent: AnalysisAgent):
        papers = [
            {"id": "p1", "year": 2023, "title": "Later"},
            {"id": "p2", "year": 2021, "title": "Earlier"},
        ]
        timeline = agent._build_timeline(papers)
        assert timeline[0]["year"] == 2021
        assert timeline[1]["year"] == 2023

    @pytest.mark.asyncio
    async def test_execute_runs_full_analysis(self, agent: AnalysisAgent, sample_papers):
        agent._lifecycle.transition = MagicMock()  # type: ignore[method-assign]
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={"papers": sample_papers},
        )
        output = await agent.execute(context)
        report = output.output["analysis_report"]
        assert "themes" in report
        assert "gaps" in report
        assert "comparisons" in report
        assert "contradictions" in report
        assert "timeline" in report


# ===========================================================================
# IdeaGenerationAgent Tests
# ===========================================================================


class TestIdeaGenerationAgent:
    @pytest.fixture
    def agent(self) -> IdeaGenerationAgent:
        return IdeaGenerationAgent()

    @pytest.fixture
    def sample_gaps(self) -> list[dict]:
        return [
            {
                "id": "gap1",
                "description": "Limited research on efficient transformer architectures for edge devices",
                "area": "efficient transformers",
            }
        ]

    @pytest.mark.asyncio
    async def test_generate_ideas_from_papers(self, agent: IdeaGenerationAgent, sample_gaps):
        ideas = await agent.generate_ideas(sample_gaps[0])
        assert len(ideas) >= 2
        assert ideas[0]["title"].startswith("Investigating")
        assert ideas[0]["gap_addressed"] == "gap1"

    @pytest.mark.asyncio
    async def test_generate_ideas_long_description(self, agent: IdeaGenerationAgent):
        gap = {
            "id": "gap2",
            "description": "A very long research gap description that exceeds the eighty character threshold to trigger the third idea variant",
            "area": "long gap",
        }
        ideas = await agent.generate_ideas(gap)
        assert len(ideas) == 3

    @pytest.mark.asyncio
    async def test_identify_opportunities(self, agent: IdeaGenerationAgent):
        ideas = [
            {"title": "Idea 1", "overlap_score": 0.2},
            {"title": "Idea 2", "overlap_score": 0.8},
        ]
        opportunities = await agent.generate_opportunities(ideas)
        assert len(opportunities) == 2
        assert opportunities[0]["feasibility"] > opportunities[1]["feasibility"]

    @pytest.mark.asyncio
    async def test_detect_novelty_low_overlap(self, agent: IdeaGenerationAgent):
        idea = {"title": "New Quantum Computing Method", "description": "A novel approach to quantum error correction"}
        papers = [{"id": "p1", "title": "Classical Machine Learning", "abstract": "supervised learning methods"}]
        score = await agent.detect_novelty(idea, papers)
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_detect_novelty_high_overlap(self, agent: IdeaGenerationAgent):
        idea = {"title": "Transformer Efficiency", "description": "Improving transformer efficiency for NLP"}
        papers = [{"id": "p1", "title": "Transformer Efficiency", "abstract": "Improving transformer efficiency for NLP tasks"}]
        score = await agent.detect_novelty(idea, papers)
        assert score > 0

    @pytest.mark.asyncio
    async def test_prioritize_ideas(self, agent: IdeaGenerationAgent):
        ideas = [
            {"title": "A", "feasibility": 0.9, "novelty_score": 0.8, "resource_requirements": "low", "overlap_score": 0.1},
            {"title": "B", "feasibility": 0.3, "novelty_score": 0.2, "resource_requirements": "high", "overlap_score": 0.9},
        ]
        recs = await agent.generate_recommendations(ideas)
        assert recs[0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_validate_output_valid(self, agent: IdeaGenerationAgent):
        output = AgentOutput(
            agent_id="idea_gen",
            workflow_id="w1",
            output={
                "ideas": [
                    {
                        "title": "I1",
                        "description": "D1",
                        "gap_addressed": "g1",
                        "overlap_score": 0.0,
                        "overlapping_papers": [],
                        "experiment_plan": "Plan",
                        "feasibility": 0.5,
                        "novelty_score": 0.5,
                        "resource_requirements": "medium",
                    }
                ],
                "recommendations": [{"idea_id": "I1", "priority": "medium", "rationale": "Ok"}],
                "synthesis": "text",
            },
        )
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_output_missing_ideas(self, agent: IdeaGenerationAgent):
        output = AgentOutput(
            agent_id="idea_gen",
            workflow_id="w1",
            output={"recommendations": [], "synthesis": ""},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_validate_output_missing_recommendations(self, agent: IdeaGenerationAgent):
        output = AgentOutput(
            agent_id="idea_gen",
            workflow_id="w1",
            output={
                "ideas": [
                    {
                        "title": "I1",
                        "description": "D1",
                        "gap_addressed": "g1",
                        "overlap_score": 0.0,
                        "overlapping_papers": [],
                        "experiment_plan": "Plan",
                        "feasibility": 0.5,
                        "novelty_score": 0.5,
                        "resource_requirements": "medium",
                    }
                ],
                "synthesis": "text",
            },
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_execute_full_workflow(self, agent: IdeaGenerationAgent, sample_gaps):
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={
                "analysis_report": {
                    "research_gaps": sample_gaps,
                    "papers": [{"id": "p1", "title": "Existing Work", "abstract": "text"}],
                }
            },
        )
        output = await agent.execute(context)
        assert len(output.output["ideas"]) >= 1
        assert "recommendations" in output.output
        assert "synthesis" in output.output


# ===========================================================================
# WritingAgent Tests
# ===========================================================================


class TestWritingAgent:
    @pytest.fixture
    def agent(self) -> WritingAgent:
        return WritingAgent()

    @pytest.mark.asyncio
    async def test_generate_section_produces_content(self, agent: WritingAgent):
        section = await agent.generate_section(
            "Introduction",
            {"analysis_report": {"title": "NLP"}, "idea_proposal": {"synthesis": "New directions"}, "template": {}},
        )
        assert section["heading"] == "Introduction"
        assert len(section["content"]) > 0

    @pytest.mark.asyncio
    async def test_generate_section_unknown_name(self, agent: WritingAgent):
        section = await agent.generate_section(
            "Custom Section",
            {"analysis_report": {}, "idea_proposal": {}, "template": {}},
        )
        assert section["heading"] == "Custom Section"
        assert "Content to be developed" in section["content"]

    @pytest.mark.asyncio
    async def test_generate_draft_assembles_sections(self, agent: WritingAgent):
        context = AgentContext(
            workflow_id="w1", step_id="s1", trace_id="t1",
            input={
                "analysis_report": {"title": "AI Safety"},
                "idea_proposal": {"synthesis": "New safety protocols", "ideas": []},
                "template": {"name": "default"},
            },
        )
        output = await agent.execute(context)
        sections = output.output["sections"]
        assert len(sections) == 7
        headings = [s["heading"] for s in sections]
        assert "Title/Abstract" in headings
        assert "Discussion" in headings

    @pytest.mark.asyncio
    async def test_insert_citations(self, agent: WritingAgent):
        section = {"heading": "Introduction", "content": "The introduction covers related work.", "citations": []}
        citations: list[dict] = []
        source_papers = [
            {"doi": "10.1234/survey", "title": "A Survey of Related Work", "abstract": "overview of the field"},
        ]
        result = await agent.insert_citations(section, citations, source_papers)
        assert len(citations) > 0
        assert "@" in result["content"]

    @pytest.mark.asyncio
    async def test_refine_draft_edits(self, agent: WritingAgent):
        sections = [
            {"heading": "Intro", "content": "Hello world", "citations": []},
            {"heading": "Method", "content": "  Double  spaces  ", "citations": []},
        ]
        refined = await agent.refine_draft(sections)
        assert "  " not in refined[1]["content"]
        assert refined[0]["content"].endswith(".")

    @pytest.mark.asyncio
    async def test_validate_output_valid(self, agent: WritingAgent):
        output = AgentOutput(
            agent_id="writer",
            workflow_id="w1",
            output={
                "sections": [{"heading": "Intro", "content": "Text", "citations": ["cit_1"]}],
                "citations": [{"id": "cit_1", "doi": "10.1000/test", "text": "Ref", "context": "Intro"}],
                "metadata": {"template_used": "default", "word_count": 1, "section_count": 1},
            },
        )
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_output_invalid_no_sections(self, agent: WritingAgent):
        output = AgentOutput(
            agent_id="writer", workflow_id="w1",
            output={"citations": [], "metadata": {"template_used": "default", "word_count": 0, "section_count": 0}},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_validate_output_missing_metadata(self, agent: WritingAgent):
        output = AgentOutput(
            agent_id="writer", workflow_id="w1",
            output={"sections": [], "citations": [], "metadata": {"template_used": "default"}},
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_build_section_content_all_templates(self, agent: WritingAgent):
        for name in ["Title/Abstract", "Introduction", "Related Work", "Method", "Experiment Design", "Expected Results", "Discussion"]:
            content = agent._build_section_content(name, {"title": "Test"}, {"synthesis": "Synth"})
            assert len(content) > 0


# ===========================================================================
# ReviewAgent Tests
# ===========================================================================


class TestReviewAgent:
    @pytest.fixture
    def agent(self) -> ReviewAgent:
        return ReviewAgent()

    @pytest.fixture
    def sample_draft(self) -> dict:
        return {
            "sections": [
                {"heading": "Introduction", "content": "This is the introduction. It covers related work @cit_1."},
                {"heading": "Method", "content": "We propose a new method."},
            ],
            "citations": [
                {"id": "cit_1", "doi": "10.1000/test", "text": "Reference text", "context": "Introduction"},
            ],
        }

    @pytest.mark.asyncio
    async def test_evaluate_quality_scores_output(self, agent: ReviewAgent, sample_draft):
        quality = await agent.evaluate_quality(sample_draft)
        scores = quality["scores"]
        for key in ("structure", "citations", "validity", "clarity", "completeness"):
            assert key in scores

    @pytest.mark.asyncio
    async def test_verify_citations_checks_references(self, agent: ReviewAgent):
        draft = {
            "sections": [],
            "citations": [
                {"id": "c1", "doi": "", "text": "Some text"},
                {"id": "c2", "doi": "10.1000/valid", "text": ""},
            ],
        }
        issues = await agent.verify_citations(draft)
        assert len(issues) == 2

    @pytest.mark.asyncio
    async def test_verify_citations_no_issues(self, agent: ReviewAgent):
        draft = {
            "sections": [],
            "citations": [{"id": "c1", "doi": "10.1000/valid", "text": "Full text"}],
        }
        issues = await agent.verify_citations(draft)
        assert issues == []

    @pytest.mark.asyncio
    async def test_check_completeness(self, agent: ReviewAgent):
        draft = {
            "sections": [
                {"heading": "Introduction", "content": "Text."},
                {"heading": "Method", "content": "Text."},
            ],
            "citations": [],
        }
        issues = await agent.check_completeness(draft)
        # Missing: title/abstract, related work, experiment design, expected results, discussion
        assert len(issues) >= 1

    @pytest.mark.asyncio
    async def test_check_completeness_all_present(self, agent: ReviewAgent):
        draft = {
            "sections": [
                {"heading": "Title/Abstract", "content": "Text."},
                {"heading": "Introduction", "content": "Text."},
                {"heading": "Related Work", "content": "Text."},
                {"heading": "Method", "content": "Text."},
                {"heading": "Experiment Design", "content": "Text."},
                {"heading": "Expected Results", "content": "Text."},
                {"heading": "Discussion", "content": "Text."},
            ],
            "citations": [],
        }
        issues = await agent.check_completeness(draft)
        assert issues == []

    @pytest.mark.asyncio
    async def test_assess_readability(self, agent: ReviewAgent, sample_draft):
        clarity = agent._score_clarity(sample_draft["sections"])
        assert 1 <= clarity <= 5

    @pytest.mark.asyncio
    async def test_score_structure(self, agent: ReviewAgent, sample_draft):
        score = agent._score_structure(sample_draft["sections"])
        assert 1 <= score <= 5

    @pytest.mark.asyncio
    async def test_extract_claims(self, agent: ReviewAgent, sample_draft):
        claims = agent._extract_claims(sample_draft["sections"])
        assert len(claims) >= 1

    @pytest.mark.asyncio
    async def test_validate_output_valid(self, agent: ReviewAgent):
        output = AgentOutput(
            agent_id="reviewer",
            workflow_id="w1",
            output={
                "scores": {"structure": 4, "citations": 3, "validity": 4, "clarity": 5, "completeness": 3},
                "citation_issues": [],
                "groundedness_issues": [],
                "revision_requests": [],
                "summary": "Review PASSED | Average score: 3.8/5",
                "passed": True,
            },
        )
        assert await agent.validate_output(output) is True

    @pytest.mark.asyncio
    async def test_validate_output_invalid_score_range(self, agent: ReviewAgent):
        output = AgentOutput(
            agent_id="reviewer",
            workflow_id="w1",
            output={
                "scores": {"structure": 6, "citations": 3, "validity": 4, "clarity": 5, "completeness": 3},
                "citation_issues": [],
                "groundedness_issues": [],
                "revision_requests": [],
                "summary": "",
                "passed": True,
            },
        )
        assert await agent.validate_output(output) is False

    @pytest.mark.asyncio
    async def test_build_summary(self, agent: ReviewAgent):
        summary = agent._build_summary(
            {"structure": 4, "citations": 3, "validity": 4, "clarity": 5, "completeness": 3},
            [], [],
        )
        assert "PASSED" in summary or "NEEDS REVISION" in summary


# ===========================================================================
# SupervisorAgent Tests
# ===========================================================================


class TestSupervisorAgent:
    @pytest.fixture
    def agent(self, mock_registry) -> SupervisorAgent:
        return SupervisorAgent(agent_registry=mock_registry)

    @pytest.mark.asyncio
    async def test_execute_runs_full_workflow(self, agent: SupervisorAgent, mock_registry, agent_context):
        mock_planner = AsyncMock()
        mock_planner.execute = AsyncMock(
            return_value=AgentOutput(
                agent_id="planner",
                workflow_id="wf-1",
                output={
                    "plan": ExecutionPlan(
                        steps=[
                            AgentStep(agent_id="research", input={}, priority=1),
                            AgentStep(agent_id="analysis", input={}, priority=2),
                            AgentStep(agent_id="idea_gen", input={}, priority=3),
                            AgentStep(agent_id="writing", input={}, priority=4),
                            AgentStep(agent_id="review", input={}, priority=5),
                        ],
                    ),
                    "decomposition": {},
                },
            )
        )
        mock_phase_agent = AsyncMock()
        mock_phase_agent.execute = AsyncMock(
            return_value=AgentOutput(agent_id="phase", workflow_id="wf-1", output={})
        )
        side_effects = [mock_planner] + [mock_phase_agent] * 5
        mock_registry.get.side_effect = side_effects

        with patch("uuid.uuid4", return_value="cp-1"):
            result = await agent.execute(agent_context)
        assert result.agent_id == "supervisor"
        wf_result = result.output["workflow_result"]
        assert wf_result["steps_completed"] == agent.PHASES
        assert wf_result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_execute_with_real_stream_event_dispatcher_does_not_raise(
        self, mock_registry, agent_context,
    ):
        # Regression test: get_research_service() wires a real StreamEventDispatcher
        # into SupervisorAgent (app/api/dependencies.py). handle_checkpoint calls
        # event_dispatcher.dispatch_checkpoint_created(...) for every checkpoint
        # phase (Research/Analysis/Idea Gen/Writing) -- this must not raise
        # AttributeError against the real adapter's interface.
        from app.ai.evaluation.engine import EvaluationEngine
        from app.streaming.dispatcher_adapter import StreamEventDispatcher
        from app.streaming.manager import EventStreamManager

        event_manager = EventStreamManager()
        agent = SupervisorAgent(
            agent_registry=mock_registry,
            event_dispatcher=StreamEventDispatcher(event_manager),
            evaluation_engine=EvaluationEngine(),
        )

        mock_planner = AsyncMock()
        mock_planner.execute = AsyncMock(
            return_value=AgentOutput(
                agent_id="planner",
                workflow_id="wf-1",
                output={
                    "plan": ExecutionPlan(
                        steps=[
                            AgentStep(agent_id="research", input={}, priority=1),
                            AgentStep(agent_id="analysis", input={}, priority=2),
                            AgentStep(agent_id="idea_gen", input={}, priority=3),
                            AgentStep(agent_id="writing", input={}, priority=4),
                            AgentStep(agent_id="review", input={}, priority=5),
                        ],
                    ),
                    "decomposition": {},
                },
            )
        )
        mock_phase_agent = AsyncMock()
        mock_phase_agent.execute = AsyncMock(
            return_value=AgentOutput(agent_id="phase", workflow_id="wf-1", output={})
        )
        mock_registry.get.side_effect = [mock_planner] + [mock_phase_agent] * 5

        result = await agent.execute(agent_context)

        assert result.agent_id == "supervisor"
        events = await event_manager.get_event_history("wf-1")
        event_types = {e.type.value for e in events}
        assert "checkpoint.created" in event_types
        assert "workflow.started" in event_types
        assert "agent.started" in event_types
        assert "agent.completed" in event_types

    @pytest.mark.asyncio
    async def test_execute_step_delegates_to_agent(self, agent: SupervisorAgent, mock_registry):
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(
            return_value=AgentOutput(agent_id="writer", workflow_id="wf-1", output={"draft": "text"})
        )
        mock_registry.get.return_value = mock_agent
        step = AgentStep(agent_id="writer", input={"topic": "AI"}, max_retries=0)
        with patch.object(agent, "_state_manager", None):
            output = await agent.execute_step(step)
        assert output.agent_id == "writer"

    @pytest.mark.asyncio
    async def test_execute_step_retry_on_validation_failure(self, agent: SupervisorAgent, mock_registry):
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(
            return_value=AgentOutput(agent_id="writer", workflow_id="wf-1", output={})
        )
        mock_registry.get.return_value = mock_agent
        agent.validate_output = AsyncMock(return_value=False)  # type: ignore[assignment]
        step = AgentStep(agent_id="writer", input={}, max_retries=1)
        with (
            patch("asyncio.sleep", AsyncMock()),
            pytest.raises(RetryableError, match="Output validation failed"),
        ):
            await agent.execute_step(step)

    @pytest.mark.asyncio
    async def test_execute_step_raises_aara_error(self, agent: SupervisorAgent, mock_registry):
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(
            side_effect=AARAError(ErrorCode(code="TEST_ERR", http_status=500, message="test error"))
        )
        mock_registry.get.return_value = mock_agent
        step = AgentStep(agent_id="writer", input={}, max_retries=0)
        with pytest.raises(AARAError):
            await agent.execute_step(step)

    @pytest.mark.asyncio
    async def test_handle_checkpoint_creates_checkpoint(self, agent: SupervisorAgent):
        output = AgentOutput(agent_id="writer", workflow_id="wf-1", summary="Section written")
        with patch("uuid.uuid4", return_value="cp-abc"):
            cpid = await agent.handle_checkpoint("Writing", output)
        assert cpid == "cp-abc"
        assert agent._checkpoint_ids["Writing"] == "cp-abc"

    @pytest.mark.asyncio
    async def test_orchestrate_phase(self, agent: SupervisorAgent, mock_registry, agent_context):
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(
            return_value=AgentOutput(agent_id="phase_agent", workflow_id="wf-1", output={})
        )
        mock_registry.get.return_value = mock_agent
        output = await agent.run_phase("Research", {"query": "test"})
        assert output.agent_id == "phase_agent"

    @pytest.mark.asyncio
    async def test_handle_error_wraps_errors(self, agent: SupervisorAgent, agent_context):
        agent._start_time = 1000.0
        error = ValueError("Something went wrong")
        result = await agent.handle_error(error, agent_context)
        assert "error" in result.output
        assert "Something went wrong" in result.output["error"]

    @pytest.mark.asyncio
    async def test_validate_output_with_workflow_result(self, agent: SupervisorAgent):
        valid_output = AgentOutput(
            agent_id="supervisor",
            workflow_id="w1",
            output={
                "workflow_result": WorkflowResult(
                    workflow_id="w1", status="completed", query="test"
                ).model_dump()
            },
        )
        assert await agent.validate_output(valid_output) is True

    @pytest.mark.asyncio
    async def test_validate_output_invalid_workflow_result(self, agent: SupervisorAgent):
        invalid_output = AgentOutput(
            agent_id="supervisor",
            workflow_id="w1",
            output={"workflow_result": {"workflow_id": 123}},  # wrong type for workflow_id
        )
        assert await agent.validate_output(invalid_output) is False

    @pytest.mark.asyncio
    async def test_properties(self, agent: SupervisorAgent):
        agent._workflow_id = "wf-1"
        agent._trace_id = "tr-1"
        agent._state.intermediate_outputs = {"key": "val"}
        agent._state.current_phase = AgentPhase.REASONING
        assert agent.workflow_id == "wf-1"
        assert agent.trace_id == "tr-1"
        assert agent.state == {"key": "val"}
        assert agent.current_phase == "reasoning"

    @pytest.mark.asyncio
    async def test_aggregate_results(self, agent: SupervisorAgent):
        agent._phase_outputs["Research"] = AgentOutput(
            agent_id="r", workflow_id="w1",
            output={"papers": [{"id": "p1"}]},
        )
        agent._phase_outputs["Analysis"] = AgentOutput(
            agent_id="a", workflow_id="w1",
            output={"analysis": {"themes": []}},
        )
        result = await agent.aggregate_results()
        assert result.papers == [{"id": "p1"}]
        assert result.analysis == {"themes": []}

    @pytest.mark.asyncio
    async def test_execute_non_checkpoint_phases(self, agent: SupervisorAgent, agent_context):
        mock_planner = AsyncMock()
        mock_planner.execute = AsyncMock(
            return_value=AgentOutput(
                agent_id="planner",
                workflow_id="wf-1",
                output={"plan": ExecutionPlan(steps=[]), "decomposition": {}},
            )
        )
        mock_phase = AsyncMock()
        mock_phase.execute = AsyncMock(
            return_value=AgentOutput(agent_id="ph", workflow_id="wf-1", output={})
        )
        mock_registry = MagicMock()
        mock_registry.get.side_effect = [mock_planner] + [mock_phase] * 5
        agent._agent_registry = mock_registry

        with patch("uuid.uuid4", return_value="cp-x"):
            result = await agent.execute(agent_context)
        wf = result.output["workflow_result"]
        assert len(wf["checkpoint_decisions"]) == 4  # All phases except Review
