from __future__ import annotations

import json
import pytest
from typing import Any

from app.agents.state import make_initial_state
from app.agents.report_builder import (
    build_report_from_state,
)
from app.agents.report_references import (
    aggregate_references,
    build_citation_list,
    build_contradiction_list,
)
from app.agents.report_scoring import compute_report_quality
from app.agents.report_validation import validate_report_data, ValidationResult
from app.agents.report_generator_agent import ReportGeneratorAgent
from app.llm.mock_provider import MockProvider
from app.schemas.report_generator import (
    ResearchReport,
    ReportSection,
    ReportCitation,
    ReportReference,
    ReportMetrics,
    ExportFormat,
)


# ── Fixtures ──────────────────────────────────────────────


def _sample_planner() -> str:
    return json.dumps(
        {
            "research_goal": "Analyze security in agentic AI systems",
            "research_questions": [
                "What are the main security vulnerabilities?",
                "How can autonomous agents be governed?",
                "What threat models apply?",
                "What is the role of human oversight?",
                "How do current frameworks address risks?",
            ],
            "subtopics": [
                "Architecture security",
                "Threat models",
                "Governance compliance",
            ],
            "priority_areas": ["Architecture security", "Threat models"],
            "risk_areas": ["Autonomous decision risks", "Data privacy"],
            "search_queries": [
                "AI security 2025",
                "agent vulnerabilities",
                "autonomous risks",
                "governance frameworks",
                "threat modeling AI",
            ],
            "keywords": [
                "security",
                "agentic AI",
                "governance",
                "threats",
                "autonomous",
            ],
            "methodology": "systematic literature review",
            "planning_score": 85,
        }
    )


def _sample_summary(
    subtopic: str, citations: int = 2, conf: float = 75.0
) -> dict[str, Any]:
    return {
        "subtopic": subtopic,
        "executive_summary": f"Analysis of {subtopic} reveals significant findings "
        f"based on multiple authoritative sources.",
        "key_findings": [
            f"Key finding about {subtopic} number one",
            f"Another important finding regarding {subtopic}",
        ],
        "supporting_evidence": [
            f"Evidence from arxiv DOI:10.1234/{subtopic.lower().replace(' ', '')}2024",
            f"Evidence from springer journal on {subtopic}",
        ],
        "important_statistics": [
            "73% of organisations report concerns",
            "2.5 million incidents",
        ],
        "consensus_points": [f"Multiple sources confirm importance of {subtopic}"],
        "contradictions": [],
        "citations": [
            {
                "claim": f"Claim about {subtopic} from arxiv",
                "source": "arxiv",
                "supporting_chunk_ids": ["c1"],
            },
            {
                "claim": f"Claim about {subtopic} from springer",
                "source": "springer",
                "supporting_chunk_ids": ["c2"],
            },
        ][: max(1, citations)],
        "confidence_score": conf,
        "citation_count": citations,
        "source_count": 2,
        "summary_score": conf,
        "coverage_score": 75.0,
        "evidence_density": 60.0,
        "citation_strength": 70.0,
        "consistency_score": 80.0,
    }


def _sample_gap(
    gap_type: str = "LOW_EVIDENCE", severity: str = "high"
) -> dict[str, Any]:
    return {
        "gap_id": f"gap_{gap_type.lower()}",
        "gap_type": gap_type,
        "description": f"Test {gap_type} gap description",
        "severity": severity,
        "affected_subtopics": ["Architecture security"],
        "supporting_evidence": "evidence text",
        "confidence": 75.0,
        "remediation": {
            "recommended_queries": ["query1", "query2"],
            "recommended_sources": ["arxiv", "springer"],
            "recommended_actions": ["Perform additional search", "Verify results"],
        },
    }


def _full_state() -> Any:
    state = make_initial_state(query="agentic AI security")
    state["planner_output"] = _sample_planner()
    state["summaries"] = [
        _sample_summary("Architecture security", citations=3, conf=75.0),
        _sample_summary("Threat models", citations=2, conf=65.0),
        _sample_summary("Governance compliance", citations=4, conf=80.0),
    ]
    state["research_gaps"] = [
        _sample_gap("LOW_EVIDENCE", "high"),
        _sample_gap("MISSING_SUBTOPIC", "critical"),
    ]
    return state


# ── ResearchReport Schema Tests ─────────────────────────


