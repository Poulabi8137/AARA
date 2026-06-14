from __future__ import annotations

import json
import math
from typing import Any

import pytest

from app.evaluation.benchmark import (
    BUILTIN_BENCHMARKS,
    BenchmarkDefinition,
    BenchmarkRunner,
    _collect_findings,
    _collect_references,
    _collect_subtopics,
    _normalize_reference,
    _significant_words,
)
from app.evaluation.metrics import (
    METRIC_REGISTRY,
    compute_citation_density,
    compute_evidence_strength,
    compute_gap_coverage,
    compute_hallucination_proxy,
    compute_question_coverage,
    compute_report_completeness,
    compute_research_quality,
    compute_source_diversity,
    compute_summary_quality,
)
from app.evaluation.evaluators import WorkflowEvaluator
from app.evaluation.scorecard import generate_scorecard, _safe_parse_report
from app.evaluation.report import build_evaluation_report


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_planner_questions() -> list[str]:
    return [
        "What are the key challenges in reinforcement learning?",
        "How does transfer learning improve model performance?",
        "What are the ethical implications of large language models?",
        "How can we measure AI system robustness?",
    ]


@pytest.fixture
def sample_summaries() -> list[dict[str, Any]]:
    return [
        {
            "subtopic": "Reinforcement Learning Challenges",
            "executive_summary": "Key challenges include sample efficiency and reward design.",
            "key_findings": [
                "Sample efficiency remains a major bottleneck in RL",
                "Reward hacking can lead to unintended behaviors",
            ],
            "citations": [
                {"claim": "Sample efficiency is a bottleneck", "source": "arxiv.org/abs/2101.03958", "supporting_chunk_ids": ["c1"]},
                {"claim": "Reward hacking causes issues", "source": "arxiv.org/abs/2005.08691", "supporting_chunk_ids": ["c2"]},
            ],
            "sources": ["arxiv.org/abs/2101.03958", "arxiv.org/abs/2005.08691"],
            "supporting_evidence": [{"content": "Evidence content 1", "relevance_score": 85.0}],
            "coverage_score": 80.0,
            "citation_strength": 70.0,
            "consistency_score": 90.0,
            "summary_score": 85.0,
            "evidence_density": 75.0,
            "confidence_score": 80.0,
            "citation_count": 2,
            "source_count": 2,
        },
        {
            "subtopic": "Transfer Learning Methods",
            "executive_summary": "Transfer learning improves performance through pre-training.",
            "key_findings": [
                "Pre-training on large datasets improves downstream task performance",
            ],
            "citations": [
                {"claim": "Pre-training improves performance", "source": "arxiv.org/abs/1905.05583", "supporting_chunk_ids": ["c3"]},
            ],
            "sources": ["arxiv.org/abs/1905.05583"],
            "supporting_evidence": [{"content": "Evidence content 2", "relevance_score": 90.0}],
            "coverage_score": 75.0,
            "citation_strength": 65.0,
            "consistency_score": 85.0,
            "summary_score": 80.0,
            "evidence_density": 70.0,
            "confidence_score": 75.0,
            "citation_count": 1,
            "source_count": 1,
        },
    ]


@pytest.fixture
def sample_gaps() -> list[dict[str, Any]]:
    return [
        {"gap_id": "g1", "gap_type": "LOW_EVIDENCE", "severity": "high", "description": "Low evidence for RL subtopic", "affected_subtopics": ["RL"], "supporting_evidence": "", "confidence": 85.0},
        {"gap_id": "g2", "gap_type": "MISSING_SUBTOPIC", "severity": "medium", "description": "Missing safety considerations", "affected_subtopics": ["safety"], "supporting_evidence": "", "confidence": 70.0},
    ]


