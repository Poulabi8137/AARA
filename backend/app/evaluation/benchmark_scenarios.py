"""Benchmark scenarios for evaluating research quality across dimensions.

Each scenario is a structured research query with known expected outputs,
allowing objective measurement of citation accuracy, completeness, and
factual consistency.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BenchmarkScenario:
    name: str
    query: str
    objective: str
    domain: str
    expected_subtopics: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    known_contradictions: list[str] = field(default_factory=list)
    min_expected_sections: int = 3
    expected_references: int = 3
    validation_rules: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationResult:
    scenario: str
    section_count: int
    reference_count: int
    citation_count: int
    has_citations: bool
    has_introduction: bool
    has_conclusion: bool
    has_executive_summary: bool
    has_methodology: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    completeness_score: float = 0.0


BENCHMARK_SCENARIOS = [
    BenchmarkScenario(
        name="ai_ethics_transparency",
        query="Ethical considerations in AI transparency and explainability",
        objective="Identify key ethical frameworks, technical approaches for explainable AI, and regulatory implications for deploying transparent AI systems in healthcare.",
        domain="AI Ethics",
        expected_subtopics=[
            "explainability",
            "transparency",
            "fairness",
            "accountability",
            "healthcare",
        ],
        expected_keywords=[
            "XAI", "explainable", "transparency", "ethics", "GDPR",
            "fairness", "accountability", "interpretability",
        ],
        known_contradictions=[
            "Accuracy vs interpretability trade-off",
            "Regulatory compliance vs innovation speed",
        ],
        min_expected_sections=4,
        expected_references=5,
        validation_rules={
            "must_mention": ["GDPR", "fairness", "bias"],
            "must_not_contain": [],
        },
    ),
    BenchmarkScenario(
        name="quantum_machine_learning",
        query="Quantum machine learning: current capabilities and limitations",
        objective="Survey the state of quantum machine learning algorithms, identify which classical ML problems show quantum advantage, and analyze hardware limitations.",
        domain="Quantum Computing",
        expected_subtopics=[
            "quantum algorithms",
            "variational circuits",
            "quantum advantage",
            "hardware limitations",
        ],
        expected_keywords=[
            "quantum", "variational", "VQE", "QAOA", "NISQ",
            "superposition", "entanglement", "error correction",
        ],
        min_expected_sections=3,
        expected_references=4,
    ),
    BenchmarkScenario(
        name="federated_learning_privacy",
        query="Privacy-preserving machine learning: federated learning and differential privacy",
        objective="Analyze federated learning architectures, differential privacy guarantees, and the privacy-utility trade-off in distributed ML systems.",
        domain="Privacy & Security",
        expected_subtopics=[
            "federated learning",
            "differential privacy",
            "privacy-utility trade-off",
            "secure aggregation",
        ],
        expected_keywords=[
            "federated", "privacy", "differential", "secure aggregation",
            "communication efficiency", "non-iid", "gradient leakage",
        ],
        known_contradictions=[
            "Privacy guarantees vs model accuracy",
            "Communication cost vs convergence speed",
        ],
        min_expected_sections=4,
        expected_references=5,
    ),
    BenchmarkScenario(
        name="climate_carbon_capture",
        query="Direct air capture technologies for climate change mitigation",
        objective="Evaluate the technological readiness, energy requirements, and economic viability of direct air capture (DAC) systems for atmospheric CO2 removal.",
        domain="Climate Science",
        expected_subtopics=[
            "direct air capture",
            "carbon removal",
            "energy requirements",
            "economic viability",
            "policy frameworks",
        ],
        expected_keywords=[
            "DAC", "carbon capture", "CO2 removal", "negative emissions",
            "sorbent", "thermodynamic", "levelized cost",
        ],
        min_expected_sections=3,
        expected_references=4,
    ),
    BenchmarkScenario(
        name="nlp_low_resource",
        query="Low-resource natural language processing: techniques and challenges",
        objective="Survey transfer learning, data augmentation, and cross-lingual methods for NLP in languages with limited annotated data.",
        domain="Natural Language Processing",
        expected_subtopics=[
            "transfer learning",
            "data augmentation",
            "cross-lingual learning",
            "multilingual models",
            "evaluation",
        ],
        expected_keywords=[
            "low-resource", "transfer learning", "cross-lingual",
            "multilingual BERT", "data augmentation", "zero-shot",
            "few-shot", "unsupervised",
        ],
        min_expected_sections=4,
        expected_references=5,
    ),
]


def evaluate_report(scenario: BenchmarkScenario, report: dict[str, Any]) -> EvaluationResult:
    """Evaluate a generated report against a benchmark scenario."""
    result = EvaluationResult(
        scenario=scenario.name,
        section_count=0,
        reference_count=0,
        citation_count=0,
        has_citations=False,
        has_introduction=False,
        has_conclusion=False,
        has_executive_summary=False,
        has_methodology=False,
    )

    sections = report.get("sections", [])
    references = report.get("references", [])
    citations_flat = report.get("citations", [])

    result.section_count = len(sections)
    result.reference_count = len(references)

    # Count citations across all sections
    citation_count = len(citations_flat)
    for s in sections:
        citation_count += len(s.get("citations", []))
    result.citation_count = citation_count
    result.has_citations = citation_count > 0

    # Check structural completeness
    result.has_introduction = bool(report.get("introduction", ""))
    result.has_conclusion = bool(report.get("conclusion", ""))
    result.has_executive_summary = bool(report.get("executive_summary", ""))
    result.has_methodology = bool(report.get("methodology", ""))

    # Section count validation
    if len(sections) < scenario.min_expected_sections:
        result.errors.append(
            f"Expected >= {scenario.min_expected_sections} sections, got {len(sections)}"
        )

    # Reference count validation
    if len(references) < scenario.expected_references:
        result.warnings.append(
            f"Expected >= {scenario.expected_references} references, got {len(references)}"
        )

    # Subtopic coverage
    covered = set()
    for s in sections:
        title = s.get("title", s.get("subtopic", "")).lower()
        summary = s.get("summary", "").lower()
        for subtopic in scenario.expected_subtopics:
            if subtopic.lower() in title or subtopic.lower() in summary:
                covered.add(subtopic.lower())

    missing_subtopics = set(scenario.expected_subtopics) - covered
    if missing_subtopics:
        result.warnings.append(f"Missing subtopics: {', '.join(sorted(missing_subtopics))}")

    # Keyword presence
    all_text = " ".join([
        report.get("executive_summary", ""),
        report.get("introduction", ""),
        report.get("conclusion", ""),
        " ".join(s.get("summary", "") for s in sections),
    ]).lower()

    for kw in scenario.expected_keywords:
        if kw.lower() not in all_text:
            result.warnings.append(f"Keyword not found: '{kw}'")

    # Validation rules
    rules = scenario.validation_rules
    if "must_mention" in rules:
        for term in rules["must_mention"]:
            if term.lower() not in all_text:
                result.warnings.append(f"Required term missing: '{term}'")

    # Compute scores
    structural_score = (
        sum([result.has_introduction, result.has_conclusion,
             result.has_executive_summary, result.has_methodology]) / 4.0
    ) * 40

    content_score = min(30, (result.section_count / max(scenario.min_expected_sections, 1)) * 30)
    citation_score = min(15, result.citation_count * 3)
    coverage_score = max(0, 15 - len(missing_subtopics) * 3)

    result.completeness_score = round(structural_score + content_score + citation_score + coverage_score, 1)
    result.confidence = round(
        (result.completeness_score / 100.0) * (1.0 - len(result.errors) * 0.1),
        2,
    )

    return result


def run_benchmark_suite(reports: dict[str, dict[str, Any]]) -> list[EvaluationResult]:
    """Run the full benchmark suite against a set of generated reports."""
    results = []
    for scenario in BENCHMARK_SCENARIOS:
        report = reports.get(scenario.name, {})
        if not report:
            result = EvaluationResult(
                scenario=scenario.name,
                section_count=0,
                reference_count=0,
                citation_count=0,
                has_citations=False,
                has_introduction=False,
                has_conclusion=False,
                has_executive_summary=False,
                has_methodology=False,
                errors=["No report generated"],
            )
        else:
            result = evaluate_report(scenario, report)
        results.append(result)
    return results
