from __future__ import annotations

import json
import pytest
from typing import Any

from app.agents.state import make_initial_state
from app.agents.gap_analysis import (
    detect_all_gaps,
    _parse_planner,
    _detect_missing_subtopics,
    _detect_low_evidence,
    _detect_contradictions,
    _detect_missing_risk_analysis,
    _detect_missing_priority_area,
    _detect_missing_research_question,
    _detect_insufficient_source_diversity,
    _detect_low_confidence_summary,
)
from app.agents.gap_severity import compute_severity, _base_severity
from app.agents.gap_coverage import (
    compute_coverage_metrics,
    build_question_mapping,
    build_priority_mapping,
    build_risk_mapping,
)
from app.agents.gap_remediation import generate_remediation
from app.agents.gap_detection_agent import GapDetectionAgent
from app.llm.mock_provider import MockProvider
from app.schemas.gap_detection import (
    GapType,
    SeverityLevel,
    ResearchGap,
    RemediationSuggestion,
    CoverageMetrics,
)


# ── Fixtures ──────────────────────────────────────────────


def _sample_planner() -> dict[str, Any]:
    return {
        "research_goal": "Analyze security in agentic AI systems",
        "research_questions": [
            "What are the main security vulnerabilities in agentic AI?",
            "How can autonomous agents be governed effectively?",
            "What threat models apply to multi-agent systems?",
            "What is the role of human oversight?",
            "How do current frameworks address these risks?",
        ],
        "subtopics": [
            "Architecture security",
            "Threat models",
            "Governance compliance",
            "Human oversight",
            "Framework evaluation",
        ],
        "priority_areas": [
            "Architecture security",
            "Threat models",
            "Governance compliance",
        ],
        "risk_areas": [
            "Autonomous decision risks",
            "Data privacy",
            "Adversarial attacks",
        ],
        "search_queries": [
            "AI security 2025",
            "agent vulnerabilities",
            "autonomous risks",
            "governance frameworks",
            "threat modeling AI",
        ],
        "planning_score": 85,
        "completeness": 80,
        "coverage": 82,
        "specificity": 75,
    }


def _sample_summary(
    subtopic: str,
    citations: int = 3,
    sources: int = 2,
    conf: float = 70.0,
    contradictions: int = 0,
) -> dict[str, Any]:
    s: dict[str, Any] = {
        "subtopic": subtopic,
        "executive_summary": f"Analysis of {subtopic} reveals significant findings "
        f"with high confidence based on multiple sources.",
        "key_findings": [
            f"Key finding about {subtopic} number one",
            f"Another important finding regarding {subtopic}",
            f"Third critical insight for {subtopic}",
        ],
        "supporting_evidence": [
            f"Evidence from arxiv DOI:10.1234/{subtopic.lower().replace(' ', '')}2024",
            f"Evidence from springer journal on {subtopic}",
        ],
        "important_statistics": ["73%", "2.5 million"],
        "consensus_points": [f"Multiple sources confirm importance of {subtopic}"],
        "contradictions": [],
        "citations": [
            {"claim": f"Claim about {subtopic}", "supporting_chunk_ids": ["c1"]},
        ]
        * max(0, citations),
        "confidence_score": conf,
        "citation_count": citations,
        "source_count": sources,
        "summary_score": conf,
        "coverage_score": 75.0,
        "evidence_density": 60.0,
        "citation_strength": 70.0,
        "consistency_score": 80.0,
    }
    if contradictions > 0:
        s["contradictions"] = [
            {
                "topic": f"conflicting viewpoints in {subtopic}",
                "statements": ["Source A says X", "Source B says not X"],
                "source_chunk_ids": ["ca", "cb"],
                "severity": "medium",
            }
        ] * contradictions
    return s


def _sample_bundle(subtopic: str) -> dict[str, Any]:
    return {
        "subtopic": subtopic,
        "evidence": [
            {
                "content": f"Content about {subtopic}",
                "chunk_id": f"c_{subtopic}",
                "relevance_score": 85.0,
            },
        ],
        "sources": ["arxiv"],
        "confidence_score": 70.0,
        "coverage": True,
    }