@pytest.fixture
def sample_report() -> dict[str, Any]:
    return {
        "title": "Test Report",
        "executive_summary": "This report covers AI topics.",
        "introduction": "Introduction content.",
        "methodology": "Literature review.",
        "conclusion": "AI continues to advance rapidly with significant implications for safety and ethics.",
        "key_findings": ["Finding 1", "Finding 2"],
        "limitations": "Limited data.",
        "recommendations": ["More research needed."],
        "future_research": ["Explore safety."],
        "sections": [
            {
                "title": "RL Challenges",
                "summary": "Details about RL challenges.",
                "key_findings": ["Sample efficiency bottleneck", "Reward design complexity"],
                "citations": [
                    {"claim": "Sample efficiency is hard", "source": "arxiv.org/abs/2101.03958", "supporting_chunk_ids": ["c1"]},
                ],
            },
            {
                "title": "Transfer Learning",
                "summary": "Details about transfer learning.",
                "key_findings": ["Pre-training helps", "Fine-tuning requires care"],
                "citations": [
                    {"claim": "Pre-training works", "source": "arxiv.org/abs/1905.05583", "supporting_chunk_ids": ["c3"]},
                ],
            },
        ],
    }


@pytest.fixture
def sample_state(
    sample_planner_questions: list[str],
    sample_summaries: list[dict[str, Any]],
    sample_gaps: list[dict[str, Any]],
    sample_report: dict[str, Any],
) -> dict[str, Any]:
    planner_output = json.dumps({
        "research_questions": sample_planner_questions,
        "subtopics": ["RL Challenges", "Transfer Learning", "Ethics"],
        "search_queries": ["query1", "query2", "query3", "query4", "query5"],
        "keywords": ["RL", "transfer", "ethics"],
        "research_goal": "Test research goal",
        "expected_deliverables": ["report"],
        "priority_areas": ["safety"],
        "risk_areas": ["bias"],
        "methodology": "literature review",
        "estimated_steps": 5,
        "planning_score": 80,
        "completeness": 85,
        "coverage": 75,
        "specificity": 80,
    })
    return {
        "query": "Test query about AI research",
        "planner_output": planner_output,
        "summaries": sample_summaries,
        "research_gaps": sample_gaps,
        "generated_report": sample_report,
        "retrieved_documents": [
            {"source": "arxiv.org/abs/2101.03958", "content": "RL challenges content"},
            {"source": "arxiv.org/abs/1905.05583", "content": "Transfer learning content"},
            {"source": "arxiv.org/abs/2005.08691", "content": "Reward hacking content"},
        ],
        "status": "report_generation_complete",
        "execution_history": [],
        "agent_metrics": {},
        "errors": [],
        "timestamp": "2026-06-13T00:00:00",
    }


# =============================================================================
# Metric Tests
# =============================================================================

class TestQuestionCoverage:
    def test_full_coverage(self):
        questions = ["What is deep learning?", "How does RL work?"]
        summaries = [
            {"subtopic": "Deep Learning", "executive_summary": "Deep learning uses neural networks", "key_findings": []},
            {"subtopic": "RL", "executive_summary": "RL uses rewards", "key_findings": ["RL works with rewards"]},
        ]
        score = compute_question_coverage(questions, [], summaries)
        assert 0 <= score <= 100

    def test_no_questions(self):
        assert compute_question_coverage([], [], []) == 0.0

    def test_no_summaries(self):
        score = compute_question_coverage(["What is AI?"], [], [])
        assert score == 0.0


class TestCitationDensity:
    def test_density_score(self):
        score = compute_citation_density(
            [{"claim": "c1"}, {"claim": "c2"}, {"claim": "c3"}, {"claim": "c4"}],
            [{"title": "s1"}, {"title": "s2"}],
        )
        assert score == 100.0  # 4/2 = 2, min(2/2, 1)*100 = 100

    def test_low_density(self):
        score = compute_citation_density(
            [{"claim": "c1"}],
            [{"title": "s1"}, {"title": "s2"}],
        )
        assert score == 25.0  # 1/2 = 0.5, (0.5/2)*100 = 25

    def test_no_citations(self):
        score = compute_citation_density([], [{"title": "s1"}])
        assert score == 0.0

    def test_no_sections(self):
        score = compute_citation_density([{"claim": "c1"}], [])
        assert score == 50.0  # 1/1 = 1, (1/2)*100 = 50


