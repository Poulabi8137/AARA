"""Tests for paper authoring agents, schemas, and API."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock


from app.agents.proposal_agent import ProposalAgent
from app.agents.paper_author_agent import PaperAuthorAgent
from app.agents.quality_review_agent import QualityReviewAgent
from app.agents.citation_validator_agent import CitationValidatorAgent
from app.agents.evidence_validator_agent import EvidenceValidatorAgent
from app.agents.state import make_initial_state
from app.schemas.paper import (
    ProposalCreate, PaperGenerateRequest,
    SectionRewriteRequest, BasePaperAnalysisCreate,
)
from app.models.paper import (
    PaperStatus, SectionStatus, PaperOperation,
    EvidenceClass,
)


class TestProposalAgent:
    async def test_arun_with_fallback(self):
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM failed"))
        agent = ProposalAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test gap", project_id="p1", objective="test objective")
        state["selected_gap"] = {"description": "research gap in AI", "id": "gap1"}
        state["domain"] = "Artificial Intelligence"
        state["keywords"] = "machine learning, deep learning"

        result_state = await agent.arun(state)
        proposal = result_state.get("proposal", {})
        assert result_state["status"] == "proposal_complete"
        assert "proposed_title" in proposal
        assert "problem_statement" in proposal
        assert "research_questions" in proposal
        assert "hypothesis" in proposal
        assert "objectives" in proposal
        assert len(proposal["research_questions"]) >= 2

    async def test_arun_with_llm_response(self):
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "proposed_title": "Novel AI Approach",
            "problem_statement": "Key problem in AI",
            "motivation": "Why this matters",
            "research_questions": ["Q1?", "Q2?", "Q3?"],
            "hypothesis": "Our approach will improve accuracy",
            "objectives": ["O1", "O2"],
            "expected_contributions": ["C1", "C2"],
            "proposed_methodology": "Deep learning approach",
            "evaluation_strategy": "Benchmark evaluation",
            "future_scope": "Extension to other domains",
        })
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=mock_response)
        agent = ProposalAgent(llm_provider=mock_llm)
        state = make_initial_state(query="AI safety", project_id="p1")
        state["selected_gap"] = {"description": "AI safety gap", "id": "gap1"}

        result_state = await agent.arun(state)
        proposal = result_state.get("proposal", {})
        assert proposal["proposed_title"] == "Novel AI Approach"
        assert len(proposal["research_questions"]) == 3

    def test_fallback_proposal_structure(self):
        mock_llm = MagicMock()
        agent = ProposalAgent(llm_provider=mock_llm)
        proposal = agent._fallback_proposal("AI safety alignment", "AI")
        required_keys = [
            "proposed_title", "problem_statement", "motivation",
            "research_questions", "hypothesis", "objectives",
            "expected_contributions", "proposed_methodology",
            "evaluation_strategy", "future_scope",
        ]
        for key in required_keys:
            assert key in proposal, f"Missing key: {key}"


class TestPaperAuthorAgent:
    async def test_arun_without_proposal(self):
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM failed"))
        agent = PaperAuthorAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test paper")
        state["proposal"] = {
            "proposed_title": "Test Research Paper",
            "problem_statement": "Test problem",
            "motivation": "Test motivation",
            "research_questions": ["Q1?"],
            "hypothesis": "H1",
            "objectives": ["O1"],
            "expected_contributions": ["C1"],
            "proposed_methodology": "Methodology",
            "evaluation_strategy": "Evaluation",
            "future_scope": "Future work",
            "keywords": ["test"],
        }
        result_state = await agent.arun(state)
        paper = result_state.get("paper_draft", {})
        assert result_state["status"] == "paper_generated"
        assert "title" in paper
        assert "sections" in paper
        assert len(paper["sections"]) > 0

    async def test_arun_empty_proposal(self):
        mock_llm = MagicMock()
        agent = PaperAuthorAgent(llm_provider=mock_llm)
        state = make_initial_state(query="emergency fallback")
        result_state = await agent.arun(state)
        paper = result_state.get("paper_draft", {})
        assert paper["title"].startswith("Research on")

    def test_template_paper_has_all_ieee_sections(self):
        mock_llm = MagicMock()
        agent = PaperAuthorAgent(llm_provider=mock_llm)
        proposal = {
            "proposed_title": "Test",
            "problem_statement": "Problem",
            "motivation": "Why",
            "research_questions": ["Q1?"],
            "hypothesis": "H1",
            "objectives": ["O1"],
            "expected_contributions": ["C1"],
            "proposed_methodology": "Method",
            "evaluation_strategy": "Eval",
            "future_scope": "Future",
            "keywords": ["key"],
        }
        paper = agent._template_paper(proposal)
        assert len(paper["sections"]) == 15
        titles = [s["section_title"] for s in paper["sections"]]
        expected = ["Introduction", "Related Work", "Problem Statement", "Research Gap",
                     "Proposed Solution", "System Architecture", "Methodology", "Algorithm",
                     "Mathematical Model", "Experimental Design", "Expected Results",
                     "Discussion", "Threats to Validity", "Future Work", "Conclusion"]
        assert titles == expected


class TestQualityReviewAgent:
    async def test_review_empty(self):
        mock_llm = MagicMock()
        agent = QualityReviewAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test")
        state = await agent.arun(state)
        review = state.get("quality_review", {})
        assert review.get("composite_score") == 0.0

    async def test_review_with_template(self):
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("LLM failed"))
        agent = QualityReviewAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test")
        state["paper_draft"] = {
            "title": "Test Paper",
            "abstract": "Abstract here",
            "sections": [{"section_number": i, "section_title": f"S{i}", "content": "x"} for i in range(1, 16)],
            "references": [{"citation_key": "[1]", "authors": "A", "title": "T", "year": 2024}],
        }
        state = await agent.arun(state)
        review = state.get("quality_review", {})
        assert review["composite_score"] > 0
        assert "suggestions" in review
        assert "strengths" in review
        assert "weaknesses" in review


class TestCitationValidatorAgent:
    async def test_validate_empty(self):
        mock_llm = MagicMock()
        agent = CitationValidatorAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test")
        state["paper_draft"] = {"references": []}
        state = await agent.arun(state)
        val = state.get("citation_validation", {})
        assert val.get("total", 0) == 0

    async def test_rule_based_validation(self):
        mock_llm = MagicMock()
        agent = CitationValidatorAgent(llm_provider=mock_llm)
        refs = [
            {"citation_key": "[1]", "authors": "Smith, J.", "title": "AI Advances", "year": 2024, "doi": "10.1234/test"},
            {"citation_key": "[2]", "authors": "Placeholder", "title": "Placeholder Title", "year": 2023},
            {"citation_key": "[1]", "authors": "Smith, J.", "title": "AI Advances", "year": 2024, "doi": "10.1234/test"},
        ]
        results = agent._rule_based_validation(refs)
        assert len(results) == 3
        assert results[0]["has_doi"] is True
        assert results[0]["is_duplicate"] is False
        assert results[1]["is_fabricated"] is True
        assert results[2]["is_duplicate"] is True

    def test_ieee_format(self):
        mock_llm = MagicMock()
        agent = CitationValidatorAgent(llm_provider=mock_llm)
        formatted = agent._format_ieee({"authors": "J. Smith", "title": "AI", "journal": "IEEE", "year": 2024})
        assert "J. Smith" in formatted
        assert "AI" in formatted


class TestEvidenceValidatorAgent:
    async def test_validate_empty(self):
        mock_llm = MagicMock()
        agent = EvidenceValidatorAgent(llm_provider=mock_llm)
        state = make_initial_state(query="test")
        state["paper_draft"] = {"sections": []}
        state = await agent.arun(state)
        val = state.get("evidence_validation", {})
        assert val.get("status") == "insufficient_content"

    async def test_heuristic_validation(self):
        mock_llm = MagicMock()
        agent = EvidenceValidatorAgent(llm_provider=mock_llm)
        content = (
            "The method achieves 95% accuracy [1]. "
            "This suggests significant improvement. "
            "Future work would extend to other domains. "
            "This is a plain statement without citations."
        )
        result = agent._heuristic_validation(content)
        assert result["coverage"]["total"] > 0
        classifications = [s["classification"] for s in result["statements"]]
        assert "supported" in classifications
        assert "speculative" in classifications
        assert "needs_citation" in classifications


class TestPaperModels:
    def test_paper_status_enum(self):
        assert PaperStatus.DRAFT.value == "draft"
        assert PaperStatus.GENERATED.value == "generated"
        assert PaperStatus.COMPLETE.value == "complete"
        assert PaperStatus.FAILED.value == "failed"

    def test_section_status_enum(self):
        assert SectionStatus.DRAFT.value == "draft"
        assert SectionStatus.APPROVED.value == "approved"

    def test_evidence_class_enum(self):
        assert EvidenceClass.SUPPORTED.value == "supported"
        assert EvidenceClass.SPECULATIVE.value == "speculative"

    def test_paper_operation_enum(self):
        assert PaperOperation.REWRITE.value == "rewrite"
        assert PaperOperation.EXPAND.value == "expand"


class TestPaperSchemas:
    def test_proposal_create_schema(self):
        data = ProposalCreate(project_id=str(uuid.uuid4()), domain="AI", objective="Test")
        assert data.project_id
        assert data.domain == "AI"

    def test_section_rewrite_request(self):
        req = SectionRewriteRequest(operation="rewrite")
        assert req.operation == "rewrite"

        req2 = SectionRewriteRequest(operation="expand")
        assert req2.operation == "expand"

    def test_paper_generate_request(self):
        req = PaperGenerateRequest(project_id=str(uuid.uuid4()), proposal_id=str(uuid.uuid4()))
        assert req.project_id
        assert req.proposal_id

    def test_base_paper_analysis_create(self):
        data = BasePaperAnalysisCreate(project_id=str(uuid.uuid4()), doi="10.1234/test")
        assert data.doi == "10.1234/test"
        assert data.url is None