def _full_state() -> Any:
    state = make_initial_state(query="agentic AI security")
    state["planner_output"] = json.dumps(_sample_planner())
    state["summaries"] = [
        _sample_summary("Architecture security", citations=3, conf=75.0),
        _sample_summary("Threat models", citations=2, conf=65.0),
        _sample_summary("Governance compliance", citations=4, conf=80.0),
    ]
    state["retrieved_documents"] = [
        _sample_bundle("Architecture security"),
        _sample_bundle("Threat models"),
        _sample_bundle("Governance compliance"),
    ]
    return state


# ── Model / Schema Tests ────────────────────────────────


class TestGapSchemas:
    def test_research_gap_creation(self) -> None:
        gap = ResearchGap(
            gap_id="test_gap_1",
            gap_type=GapType.MISSING_SUBTOPIC,
            description="Test gap",
            severity=SeverityLevel.HIGH,
            affected_subtopics=["topic1"],
            supporting_evidence="evidence here",
            remediation=RemediationSuggestion(
                recommended_queries=["q1"],
                recommended_sources=["s1"],
                recommended_actions=["a1"],
            ),
            confidence=80.0,
        )
        assert gap.gap_id == "test_gap_1"
        assert gap.gap_type == GapType.MISSING_SUBTOPIC
        assert gap.severity == SeverityLevel.HIGH
        assert gap.confidence == 80.0

    def test_gap_type_enum_values(self) -> None:
        assert GapType.MISSING_SUBTOPIC.value == "MISSING_SUBTOPIC"
        assert GapType.LOW_EVIDENCE.value == "LOW_EVIDENCE"
        assert GapType.CONTRADICTION.value == "CONTRADICTION"
        assert GapType.OUTDATED_INFORMATION.value == "OUTDATED_INFORMATION"
        assert len(GapType) == 10

    def test_severity_level_ordering(self) -> None:
        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.HIGH.value == "high"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.LOW.value == "low"

    def test_coverage_metrics_defaults(self) -> None:
        m = CoverageMetrics()
        assert m.coverage_score == 0.0
        assert m.total_gaps == 0

    def test_remediation_suggestion_defaults(self) -> None:
        r = RemediationSuggestion()
        assert r.recommended_queries == []
        assert r.recommended_sources == []
        assert r.recommended_actions == []


# ── Planner Parsing Tests ───────────────────────────────


class TestPlannerParsing:
    def test_parse_valid_json(self) -> None:
        data = '{"subtopics": ["a", "b"], "research_questions": ["q1"]}'
        result = _parse_planner(data)
        assert result["subtopics"] == ["a", "b"]

    def test_parse_invalid_json(self) -> None:
        result = _parse_planner("not json")
        assert result == {}

    def test_parse_none(self) -> None:
        assert _parse_planner(None) == {}

    def test_parse_dict_passthrough(self) -> None:
        d = {"key": "value"}
        assert _parse_planner(d) is d


# ── Gap Detection Tests ─────────────────────────────────