class TestSourceDiversity:
    def test_high_diversity(self):
        citations = [
            {"source": "src1"}, {"source": "src2"},
            {"source": "src3"}, {"source": "src4"},
            {"source": "src5"}, {"source": "src6"},
        ]
        score = compute_source_diversity(["src1", "src2", "src3"], citations)
        assert 50 <= score <= 100

    def test_no_sources(self):
        assert compute_source_diversity([], []) == 0.0

    def test_single_source(self):
        citations = [{"source": "src1"}, {"source": "src1"}, {"source": "src1"}]
        score = compute_source_diversity(["src1"], citations)
        assert score < 60  # low diversity


class TestEvidenceStrength:
    def test_strong_evidence(self):
        chunks = [
            {"content": "e1", "relevance_score": 90.0},
            {"content": "e2", "relevance_score": 85.0},
            {"content": "e3", "relevance_score": 95.0},
        ]
        score = compute_evidence_strength(chunks, ["f1", "f2"])
        assert 40 <= score <= 100

    def test_no_evidence(self):
        assert compute_evidence_strength([], ["f1"]) == 0.0

    def test_no_findings(self):
        score = compute_evidence_strength([{"content": "e1"}], [])
        assert score > 0


class TestSummaryQuality:
    def test_high_quality(self, sample_summaries):
        score = compute_summary_quality(sample_summaries)
        assert 70 <= score <= 100

    def test_no_summaries(self):
        assert compute_summary_quality([]) == 0.0


class TestGapCoverage:
    def test_no_gaps(self):
        assert compute_gap_coverage([]) == 100.0

    def test_with_gaps(self, sample_gaps):
        score = compute_gap_coverage(sample_gaps)
        assert 80 <= score <= 100  # 100 - 8 - 4 = 88

    def test_critical_penalty(self):
        gaps = [{"severity": "critical"}, {"severity": "critical"}]
        score = compute_gap_coverage(gaps)
        assert score == 70.0  # 100 - 15 - 15 = 70

    def test_all_severities(self):
        gaps = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        score = compute_gap_coverage(gaps)
        assert score == 72.0  # 100 - 15 - 8 - 4 - 1 = 72

    def test_max_penalty_floor(self):
        gaps = [{"severity": "critical"}] * 10
        score = compute_gap_coverage(gaps)
        assert score >= 0.0


class TestReportCompleteness:
    def test_complete_report(self, sample_report):
        score = compute_report_completeness(sample_report, sample_report.get("sections", []))
        assert score == 100.0

    def test_none_report(self):
        assert compute_report_completeness(None, []) == 0.0

    def test_partial_report(self):
        report = {"executive_summary": "yes", "introduction": "", "methodology": "yes"}
        score = compute_report_completeness(report, [])
        assert score == 25.0  # 2/8 = 0.25


class TestHallucinationProxy:
    def test_low_risk(self):
        report = {
            "executive_summary": "Summary.",
            "introduction": "Intro.",
            "methodology": "Method.",
            "conclusion": "AI advances rapidly.",
            "key_findings": ["Finding 1", "Finding 2"],
            "limitations": "None.",
            "recommendations": ["More research."],
            "future_research": ["Explore."],
            "sections": [
                {
                    "title": "Section 1",
                    "key_findings": ["This is finding one about AI alignment"],
                    "evidence_highlights": ["evidence highlight content"],
                    "citations": [
                        {"claim": "finding one about AI alignment", "source": "src1", "supporting_chunk_ids": ["c1"]},
                        {"claim": "evidence highlight content", "source": "src2", "supporting_chunk_ids": ["c2"]},
                    ],
                },
            ],
        }
        sections = report.get("sections", [])
        citations = sections[0].get("citations", [])
        score = compute_hallucination_proxy(
            report, sections, citations,
            ["finding one about AI alignment", "evidence highlight content"],
        )
        assert score <= 50.0

    def test_high_risk_no_report(self):
        assert compute_hallucination_proxy(None, [], [], []) == 100.0

    def test_high_risk_no_citations(self, sample_report):
        score = compute_hallucination_proxy(
            sample_report,
            sample_report.get("sections", []),
            [],
            [],
        )
        assert score > 50.0  # high risk expected