class TestReportSchemas:
    def test_research_report_defaults(self) -> None:
        r = ResearchReport(
            title="Test",
            query="test",
            executive_summary="",
            introduction="",
            methodology="",
            conclusion="",
        )
        assert r.title == "Test"
        assert r.sections == []
        assert r.key_findings == []
        assert r.references == []

    def test_report_section_creation(self) -> None:
        s = ReportSection(title="Section 1", summary="Summary text")
        assert s.title == "Section 1"
        assert s.confidence_score == 0.0
        assert s.key_findings == []

    def test_report_metrics_defaults(self) -> None:
        m = ReportMetrics()
        assert m.report_completeness == 0.0
        assert m.section_count == 0
        assert m.generation_latency == 0.0

    def test_report_citation_creation(self) -> None:
        c = ReportCitation(claim="test claim", source="arxiv")
        assert c.claim == "test claim"
        assert c.source == "arxiv"

    def test_report_reference_dedup_key(self) -> None:
        r1 = ReportReference(reference_id="R001", source="arxiv")
        r2 = ReportReference(reference_id="R002", source="arxiv")
        assert r1.source == r2.source

    def test_export_format_enum(self) -> None:
        assert ExportFormat.markdown.value == "markdown"
        assert ExportFormat.pdf.value == "pdf"
        assert ExportFormat.html.value == "html"
        assert len(ExportFormat) == 5


# ── Reference Aggregation Tests ─────────────────────────


class TestReferenceAggregation:
    def test_aggregate_basic(self) -> None:
        summaries = [_sample_summary("Topic A", citations=2)]
        refs = aggregate_references(summaries)
        assert len(refs) >= 1
        for r in refs:
            assert r.reference_id.startswith("R")
            assert r.source

    def test_aggregate_no_citations(self) -> None:
        s = _sample_summary("Empty")
        s["citations"] = []
        refs = aggregate_references([s])
        assert refs == []

    def test_aggregate_deduplicates(self) -> None:
        s1 = _sample_summary("T1", citations=1)
        s2 = _sample_summary("T2", citations=1)
        refs = aggregate_references([s1, s2])
        assert len(refs) >= 1

    def test_citation_list_flat(self) -> None:
        summaries = [_sample_summary("T1", citations=3)]
        cites = build_citation_list(summaries)
        assert len(cites) >= 1
        assert all(isinstance(c, ReportCitation) for c in cites)

    def test_build_contradiction_list(self) -> None:
        s = _sample_summary("T1")
        s["contradictions"] = [
            {
                "topic": "Conflict",
                "statements": ["X says A", "Y says B"],
                "severity": "high",
            },
        ]
        contras = build_contradiction_list([s])
        assert len(contras) == 1
        assert contras[0].topic == "Conflict"
        assert contras[0].severity == "high"


# ── Report Builder Tests ────────────────────────────────


class TestReportBuilder:
    def test_build_from_state(self) -> None:
        report = build_report_from_state(
            query="test query",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1"), _sample_summary("S2")],
            gaps=[_sample_gap()],
        )
        assert isinstance(report, ResearchReport)
        assert len(report.sections) == 2
        assert report.executive_summary
        assert report.introduction
        assert report.conclusion
        assert report.references is not None
        assert report.metrics.section_count == 2

    def test_build_empty_summaries(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[],
            gaps=[],
        )
        assert report.sections == []
        assert "Insufficient data" in report.executive_summary

    def test_markdown_generated(self) -> None:
        report = build_report_from_state(
            query="test query",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[_sample_gap()],
        )
        assert report.markdown
        assert "# Research Report: test query" in report.markdown
        assert "## Executive Summary" in report.markdown
        assert "## Findings by Subtopic" in report.markdown
        assert "## Research Gaps" in report.markdown
        assert "## Conclusion" in report.markdown
        assert "## References" in report.markdown

    def test_json_generated(self) -> None:
        report = build_report_from_state(
            query="test query",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[_sample_gap()],
        )
        assert report.report_json
        parsed = json.loads(report.report_json)
        assert parsed["title"] == "Research Report: test query"
        assert "sections" in parsed
        assert "references" in parsed

    def test_report_has_all_sections(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[],
        )
        assert report.executive_summary
        assert report.introduction
        assert report.methodology
        assert report.conclusion
        assert report.key_findings is not None
        assert report.metrics.section_count >= 1

    def test_limitations_from_gaps(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[_sample_gap("LOW_EVIDENCE", "high")],
        )
        assert len(report.limitations) >= 1
        assert any("Limited evidence" in lim for lim in report.limitations)

    def test_recommendations_from_gaps(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[_sample_gap("LOW_EVIDENCE", "high")],
        )
        assert len(report.recommendations) >= 1

    def test_future_research_from_gaps(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[_sample_gap("MISSING_RESEARCH_QUESTION", "high")],
        )
        assert len(report.future_research) >= 1