class TestGapDetection:
    def test_detect_missing_subtopics(self) -> None:
        planner = _sample_planner()
        summaries = [
            _sample_summary("Architecture security"),
            _sample_summary("Threat models"),
        ]
        gaps = _detect_missing_subtopics(planner, summaries, [])
        missing_subtopics = [g.description for g in gaps]
        assert any("Governance compliance" in d for d in missing_subtopics)
        assert any("Human oversight" in d for d in missing_subtopics)
        assert any("Framework evaluation" in d for d in missing_subtopics)
        assert all(g.gap_type == GapType.MISSING_SUBTOPIC for g in gaps)

    def test_detect_low_evidence(self) -> None:
        planner = _sample_planner()
        summaries = [
            _sample_summary("Good topic", citations=5, conf=80.0),
            _sample_summary("Weak topic", citations=0, conf=20.0),
        ]
        gaps = _detect_low_evidence(planner, summaries, [])
        low = [g for g in gaps if g.gap_type == GapType.LOW_EVIDENCE]
        assert len(low) >= 1
        assert any("Weak topic" in g.description for g in low)

    def test_detect_contradictions(self) -> None:
        planner = _sample_planner()
        summaries = [
            _sample_summary("Controversial topic", contradictions=2, conf=60.0),
            _sample_summary("Clean topic", contradictions=0, conf=80.0),
        ]
        gaps = _detect_contradictions(planner, summaries, [])
        contra = [g for g in gaps if g.gap_type == GapType.CONTRADICTION]
        assert len(contra) >= 1
        assert any("Controversial" in g.description for g in contra)

    def test_detect_missing_risk_analysis(self) -> None:
        planner = _sample_planner()
        summaries = [_sample_summary("Architecture security")]
        gaps = _detect_missing_risk_analysis(planner, summaries, [])
        missing_risk = [g for g in gaps if g.gap_type == GapType.MISSING_RISK_ANALYSIS]
        assert len(missing_risk) >= 1
        assert any("Autonomous decision risks" in g.description for g in missing_risk)

    def test_detect_missing_priority_area(self) -> None:
        planner = _sample_planner()
        summaries = [_sample_summary("Architecture security")]
        gaps = _detect_missing_priority_area(planner, summaries, [])
        missing_prio = [g for g in gaps if g.gap_type == GapType.MISSING_PRIORITY_AREA]
        assert len(missing_prio) >= 1

    def test_detect_missing_research_question(self) -> None:
        planner = _sample_planner()
        summaries = [_sample_summary("Generic")]  # won't cover specific questions
        gaps = _detect_missing_research_question(planner, summaries, [])
        missing_q = [g for g in gaps if g.gap_type == GapType.MISSING_RESEARCH_QUESTION]
        assert len(missing_q) >= 1

    def test_detect_low_confidence(self) -> None:
        planner = _sample_planner()
        summaries = [
            _sample_summary("Low confidence", citations=1, conf=15.0),
            _sample_summary("High confidence", citations=5, conf=85.0),
        ]
        gaps = _detect_low_confidence_summary(planner, summaries, [])
        low_conf = [g for g in gaps if g.gap_type == GapType.LOW_CONFIDENCE_SUMMARY]
        assert len(low_conf) >= 1
        assert any("Low confidence" in g.description for g in low_conf)

    def test_detect_insufficient_source_diversity(self) -> None:
        planner = _sample_planner()
        # All summaries have the same source -> triggers diversity gap
        summaries = [
            {
                "subtopic": "a",
                "supporting_evidence": ["arxiv paper"],
                "citation_count": 1,
                "source_count": 1,
                "confidence_score": 50,
                "contradictions": [],
                "key_findings": [],
            },
            {
                "subtopic": "b",
                "supporting_evidence": ["arxiv paper"],
                "citation_count": 1,
                "source_count": 1,
                "confidence_score": 50,
                "contradictions": [],
                "key_findings": [],
            },
        ]
        gaps = _detect_insufficient_source_diversity(planner, summaries, [])
        div_gaps = [
            g for g in gaps if g.gap_type == GapType.INSUFFICIENT_SOURCE_DIVERSITY
        ]
        assert len(div_gaps) >= 1

    def test_full_detection_pipeline(self) -> None:
        planner = json.dumps(_sample_planner())
        summaries = [
            _sample_summary("Architecture security", citations=3, conf=75.0),
            _sample_summary("Threat models", citations=1, conf=30.0),
        ]
        bundles = []
        gaps = detect_all_gaps(planner, summaries, bundles)
        assert len(gaps) > 0
        types_found = {g.gap_type for g in gaps}
        assert GapType.MISSING_SUBTOPIC in types_found
        assert any(
            g.severity
            in (SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM)
            for g in gaps
        )


# ── Severity Scoring Tests ──────────────────────────────