class TestResearchQuality:
    def test_composite(self):
        score = compute_research_quality(
            question_coverage=90.0,
            citation_density=80.0,
            source_diversity=85.0,
            evidence_strength=75.0,
            summary_quality=85.0,
            gap_coverage=88.0,
            report_completeness=100.0,
            hallucination_risk=10.0,
        )
        assert 70 <= score <= 100

    def test_low_quality(self):
        score = compute_research_quality(0, 0, 0, 0, 0, 0, 0, 100)
        assert score < 20  # all zeros, high hallucination risk

    def test_bounds(self):
        score = compute_research_quality(100, 100, 100, 100, 100, 100, 100, 0)
        assert score == 100.0


class TestMetricRegistry:
    def test_all_metrics_present(self):
        expected = {
            "question_coverage", "citation_density", "source_diversity",
            "evidence_strength", "summary_quality", "gap_coverage",
            "report_completeness", "hallucination_risk", "research_quality",
        }
        assert set(METRIC_REGISTRY.keys()) == expected

    def test_all_metrics_callable(self):
        for name, fn in METRIC_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"


# =============================================================================
# Scorecard Tests
# =============================================================================

class TestScorecard:
    def test_generate_scorecard(self, sample_state):
        result = generate_scorecard(sample_state)
        assert "scores" in result
        assert "details" in result
        assert "composite" in result
        assert "summary" in result
        assert 0 <= result["composite"] <= 100
        assert len(result["scores"]) >= 8

    def test_scorecard_empty_state(self):
        result = generate_scorecard({})
        assert result["composite"] < 40  # low quality for empty
        assert result["summary"]["passed"] is False

    def test_scorecard_summary_tier(self, sample_state):
        result = generate_scorecard(sample_state)
        tier = result["summary"]["tier"]
        assert tier in ("excellent", "good", "acceptable", "poor")


class TestSafeParseReport:
    def test_dict_passthrough(self):
        report = {"key": "value"}
        assert _safe_parse_report(report) == report

    def test_json_string(self):
        report = '{"key": "value"}'
        assert _safe_parse_report(report) == {"key": "value"}

    def test_invalid_string(self):
        assert _safe_parse_report("not json") is None

    def test_none(self):
        assert _safe_parse_report(None) is None


# =============================================================================
# Benchmark Tests
# =============================================================================

class TestBenchmarkDefinition:
    def test_create_benchmark(self):
        bm = BenchmarkDefinition(
            name="test_benchmark",
            query="test query",
            expected_findings=["f1", "f2"],
            expected_subtopics=["s1"],
            expected_references=["r1"],
        )
        assert bm.name == "test_benchmark"
        assert bm.id is not None

    def test_to_dict(self):
        bm = BenchmarkDefinition("bm1", "q?", ["f1"], ["s1"], ["r1"])
        d = bm.to_dict()
        assert d["name"] == "bm1"
        assert d["query"] == "q?"

    def test_from_dict(self):
        d = {
            "name": "bm2",
            "query": "q2",
            "expected_findings": ["f1"],
            "expected_subtopics": ["s1"],
            "expected_references": ["r1"],
        }
        bm = BenchmarkDefinition.from_dict(d)
        assert bm.name == "bm2"

    def test_from_dict_with_id(self):
        d = {
            "id": "custom-id",
            "name": "bm3",
            "query": "q3",
            "expected_findings": [],
            "expected_subtopics": [],
            "expected_references": [],
        }
        bm = BenchmarkDefinition.from_dict(d)
        assert bm.id == "custom-id"