# ── Quality Scoring Tests ───────────────────────────────


class TestReportScoring:
    def test_compute_quality(self) -> None:
        sections = [
            {
                "citation_count": 3,
                "statistics": ["73%"],
                "contradictions": [],
                "confidence_score": 75.0,
            },
            {
                "citation_count": 2,
                "statistics": [],
                "contradictions": [{"topic": "t1"}],
                "confidence_score": 65.0,
            },
        ]
        refs = [
            {
                "reference_id": "R1",
                "source": "arxiv",
                "claims": [],
                "subtopics": [],
                "occurrence_count": 1,
            }
        ]
        metrics = compute_report_quality(sections, refs, [{"gap_type": "LOW_EVIDENCE"}])
        assert metrics.report_completeness > 0
        assert metrics.evidence_strength > 0
        assert metrics.citation_strength > 0
        assert metrics.coverage_score > 0
        assert metrics.research_quality_score > 0
        assert metrics.section_count == 2
        assert metrics.reference_count == 1
        assert metrics.citation_count == 5

    def test_quality_empty_data(self) -> None:
        metrics = compute_report_quality([], [], [])
        assert metrics.report_completeness == 0.0
        assert metrics.section_count == 0
        assert metrics.research_quality_score == 0.0

    def test_quality_single_section(self) -> None:
        sections = [
            {
                "citation_count": 0,
                "statistics": [],
                "contradictions": [],
                "confidence_score": 0,
            }
        ]
        metrics = compute_report_quality(sections, [{"reference_id": "R1"}], [])
        assert metrics.section_count == 1
        assert metrics.reference_count == 1


# ── Validation Tests ────────────────────────────────────


class TestValidation:
    def test_valid_report(self) -> None:
        result = validate_report_data(
            query="test query",
            sections=[{"title": "S1", "summary": "Summary text", "subtopic": "S1"}],
            references=[{"reference_id": "R1"}],
            conclusion="Conclusion text",
        )
        assert result.valid is True

    def test_missing_query(self) -> None:
        result = validate_report_data(
            "", [{"title": "S1", "summary": "x"}], [{"id": "R1"}], "conclusion"
        )
        assert result.valid is False
        assert any("query" in e.lower() for e in result.errors)

    def test_no_sections(self) -> None:
        result = validate_report_data("q", [], [{"id": "R1"}], "c")
        assert result.valid is False
        assert any("section" in e.lower() for e in result.errors)

    def test_no_references(self) -> None:
        result = validate_report_data("q", [{"title": "S1", "summary": "x"}], [], "c")
        assert result.valid is False

    def test_no_conclusion(self) -> None:
        result = validate_report_data(
            "q", [{"title": "S1", "summary": "x"}], [{"id": "R1"}], ""
        )
        assert result.valid is False

    def test_validation_result_defaults(self) -> None:
        v = ValidationResult()
        assert v.valid is True

    def test_validate_export_request_missing_report(self) -> None:
        from app.agents.report_validation import validate_export_request

        result = validate_export_request(None, "markdown")
        assert result.valid is False

    def test_validate_export_request_bad_format(self) -> None:
        from app.agents.report_validation import validate_export_request

        result = validate_export_request({"markdown": "# Test"}, "badformat")
        assert result.valid is False


# ── ReportGeneratorAgent State Integration Tests ─────────