class TestSeverityScoring:
    def test_base_severity_values(self) -> None:
        assert _base_severity(GapType.MISSING_RESEARCH_QUESTION) >= _base_severity(
            GapType.LOW_CONFIDENCE_SUMMARY
        )
        assert _base_severity(GapType.MISSING_RISK_ANALYSIS) == 7
        assert _base_severity(GapType.LOW_CONFIDENCE_SUMMARY) == 2

    def test_severity_with_planner(self) -> None:
        planner = {"planning_score": 90, "priority_areas": ["a", "b", "c"]}
        sev = compute_severity(GapType.MISSING_PRIORITY_AREA, planner)
        assert sev in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)

    def test_severity_without_planner(self) -> None:
        sev = compute_severity(GapType.LOW_CONFIDENCE_SUMMARY, None)
        assert sev == SeverityLevel.LOW

    def test_severity_low_confidence_modifier(self) -> None:
        summary = {"confidence_score": 10, "citation_count": 0}
        sev = compute_severity(GapType.LOW_CONFIDENCE_SUMMARY, None, summary)
        assert sev in (SeverityLevel.LOW, SeverityLevel.MEDIUM)

    def test_severity_contradiction_modifier(self) -> None:
        summary = {
            "contradictions": [{"topic": "t1"}, {"topic": "t2"}, {"topic": "t3"}]
        }
        sev = compute_severity(GapType.CONTRADICTION, None, summary)
        assert sev in (SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM)


# ── Coverage Metrics Tests ──────────────────────────────


class TestCoverageMetrics:
    def test_coverage_metrics_values(self) -> None:
        planner = _sample_planner()
        summaries = [
            _sample_summary("Architecture security", citations=3, conf=80.0),
            _sample_summary("Threat models", citations=2, conf=65.0),
        ]
        gaps = detect_all_gaps(json.dumps(planner), summaries, [])
        metrics = compute_coverage_metrics(gaps, planner, summaries)
        assert metrics.coverage_score > 0
        assert metrics.total_gaps >= 2
        assert metrics.subtopics_planned == 5
        assert metrics.subtopics_covered >= 2

    def test_question_completion(self) -> None:
        planner = _sample_planner()
        mapping = build_question_mapping(planner["research_questions"], [])
        assert all(v == "uncovered" for v in mapping.values())
        assert len(mapping) == 5

    def test_priority_mapping(self) -> None:
        planner = _sample_planner()
        summaries = [_sample_summary("Architecture security")]
        mapping = build_priority_mapping(planner["priority_areas"], summaries)
        assert mapping.get("Architecture security") == "covered"

    def test_risk_mapping(self) -> None:
        planner = _sample_planner()
        mapping = build_risk_mapping(planner["risk_areas"], [])
        assert all(v == "uncovered" for v in mapping.values())

    def test_metrics_all_zeros_no_data(self) -> None:
        metrics = compute_coverage_metrics([], None, [])
        assert metrics.coverage_score == 0.0
        assert metrics.total_gaps == 0
        assert metrics.subtopics_planned == 0


# ── State Integration Tests ──────────────────────────────


