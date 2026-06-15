# Research Quality Evaluation Framework

## Overview

AARA includes a structured evaluation framework for measuring research quality across multiple dimensions. The framework is in `backend/app/evaluation/benchmark_scenarios.py`.

## Benchmark Scenarios

| Scenario | Domain | Expected Subtopics | Validation Rules |
|----------|--------|-------------------|------------------|
| AI Ethics & Transparency | AI Ethics | 5 | Must mention GDPR, fairness, bias |
| Quantum Machine Learning | Quantum Computing | 4 | Keyword coverage |
| Federated Learning Privacy | Privacy & Security | 4 | 5 expected references |
| Direct Air Capture | Climate Science | 5 | 4 expected references |
| Low-Resource NLP | NLP | 5 | 5 expected references |

## Evaluation Metrics

### Structural Completeness (40 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Has introduction | 10 | Report contains an introduction section |
| Has conclusion | 10 | Report contains a conclusion |
| Has executive summary | 10 | Report has an executive summary |
| Has methodology | 10 | Report describes methodology used |

### Content Quality (30 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Section count | up to 30 | >= min_expected_sections gets full points |

### Citation Quality (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Citation count | up to 15 | Each citation adds 3 points |

### Coverage (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Subtopic coverage | up to 15 | -3 per missing expected subtopic |

## Scoring

- **100**: Perfect report — all sections, all citations, all subtopics covered
- **80-99**: Excellent — minor gaps in coverage
- **60-79**: Good — missing some expected content
- **40-59**: Fair — significant gaps
- **< 40**: Poor — critically incomplete

## Running Evaluations

```python
from app.evaluation.benchmark_scenarios import run_benchmark_suite, evaluate_report

reports = {
    "ai_ethics_transparency": generated_report_dict,
    # ... more reports
}
results = run_benchmark_suite(reports)

for r in results:
    print(f"{r.scenario}: {r.completeness_score}/100 (confidence: {r.confidence})")
    for err in r.errors:
        print(f"  ERROR: {err}")
    for warn in r.warnings:
        print(f"  WARN: {warn}")
```

## Grading Scale for Portfolio

| Grade | Score Range | Interpretation |
|-------|-------------|----------------|
| A+ | 95-100 | Publication quality |
| A | 85-94 | Ready for peer review |
| B+ | 75-84 | Good, minor gaps |
| B | 65-74 | Adequate |
| C | 50-64 | Needs improvement |
| F | < 50 | Major issues |
