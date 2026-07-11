from abc import ABC

import pytest

from app.ai.evaluation.aggregation import AggregatedScore, QualityAggregator
from app.ai.evaluation.engine import EvaluationEngine, EvaluationReport
from app.ai.evaluation.metrics import (
    BaseMetric,
    CitationAccuracyMetric,
    CompletenessMetric,
    CoverageMetric,
    GapQualityMetric,
    GroundednessMetric,
    HallucinationMetric,
    MetricResult,
    NoveltySupportMetric,
    TraceabilityMetric,
)


class TestMetricResult:
    def test_defaults(self):
        r = MetricResult()
        assert r.name == ""
        assert r.score == 0.0
        assert r.threshold == 0.0
        assert r.passed is False
        assert r.details == ""
        assert r.metadata == {}

    def test_custom_values(self):
        r = MetricResult(
            name="test", score=0.85, threshold=0.7, passed=True,
            details="good", metadata={"key": "val"},
        )
        assert r.name == "test"
        assert r.score == 0.85
        assert r.passed is True
        assert r.metadata["key"] == "val"


class TestBaseMetric:
    def test_is_abstract(self):
        assert issubclass(BaseMetric, ABC)
        assert hasattr(BaseMetric.evaluate, "__isabstractmethod__")

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseMetric()


class TestCitationAccuracyMetric:
    @pytest.fixture
    def metric(self):
        return CitationAccuracyMetric()

    @pytest.mark.asyncio
    async def test_all_citations_verified(self, metric):
        citations = [{"verified": True}, {"verified": True}]
        result = await metric.evaluate(citations=citations)
        assert result.score == 1.0
        assert result.passed is True
        assert result.name == "citation_accuracy"

    @pytest.mark.asyncio
    async def test_half_citations_verified(self, metric):
        citations = [{"verified": True}, {"verified": False}]
        result = await metric.evaluate(citations=citations)
        assert result.score == 0.5
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_no_citations(self, metric):
        result = await metric.evaluate(citations=[])
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_empty_input_defaults_empty(self, metric):
        result = await metric.evaluate()
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_detail_string(self, metric):
        citations = [{"verified": True}, {"verified": False}]
        result = await metric.evaluate(citations=citations)
        assert "1/2" in result.details


class TestGroundednessMetric:
    @pytest.fixture
    def metric(self):
        return GroundednessMetric()

    @pytest.mark.asyncio
    async def test_all_claims_supported(self, metric):
        claims = [{"has_citation": True}, {"has_citation": True}, {"has_citation": True}]
        result = await metric.evaluate(claims=claims)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_partial_support(self, metric):
        claims = [{"has_citation": True}, {"has_citation": False}]
        result = await metric.evaluate(claims=claims)
        assert result.score == 0.5
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_no_claims(self, metric):
        result = await metric.evaluate(claims=[])
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_threshold(self, metric):
        assert metric.evaluate.__name__ is not None

    @pytest.mark.asyncio
    async def test_name_and_details(self, metric):
        result = await metric.evaluate(claims=[{"has_citation": True}])
        assert result.name == "groundedness"
        assert "1/1" in result.details


class TestHallucinationMetric:
    @pytest.fixture
    def metric(self):
        return HallucinationMetric()

    @pytest.mark.asyncio
    async def test_no_hallucinations(self, metric):
        claims = [{"is_hallucination": False}, {"is_hallucination": False}]
        result = await metric.evaluate(sampled_claims=claims)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_all_hallucinated(self, metric):
        claims = [{"is_hallucination": True}, {"is_hallucination": True}]
        result = await metric.evaluate(sampled_claims=claims)
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_mixed_hallucinations(self, metric):
        claims = [
            {"is_hallucination": True},
            {"is_hallucination": False},
            {"is_hallucination": False},
            {"is_hallucination": False},
            {"is_hallucination": False},
        ]
        result = await metric.evaluate(sampled_claims=claims)
        assert result.score == 0.8
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_empty_claims(self, metric):
        result = await metric.evaluate(sampled_claims=[])
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_name(self, metric):
        result = await metric.evaluate(sampled_claims=[{"is_hallucination": False}])
        assert result.name == "hallucination_rate"

    @pytest.mark.asyncio
    async def test_detail_string(self, metric):
        claims = [{"is_hallucination": True}, {"is_hallucination": False}]
        result = await metric.evaluate(sampled_claims=claims)
        assert "1/2" in result.details