class TestStateIntegration:
    @pytest.mark.asyncio
    async def test_agent_populates_research_gaps(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = _full_state()
        result = await agent.run(state)
        assert result.success is True
        assert len(state.get("research_gaps", [])) > 0

    @pytest.mark.asyncio
    async def test_agent_sets_status(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        assert state["status"] == "gap_detection_complete"

    @pytest.mark.asyncio
    async def test_agent_metrics_populated(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        metrics = state["agent_metrics"]["gap_detection"]
        assert "metrics" in metrics
        assert metrics["metrics"]["total_gaps"] > 0
        assert "latency_seconds" in metrics

    @pytest.mark.asyncio
    async def test_fallback_no_summaries(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = make_initial_state(query="test")
        state["planner_output"] = json.dumps(_sample_planner())
        state["summaries"] = []
        result = await agent.run(state)
        assert result.success is True
        gaps = state.get("research_gaps", [])
        assert len(gaps) >= 1
        assert state["agent_metrics"]["gap_detection"]["used_fallback"] is True

    @pytest.mark.asyncio
    async def test_gap_ids_are_unique(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        ids = [g.get("gap_id") for g in state["research_gaps"]]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_each_gap_has_required_fields(self) -> None:
        provider = MockProvider()
        agent = GapDetectionAgent(llm_provider=provider)
        state = _full_state()
        await agent.run(state)
        for g in state["research_gaps"]:
            assert "gap_id" in g
            assert "gap_type" in g
            assert "description" in g
            assert "severity" in g
            assert "confidence" in g


# ── Debug Endpoint Test ─────────────────────────────────


class TestDebugEndpoint:
    def test_debug_request_model(self) -> None:
        from app.api.gap_debug import DebugGapRequest

        req = DebugGapRequest(
            planner_output=json.dumps(_sample_planner()),
            summaries=[_sample_summary("Architecture security")],
            query="test",
        )
        assert req.query == "test"
        assert len(req.summaries) == 1
        assert req.planner_output is not None

    def test_debug_response_model(self) -> None:
        from app.api.gap_debug import DebugGapResponse

        resp = DebugGapResponse(
            gaps=[
                ResearchGap(
                    gap_id="test",
                    gap_type=GapType.MISSING_SUBTOPIC,
                    description="x",
                    severity=SeverityLevel.LOW,
                ).model_dump()
            ],
            metrics=CoverageMetrics(total_gaps=1),
            question_mapping={"q1": "uncovered"},
            priority_mapping={"p1": "covered"},
            risk_mapping={"r1": "uncovered"},
            gap_count=1,
            severity_distribution={"critical": 0, "high": 0, "medium": 0, "low": 1},
            total_gaps=1,
        )
        assert resp.gap_count == 1
        assert resp.severity_distribution["low"] == 1


# ── Graph Node Test ─────────────────────────────────────


class TestGraphNode:
    @pytest.mark.asyncio
    async def test_gap_detection_node(self) -> None:
        from app.graphs.nodes import gap_detection_node

        state = _full_state()
        result = await gap_detection_node(state)
        assert "research_gaps" in result
        assert len(result["research_gaps"]) > 0
        assert result["status"] == "gap_detection_complete"
        assert len(result.get("execution_history", [])) > 0
        # Verify at least one entry has the node name
        node_entries = [
            e for e in result["execution_history"] if e.get("node") == "gap_detection"
        ]
        assert len(node_entries) >= 1


# ── Edge Cases and Error Handling ───────────────────────


class TestEdgeCases:
    def test_empty_planner(self) -> None:
        gaps = detect_all_gaps(None, [], [])
        assert gaps == []

    def test_no_summaries_detection(self) -> None:
        gaps = detect_all_gaps(json.dumps(_sample_planner()), [], [])
        # Should detect missing subtopics, missing risk, missing priorities from planner alone
        assert len(gaps) > 0

    def test_all_subtopics_covered_no_gaps_for_that_type(self) -> None:
        planner = _sample_planner()
        summaries = [_sample_summary(s) for s in planner["subtopics"]]
        gaps = _detect_missing_subtopics(planner, summaries, [])
        missing = [g for g in gaps if g.gap_type == GapType.MISSING_SUBTOPIC]
        assert len(missing) == 0

    def test_contradictions_with_empty_list(self) -> None:
        gaps = _detect_contradictions({}, [], [])
        assert gaps == []

    def test_remediation_generation_all_types(self) -> None:
        for gt in GapType:
            rem = generate_remediation(gt, _sample_planner(), [], [])
            assert isinstance(rem, RemediationSuggestion)
            assert isinstance(rem.recommended_queries, list)
            assert isinstance(rem.recommended_sources, list)
            assert isinstance(rem.recommended_actions, list)

    def test_severity_all_types_produces_valid_level(self) -> None:
        for gt in GapType:
            sev = compute_severity(gt, {"planning_score": 50})
            assert sev in SeverityLevel