class TestBuiltinBenchmarks:
    def test_three_benchmarks(self):
        assert len(BUILTIN_BENCHMARKS) == 3

    def test_all_have_names(self):
        for bm in BUILTIN_BENCHMARKS:
            assert bm.name, f"Benchmark missing name: {bm}"

    def test_all_have_queries(self):
        for bm in BUILTIN_BENCHMARKS:
            assert bm.query, f"Benchmark {bm.name} missing query"

    def test_ai_safety_findings(self):
        bm = BUILTIN_BENCHMARKS[0]
        assert len(bm.expected_findings) >= 3


class TestBenchmarkRunner:
    def test_list_benchmarks(self):
        runner = BenchmarkRunner()
        benchmarks = runner.list_benchmarks()
        assert len(benchmarks) == 3

    def test_get_benchmark_found(self):
        runner = BenchmarkRunner()
        bm = runner.get_benchmark("ai_safety_research")
        assert bm is not None
        assert bm.name == "ai_safety_research"

    def test_get_benchmark_not_found(self):
        runner = BenchmarkRunner()
        assert runner.get_benchmark("nonexistent") is None

    @pytest.mark.asyncio
    async def test_run_benchmark(self, sample_state):
        runner = BenchmarkRunner()
        result = await runner.run_benchmark("ai_safety_research", sample_state)
        assert "benchmark" in result
        assert "finding_match_rate" in result
        assert "subtopic_match_rate" in result
        assert "reference_match_rate" in result
        assert "overall_benchmark_score" in result
        assert "passed" in result

    @pytest.mark.asyncio
    async def test_run_invalid_benchmark(self):
        runner = BenchmarkRunner()
        with pytest.raises(ValueError, match="Unknown benchmark"):
            await runner.run_benchmark("nonexistent", {})

    def test_compute_match_rate(self):
        rate = BenchmarkRunner.compute_match_rate(
            ["reinforcement learning challenges", "transfer learning"],
            ["reinforcement learning is about rewards", "transfer learning improves models"],
        )
        assert rate > 50.0
        assert rate <= 100.0

    def test_compute_match_rate_empty_expected(self):
        rate = BenchmarkRunner.compute_match_rate([], ["something"])
        assert rate == 100.0

    def test_compute_match_rate_no_actual(self):
        rate = BenchmarkRunner.compute_match_rate(["something"], [])
        assert rate == 0.0

    def test_compute_reference_match_rate(self):
        rate = BenchmarkRunner.compute_reference_match_rate(
            ["https://arxiv.org/abs/2101.03958"],
            ["arxiv.org/abs/2101.03958"],
        )
        assert rate == 100.0

    def test_compute_reference_match_rate_no_match(self):
        rate = BenchmarkRunner.compute_reference_match_rate(
            ["https://arxiv.org/abs/2101.03958"],
            ["arxiv.org/abs/9999.99999"],
        )
        assert rate == 0.0


class TestBenchmarkHelpers:
    def test_collect_findings(self, sample_state):
        findings = _collect_findings(sample_state)
        assert len(findings) > 0

    def test_collect_subtopics(self, sample_state):
        subtopics = _collect_subtopics(sample_state)
        assert len(subtopics) > 0

    def test_collect_references(self, sample_state):
        refs = _collect_references(sample_state)
        assert len(refs) > 0

    def test_collect_findings_empty(self):
        assert _collect_findings({}) == []

    def test_significant_words(self):
        words = _significant_words("The quick brown fox jumps")
        assert "quick" in words
        assert "the" not in words

    def test_normalize_reference(self):
        assert _normalize_reference("HTTPS://ARXIV.ORG/ABS/2101.03958/") == "arxiv.org/abs/2101.03958"
        assert _normalize_reference("") == ""


# =============================================================================
# Evaluator Tests
# =============================================================================

class TestWorkflowEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate(self, sample_state):
        evaluator = WorkflowEvaluator()
        result = await evaluator.evaluate(sample_state)
        assert "scorecard" in result
        assert "metrics" in result
        assert "evaluation_latency" in result
        assert result["query"] == "Test query about AI research"
        assert len(result["metrics"]) >= 8

    @pytest.mark.asyncio
    async def test_evaluate_empty_state(self):
        evaluator = WorkflowEvaluator()
        result = await evaluator.evaluate({})
        assert result["scorecard"]["composite"] < 40

    def test_compute_trend_empty(self):
        evaluator = WorkflowEvaluator()
        trend = evaluator.compute_trend([])
        assert trend["evaluation_count"] == 0
        assert trend["trend_direction"] == "unknown"

    @pytest.mark.asyncio
    async def test_compute_trend_single(self):
        evaluator = WorkflowEvaluator()
        planner_output = json.dumps({
            "research_questions": ["q1", "q2"],
            "subtopics": ["s1", "s2"],
            "search_queries": ["q1", "q2", "q3", "q4", "q5"],
            "keywords": ["k1"],
            "research_goal": "goal",
            "expected_deliverables": ["report"],
            "priority_areas": ["p1"],
            "risk_areas": ["r1"],
            "methodology": "lit review",
            "estimated_steps": 5,
            "planning_score": 80,
            "completeness": 85,
            "coverage": 75,
            "specificity": 80,
        })
        state = {
            "query": "test",
            "planner_output": planner_output,
            "summaries": [
                {"subtopic": "s1", "executive_summary": "S1 content", "key_findings": ["f1"],
                 "citations": [{"claim": "c1", "source": "src1", "supporting_chunk_ids": ["c1"]}],
                 "sources": ["src1"], "supporting_evidence": [],
                 "coverage_score": 80, "citation_strength": 70, "consistency_score": 90,
                 "summary_score": 85, "evidence_density": 75},
                {"subtopic": "s2", "executive_summary": "S2 content", "key_findings": ["f2"],
                 "citations": [{"claim": "c2", "source": "src2", "supporting_chunk_ids": ["c2"]}],
                 "sources": ["src2"], "supporting_evidence": [],
                 "coverage_score": 75, "citation_strength": 65, "consistency_score": 85,
                 "summary_score": 80, "evidence_density": 70},
            ],
            "research_gaps": [],
            "generated_report": {
                "executive_summary": "yes", "introduction": "yes", "methodology": "yes",
                "conclusion": "yes", "key_findings": ["f1"], "limitations": "yes",
                "recommendations": ["r1"], "future_research": ["fr"],
                "sections": [{"title": "s1", "key_findings": ["f1"], "citations": [{"claim": "c1"}]}],
            },
            "retrieved_documents": [],
            "status": "completed",
            "execution_history": [],
            "agent_metrics": {},
            "errors": [],
            "timestamp": "2026-01-01",
        }
        result = await evaluator.evaluate(state, execution_id="exec1")
        trend = evaluator.compute_trend([result])
        assert trend["evaluation_count"] == 1
        assert trend["average_quality"] > 0

    def test_compute_trend_improving(self):
        evaluator = WorkflowEvaluator()
        r1 = {"scorecard": {"composite": 30, "scores": {"a": 30}}}
        r2 = {"scorecard": {"composite": 60, "scores": {"a": 60}}}
        trend = evaluator.compute_trend([r1, r2])
        assert trend["trend_direction"] == "improving"

    def test_compute_trend_declining(self):
        evaluator = WorkflowEvaluator()
        r1 = {"scorecard": {"composite": 80, "scores": {"a": 80}}}
        r2 = {"scorecard": {"composite": 40, "scores": {"a": 40}}}
        trend = evaluator.compute_trend([r1, r2])
        assert trend["trend_direction"] == "declining"

    def test_metric_distributions(self):
        evaluator = WorkflowEvaluator()
        evals = [
            {"scorecard": {"scores": {"m1": 80, "m2": 70}}},
            {"scorecard": {"scores": {"m1": 90, "m2": 60}}},
            {"scorecard": {"scores": {"m1": 85, "m2": 65}}},
        ]
        dist = evaluator.compute_metric_distributions(evals)
        assert "m1" in dist
        assert "m2" in dist
        assert dist["m1"]["avg"] == 85.0
        assert dist["m2"]["min"] == 60.0
        assert dist["m2"]["max"] == 70.0