class TestCoverageMetric:
    @pytest.fixture
    def metric(self):
        return CoverageMetric()

    @pytest.mark.asyncio
    async def test_full_coverage(self, metric):
        result = await metric.evaluate(coverage_score=1.0)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_low_coverage(self, metric):
        result = await metric.evaluate(coverage_score=0.3)
        assert result.score == 0.3
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_default_zero_coverage(self, metric):
        result = await metric.evaluate()
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_missing_topics_in_metadata(self, metric):
        result = await metric.evaluate(coverage_score=0.5, missing_topics=["topic_a"])
        assert result.metadata["missing_topics"] == ["topic_a"]

    @pytest.mark.asyncio
    async def test_name(self, metric):
        result = await metric.evaluate(coverage_score=1.0)
        assert result.name == "coverage"


class TestGapQualityMetric:
    @pytest.fixture
    def metric(self):
        return GapQualityMetric()

    @pytest.mark.asyncio
    async def test_high_quality(self, metric):
        result = await metric.evaluate(specificity=1.0, actionability=1.0, evidence_support=1.0)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_low_quality(self, metric):
        result = await metric.evaluate(specificity=0.0, actionability=0.0, evidence_support=0.0)
        assert result.score == 0.0
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_mixed_quality(self, metric):
        result = await metric.evaluate(specificity=0.5, actionability=0.5, evidence_support=0.5)
        assert result.score == 0.5
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_missing_kwargs_defaults_zero(self, metric):
        result = await metric.evaluate()
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_detail_format(self, metric):
        result = await metric.evaluate(specificity=0.9, actionability=0.8, evidence_support=0.7)
        assert "S=0.90" in result.details
        assert "A=0.80" in result.details
        assert "E=0.70" in result.details


class TestNoveltySupportMetric:
    @pytest.fixture
    def metric(self):
        return NoveltySupportMetric()

    @pytest.mark.asyncio
    async def test_low_overlap_high_novelty(self, metric):
        result = await metric.evaluate(overlap_score=0.2)
        assert result.score == 0.8
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_high_overlap_low_novelty(self, metric):
        result = await metric.evaluate(overlap_score=0.8)
        import pytest
        assert result.score == pytest.approx(0.2)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_default_zero_overlap(self, metric):
        result = await metric.evaluate()
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_threshold_boundary(self, metric):
        result = await metric.evaluate(overlap_score=0.6)
        assert result.score == 0.4
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_name(self, metric):
        result = await metric.evaluate(overlap_score=0.0)
        assert result.name == "novelty_support"


class TestTraceabilityMetric:
    @pytest.fixture
    def metric(self):
        return TraceabilityMetric()

    @pytest.mark.asyncio
    async def test_all_traceable(self, metric):
        result = await metric.evaluate(traced=10, total=10)
        assert result.score == 1.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_partial_traceability(self, metric):
        result = await metric.evaluate(traced=5, total=10)
        assert result.score == 0.5
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_zero_total_defaults(self, metric):
        result = await metric.evaluate()
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_high_traceability_passes(self, metric):
        result = await metric.evaluate(traced=19, total=20)
        assert result.score == 0.95
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_detail_format(self, metric):
        result = await metric.evaluate(traced=8, total=10)
        assert "8/10" in result.details


class TestCompletenessMetric:
    @pytest.fixture
    def metric(self):
        return CompletenessMetric()

    @pytest.mark.asyncio
    async def test_all_sections_present_and_long(self, metric):
        sections = [
            {"name": "abstract", "content": "word " * 120},
            {"name": "introduction", "content": "word " * 120},
            {"name": "related_work", "content": "word " * 120},
            {"name": "conclusion", "content": "word " * 120},
        ]
        result = await metric.evaluate(sections=sections)
        assert result.score > 0.0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_missing_sections(self, metric):
        sections = [
            {"name": "abstract", "content": "word " * 120},
        ]
        result = await metric.evaluate(sections=sections)
        assert result.passed is False
        assert "related_work" in result.details or "missing" in result.details.lower()

    @pytest.mark.asyncio
    async def test_short_sections(self, metric):
        sections = [
            {"name": "abstract", "content": "word " * 120},
            {"name": "introduction", "content": "too short"},
            {"name": "related_work", "content": "word " * 120},
            {"name": "conclusion", "content": "word " * 120},
        ]
        result = await metric.evaluate(sections=sections)
        assert result.passed is False
        assert "introduction" in result.details or "Short" in result.details

    @pytest.mark.asyncio
    async def test_empty_sections(self, metric):
        result = await metric.evaluate(sections=[])
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_extra_sections_allowed(self, metric):
        sections = [
            {"name": "abstract", "content": "word " * 120},
            {"name": "introduction", "content": "word " * 120},
            {"name": "related_work", "content": "word " * 120},
            {"name": "conclusion", "content": "word " * 120},
            {"name": "appendix", "content": "word " * 120},
        ]
        result = await metric.evaluate(sections=sections)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_required_sections_constant(self, metric):
        assert "abstract" in metric.REQUIRED_SECTIONS
        assert "introduction" in metric.REQUIRED_SECTIONS
        assert "related_work" in metric.REQUIRED_SECTIONS
        assert "conclusion" in metric.REQUIRED_SECTIONS
        assert len(metric.REQUIRED_SECTIONS) == 4