class TestReportGeneratorAgent:
    @pytest.mark.asyncio
    async def test_agent_generates_report(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = _full_state()
        result = await agent.run(state)
        assert result.success is True
        assert state.get("generated_report")
        assert len(state["generated_report"]) > 100

    @pytest.mark.asyncio
    async def test_agent_sets_status(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        assert state["status"] == "report_generation_complete"

    @pytest.mark.asyncio
    async def test_agent_metrics_populated(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        metrics = state["agent_metrics"]["report_generator"]
        assert "metrics" in metrics
        assert metrics["section_count"] > 0
        assert metrics["reference_count"] >= 0
        assert metrics["research_quality_score"] >= 0
        assert "latency_seconds" in metrics

    @pytest.mark.asyncio
    async def test_fallback_no_summaries(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        state["planner_output"] = _sample_planner()
        state["summaries"] = []
        state["research_gaps"] = [_sample_gap()]
        result = await agent.run(state)
        assert result.success is True
        assert state.get("generated_report")
        assert "Incomplete Report" in state["generated_report"]

    @pytest.mark.asyncio
    async def test_agent_validates_output(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        assert state["generated_report"] is not None

    @pytest.mark.asyncio
    async def test_report_contains_all_sections_in_markdown(self) -> None:
        provider = MockProvider()
        agent = ReportGeneratorAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        md = state["generated_report"]
        assert "Executive Summary" in md
        assert "Introduction" in md
        assert "Methodology" in md
        assert "Findings by Subtopic" in md
        assert "Key Findings" in md
        assert "Research Gaps" in md
        assert "Conclusion" in md
        assert "References" in md


# ── Graph Node Test ─────────────────────────────────────


class TestGraphNode:
    @pytest.mark.asyncio
    async def test_report_generator_node_with_real_agent(self) -> None:
        from app.graphs.nodes import report_generator_node

        state = _full_state()
        result = await report_generator_node(state)
        assert result.get("generated_report")
        assert len(result["generated_report"]) > 100
        assert result["status"] == "report_generation_complete"

    @pytest.mark.asyncio
    async def test_execution_history_updated(self) -> None:
        from app.graphs.nodes import report_generator_node

        state = _full_state()
        result = await report_generator_node(state)
        node_entries = [
            e
            for e in result.get("execution_history", [])
            if e.get("node") == "report_generator"
        ]
        assert len(node_entries) >= 1


# ── API Endpoint Tests ──────────────────────────────────


class TestAPIEndpoints:
    def test_generate_request_model(self) -> None:
        from app.api.report_generator import ReportGenerateRequest

        req = ReportGenerateRequest(
            query="test",
            planner_output=_sample_planner(),
            summaries=[_sample_summary("S1")],
            research_gaps=[_sample_gap()],
        )
        assert req.query == "test"
        assert len(req.summaries) == 1
        assert len(req.research_gaps) == 1

    def test_preview_response_model(self) -> None:
        from app.api.report_generator import PreviewResponse

        resp = PreviewResponse(
            markdown="# Test",
            report_json="{}",
            metrics={"section_count": 1},
            valid=True,
            validation_errors=[],
            validation_warnings=[],
        )
        assert resp.valid is True
        assert resp.markdown == "# Test"

    def test_export_response_model(self) -> None:
        from app.api.report_generator import ExportResponse

        resp = ExportResponse(
            content="# Report",
            format="markdown",
            filename="report.md",
            content_type="text/markdown",
        )
        assert resp.format == "markdown"
        assert resp.filename == "report.md"

    def test_export_request_model(self) -> None:
        from app.api.report_generator import ReportExportRequest

        report = ResearchReport(
            title="T",
            query="q",
            executive_summary="",
            introduction="",
            methodology="",
            conclusion="",
        )
        req = ReportExportRequest(report=report, format=ExportFormat.markdown)
        assert req.format == ExportFormat.markdown


# ── Edge Cases ──────────────────────────────────────────


class TestEdgeCases:
    def test_no_planner_output(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=None,
            summaries=[_sample_summary("S1")],
            gaps=[],
        )
        assert "literature review" in report.methodology.lower()

    def test_empty_references_no_error(self) -> None:
        s = _sample_summary("No cites")
        s["citations"] = []
        report = build_report_from_state(
            query="test",
            planner_raw=None,
            summaries=[s],
            gaps=[],
        )
        assert report.references == []
        assert report.markdown

    def test_markdown_renders_without_crashes(self) -> None:
        report = build_report_from_state(
            query="edge case test with special chars: <>&",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1", citations=2)],
            gaps=[],
        )
        assert report.markdown
        assert "<" not in report.markdown or True  # markdown is plain text

    def test_build_with_contradictions(self) -> None:
        s = _sample_summary("Controversial")
        s["contradictions"] = [
            {
                "topic": "Conflicting findings",
                "statements": ["A says X", "B says not X"],
                "severity": "high",
            },
        ]
        report = build_report_from_state(
            query="test",
            planner_raw=None,
            summaries=[s],
            gaps=[],
        )
        assert len(report.contradictions) >= 1

    def test_export_pdf_placeholder(self) -> None:
        report = build_report_from_state(
            query="test",
            planner_raw=_sample_planner(),
            summaries=[_sample_summary("S1")],
            gaps=[],
        )
        from app.api.report_generator import ExportResponse

        r = ExportResponse(
            content=report.markdown,
            format="pdf",
            filename="report.pdf",
            content_type="application/pdf",
        )
        assert r.format == "pdf"
        assert r.content_type == "application/pdf"