# =============================================================================
# Report Tests
# =============================================================================

class TestEvaluationReport:
    @pytest.mark.asyncio
    async def test_build_json(self, sample_state):
        import json
        evaluator = WorkflowEvaluator()
        result = await evaluator.evaluate(sample_state)
        report = build_evaluation_report(result, format="json")
        parsed = json.loads(report)
        assert "scorecard" in parsed

    @pytest.mark.asyncio
    async def test_build_markdown(self, sample_state):
        evaluator = WorkflowEvaluator()
        result = await evaluator.evaluate(sample_state)
        report = build_evaluation_report(result, format="markdown")
        assert "# Evaluation Report" in report
        assert "**Composite Score:**" in report
        assert "Score Breakdown" in report

    def test_build_markdown_empty(self):
        result = {
            "query": "empty",
            "evaluated_at": "now",
            "scorecard": {
                "scores": {},
                "composite": 0.0,
                "summary": {"tier": "poor", "passed": False},
            },
        }
        report = build_evaluation_report(result, format="markdown")
        assert "poor" in report.lower()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    def test_generate_scorecard_no_planner(self):
        result = generate_scorecard({"summaries": [], "research_gaps": [], "generated_report": None})
        assert result["composite"] < 20  # all 0s except gap_coverage=100*0.1=10, hallucination_risk=100 gives 0

    def test_generate_scorecard_string_report(self):
        state = {
            "generated_report": json.dumps({
                "executive_summary": "yes", "introduction": "yes", "methodology": "yes",
                "conclusion": "yes", "key_findings": ["f1"], "limitations": "yes",
                "recommendations": ["r1"], "future_research": ["fr"],
                "sections": [],
            }),
        }
        result = generate_scorecard(state)
        assert result["composite"] >= 0

    def test_hallucination_proxy_string_findings(self):
        report = {"conclusion": "AI safety is critical for future development."}
        sections = [
            {
                "title": "Safety",
                "key_findings": ["AI safety is important for alignment"],
                "evidence_highlights": ["evidence 1"],
                "citations": [],
            },
        ]
        score = compute_hallucination_proxy(report, sections, [], [])
        assert score > 0  # high risk because no citations

    def test_source_diversity_empty_citations(self):
        score = compute_source_diversity([], [])
        assert score == 0.0

    def test_benchmark_custom_benchmarks(self):
        custom = [
            BenchmarkDefinition("custom1", "q?", ["f1"], ["s1"], ["r1"]),
        ]
        runner = BenchmarkRunner(benchmarks=custom)
        assert len(runner.list_benchmarks()) == 1
        assert runner.get_benchmark("custom1") is not None

    @pytest.mark.asyncio
    async def test_run_benchmark_with_scorecard(self):
        state = {
            "query": "test",
            "planner_output": json.dumps({"research_questions": ["q1"], "subtopics": ["s1"], "search_queries": ["q1","q2","q3","q4","q5"], "keywords": ["k1"], "research_goal": "g", "expected_deliverables": ["r"], "priority_areas": ["p"], "risk_areas": ["r"], "methodology": "m", "estimated_steps": 5, "planning_score": 80, "completeness": 80, "coverage": 80, "specificity": 80}),
            "summaries": [{"subtopic": "alignment", "executive_summary": "alignment research covers X", "key_findings": ["alignment problem is key"], "citations": [{"claim": "c1", "source": "src1", "supporting_chunk_ids": ["c1"]}], "sources": ["src1"], "supporting_evidence": [{"content": "evidence"}], "coverage_score": 80, "citation_strength": 80, "consistency_score": 80, "summary_score": 80, "evidence_density": 80}],
            "research_gaps": [],
            "generated_report": None,
            "retrieved_documents": [],
            "status": "completed",
            "execution_history": [],
            "agent_metrics": {},
            "errors": [],
            "timestamp": "2026-01-01",
        }
        runner = BenchmarkRunner()
        result = await runner.run_benchmark("ai_safety_research", state)
        assert "finding_match_rate" in result
        assert "overall_benchmark_score" in result