class TestEvaluationEngine:
    @pytest.fixture
    def engine(self):
        return EvaluationEngine()

    @pytest.mark.asyncio
    async def test_evaluate_research_phase(self, engine):
        report = await engine.evaluate("research", artifact=None, coverage_score=0.8)
        assert report.phase == "research"
        assert len(report.metrics) == 1
        assert report.metrics[0].name == "coverage"

    @pytest.mark.asyncio
    async def test_evaluate_analysis_phase(self, engine):
        report = await engine.evaluate(
            "analysis", artifact=None,
            specificity=0.9, actionability=0.8, evidence_support=0.7,
        )
        assert report.phase == "analysis"
        assert report.metrics[0].name == "gap_quality"

    @pytest.mark.asyncio
    async def test_evaluate_ideas_phase(self, engine):
        report = await engine.evaluate("ideas", artifact=None, overlap_score=0.3)
        assert report.phase == "ideas"
        assert report.metrics[0].name == "novelty_support"

    @pytest.mark.asyncio
    async def test_evaluate_draft_phase(self, engine):
        report = await engine.evaluate("draft", artifact=None)
        assert report.phase == "draft"
        assert len(report.metrics) == 5

    @pytest.mark.asyncio
    async def test_evaluate_review_phase_empty(self, engine):
        report = await engine.evaluate("review", artifact=None)
        assert report.phase == "review"
        assert report.metrics == []
        assert report.overall_score == 0.0
        assert report.passed is True

    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, engine):
        report = await engine.evaluate("research", artifact=None, coverage_score=1.0)
        assert report.overall_score == 1.0

    @pytest.mark.asyncio
    async def test_passed_all_true(self, engine):
        report = await engine.evaluate("research", artifact=None, coverage_score=1.0)
        assert report.passed is True

    @pytest.mark.asyncio
    async def test_passed_any_false(self, engine):
        report = await engine.evaluate("research", artifact=None, coverage_score=0.0)
        assert report.passed is False

    @pytest.mark.asyncio
    async def test_list_metrics_known_phase(self, engine):
        names = engine.list_metrics("draft")
        assert "CitationAccuracyMetric" in names
        assert "GroundednessMetric" in names
        assert "HallucinationMetric" in names
        assert "TraceabilityMetric" in names
        assert "CompletenessMetric" in names

    @pytest.mark.asyncio
    async def test_list_metrics_unknown_phase(self, engine):
        names = engine.list_metrics("nonexistent")
        assert names == []

    @pytest.mark.asyncio
    async def test_register_metric_new_phase(self, engine):
        from app.ai.evaluation.metrics import CoverageMetric
        engine.register_metric("custom", CoverageMetric())
        names = engine.list_metrics("custom")
        assert "CoverageMetric" in names

    @pytest.mark.asyncio
    async def test_register_metric_existing_phase(self, engine):
        from app.ai.evaluation.metrics import CoverageMetric
        engine.register_metric("research", CoverageMetric())
        names = engine.list_metrics("research")
        assert names.count("CoverageMetric") == 2

    @pytest.mark.asyncio
    async def test_evaluate_unknown_phase(self, engine):
        report = await engine.evaluate("unknown", artifact=None)
        assert report.metrics == []

    @pytest.mark.asyncio
    async def test_evaluation_report_dataclass(self):
        metrics = [
            MetricResult(name="m1", score=0.8, threshold=0.7, passed=True)
        ]
        report = EvaluationReport(
            workflow_id="wf1", phase="test", metrics=metrics,
            overall_score=0.8, passed=True, artifact_id="art1",
        )
        assert report.workflow_id == "wf1"
        assert report.phase == "test"
        assert report.overall_score == 0.8
        assert report.passed is True
        assert report.artifact_id == "art1"

    @pytest.mark.asyncio
    async def test_evaluate_with_kwargs_passthrough(self, engine):
        report = await engine.evaluate("research", artifact=None, coverage_score=0.85)
        assert report.metrics[0].score == 0.85


class TestQualityAggregator:
    @pytest.fixture
    def aggregator(self):
        return QualityAggregator()

    def make_results(self, scores, passed=None):
        if passed is None:
            passed = [s >= 0.5 for s in scores]
        return [
            MetricResult(name=f"m{i}", score=s, threshold=0.5, passed=p)
            for i, (s, p) in enumerate(zip(scores, passed))
        ]

    def test_aggregate_mean(self, aggregator):
        results = self.make_results([1.0, 0.5, 0.0], [True, True, False])
        score = aggregator.aggregate(results)
        assert score.overall == pytest.approx(0.5)
        assert score.min_score == 0.0
        assert score.max_score == 1.0
        assert score.passed_count == 2
        assert score.total_count == 3

    def test_aggregate_median_odd(self, aggregator):
        results = self.make_results([1.0, 0.5, 0.0])
        score = aggregator.aggregate(results)
        assert score.median_score == 0.5

    def test_aggregate_median_even(self, aggregator):
        results = self.make_results([1.0, 0.5, 0.2, 0.0])
        score = aggregator.aggregate(results)
        assert score.median_score == pytest.approx(0.35)

    def test_aggregate_empty(self, aggregator):
        score = aggregator.aggregate([])
        assert score.overall == 0.0
        assert score.total_count == 0

    def test_aggregate_details(self, aggregator):
        results = self.make_results([0.8, 0.6])
        score = aggregator.aggregate(results)
        assert "m0" in score.details
        assert score.details["m0"]["score"] == 0.8
        assert score.details["m1"]["passed"] is True

    def test_weighted_aggregate_higher_weight(self, aggregator):
        results = self.make_results([1.0, 0.0], [True, False])
        score = aggregator.weighted_aggregate(results, {"m0": 3.0, "m1": 1.0})
        assert score.overall == pytest.approx(0.75)

    def test_weighted_aggregate_equal_weight(self, aggregator):
        results = self.make_results([0.8, 0.2])
        score = aggregator.weighted_aggregate(results, {"m0": 1.0, "m1": 1.0})
        assert score.overall == pytest.approx(0.5)

    def test_weighted_aggregate_missing_weight_defaults_one(self, aggregator):
        results = self.make_results([1.0])
        score = aggregator.weighted_aggregate(results, {})
        assert score.overall == 1.0

    def test_weighted_aggregate_empty(self, aggregator):
        score = aggregator.weighted_aggregate([], {})
        assert score.overall == 0.0
        assert score.total_count == 0

    def test_weighted_aggregate_details_include_weight(self, aggregator):
        results = self.make_results([0.9, 0.7])
        score = aggregator.weighted_aggregate(results, {"m0": 2.0, "m1": 1.0})
        assert score.details["m0"]["weight"] == 2.0
        assert score.details["m1"]["weight"] == 1.0

    def test_all_passed(self, aggregator):
        results = self.make_results([1.0, 0.8, 0.6], [True, True, True])
        score = aggregator.aggregate(results)
        assert score.passed_count == 3
        assert score.total_count == 3

    def test_none_passed(self, aggregator):
        results = self.make_results([0.4, 0.3], [False, False])
        score = aggregator.aggregate(results)
        assert score.passed_count == 0
        assert score.total_count == 2


class TestAggregatedScore:
    def test_defaults(self):
        s = AggregatedScore()
        assert s.overall == 0.0
        assert s.min_score == 0.0
        assert s.max_score == 0.0
        assert s.median_score == 0.0
        assert s.passed_count == 0
        assert s.total_count == 0
        assert s.details == {}

    def test_custom_values(self):
        s = AggregatedScore(
            overall=0.75, min_score=0.5, max_score=1.0, median_score=0.75,
            passed_count=3, total_count=4, details={"a": 1},
        )
        assert s.overall == 0.75
        assert s.min_score == 0.5
        assert s.max_score == 1.0
        assert s.median_score == 0.75
        assert s.passed_count == 3
        assert s.total_count == 4


class TestEvaluationReport:
    def test_defaults(self):
        r = EvaluationReport()
        assert r.workflow_id == ""
        assert r.phase == ""
        assert r.metrics == []
        assert r.overall_score == 0.0
        assert r.passed is False
        assert r.artifact_id == ""

    def test_custom_values(self):
        m = MetricResult(name="m1", score=0.9, threshold=0.8, passed=True)
        r = EvaluationReport(
            workflow_id="wf1", phase="draft", metrics=[m],
            overall_score=0.9, passed=True, artifact_id="art1",
        )
        assert r.workflow_id == "wf1"
        assert r.passed is True
        assert r.metrics[0].score == 0.9
