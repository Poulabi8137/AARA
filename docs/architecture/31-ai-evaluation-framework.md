# Document 31 — AI Evaluation Framework

## Purpose

Every generated artifact in AARA is evaluated against objective quality metrics. This ensures that agent outputs are grounded, accurate, and useful — not just plausible-sounding text.

## Evaluation Architecture

```
Workflow Phase → Agent Output → Evaluation Engine → Metric Scores → Quality Report
                                     ↑
                              Metric Definitions
                                  (this doc)
```

## Where Evaluation Occurs

| Phase | Artifact Evaluated | Evaluator | Metrics |
|---|---|---|---|
| Research | PaperCollection | Research Agent (self-check) | Source diversity, dedup rate, coverage |
| Analysis | GapReport | Evaluation Engine | Gap quality, evidence support, theme coherence |
| Ideas | IdeaProposal | Evaluation Engine | Overlap accuracy, feasibility, novelty support |
| Draft | PaperDraft | Review Agent + Evaluation Engine | Citation accuracy, structure, groundedness |
| Review | ReviewReport | Evaluation Engine | Review consistency, severity distribution |
| Final | WorkflowResult | Evaluation Engine (aggregate) | All metrics combined |

## Metric Definitions

### 1. Citation Accuracy

```python
class CitationAccuracyMetric:
    """Measures how many citations in a draft are real, resolvable DOIs."""

    async def evaluate(self, draft: PaperDraft) -> MetricResult:
        total = 0
        valid = 0
        for section in draft.sections:
            for citation in section.citations:
                total += 1
                if citation.doi:
                    result = await self.citation_service.validate(citation.doi)
                    if result.is_valid:
                        valid += 1

        accuracy = valid / max(total, 1)
        return MetricResult(
            name="citation_accuracy",
            score=accuracy,
            threshold=0.9,  # 90% of citations must be valid
            passed=accuracy >= 0.9,
            details=f"{valid}/{total} citations validated",
        )
```

### 2. Groundedness

Measures whether every claim in the draft is supported by at least one retrieved paper.

```python
class GroundednessMetric:
    """Measure: what fraction of claims are supported by citations to retrieved papers."""

    async def evaluate(self, draft: PaperDraft, papers: list[Paper]) -> MetricResult:
        # Use LLM to extract claims per section and check for supporting citations
        total_claims = 0
        supported_claims = 0

        for section in draft.sections:
            prompt = f"""
            Extract all factual claims from this section.
            For each claim, determine if it has an inline citation [@key].
            Section: {section.name}
            Content: {section.content[:2000]}

            Return as JSON: {{"claims": [{{"text": "...", "has_citation": bool}}]}}
            """
            result = await self.llm.extract_structured(prompt, ClaimsSchema)
            for claim in result.claims:
                total_claims += 1
                if claim.has_citation:
                    supported_claims += 1

        groundedness = supported_claims / max(total_claims, 1)
        return MetricResult(
            name="groundedness",
            score=groundedness,
            threshold=0.8,
            passed=groundedness >= 0.8,
            details=f"{supported_claims}/{total_claims} claims have citations",
        )
```

### 3. Hallucination Rate

Measures what fraction of claims cite papers that do not contain the claimed information.

```python
class HallucinationMetric:
    """Estimate hallucination rate by spot-checking claims against source papers."""

    SAMPLE_SIZE = 5  # Number of claims to verify per evaluation

    async def evaluate(self, draft: PaperDraft, papers: list[Paper]) -> MetricResult:
        # Sample claims with citations from the draft
        sampled = []
        for section in draft.sections:
            for citation in section.citations:
                if citation.paper_id and len(sampled) < self.SAMPLE_SIZE:
                    sampled.append((section, citation))

        hallucinations = 0
        for section, citation in sampled:
            paper = next((p for p in papers if p.id == citation.paper_id), None)
            if not paper or not paper.abstract:
                continue

            # Check if the claim context is supported by the paper's abstract
            prompt = f"""
            Claim context: {citation.context}
            Paper abstract: {paper.abstract[:1000]}

            Does the paper support this claim? Answer YES or NO with confidence.
            """
            result = await self.llm.infer(prompt, VerdictSchema)
            if result.verdict == "NO" and result.confidence > 0.8:
                hallucinations += 1

        rate = hallucinations / max(len(sampled), 1)
        return MetricResult(
            name="hallucination_rate",
            score=1.0 - rate,  # Invert so 1.0 = no hallucinations
            threshold=0.95,     # <5% hallucination rate
            passed=rate <= 0.05,
            details=f"{hallucinations}/{len(sampled)} claims potentially hallucinated",
        )
```

### 4. Coverage

Measures whether the retrieved papers adequately cover the research topic's key subtopics.

```python
class CoverageMetric:
    """Measures subtopic coverage across the retrieved paper set."""

    async def evaluate(self, theme: Theme, topic: str) -> MetricResult:
        prompt = f"""
        Research topic: {topic}
        Papers in theme "{theme.name}": {[p.title for p in theme.papers[:10]]}

        What key subtopics of {theme.name} are NOT covered by these papers?
        Rate coverage as 0.0 (no coverage) to 1.0 (complete coverage).
        """
        result = await self.llm.infer(prompt, CoverageSchema)
        return MetricResult(
            name="coverage",
            score=result.coverage_score,
            threshold=0.6,
            passed=result.coverage_score >= 0.6,
            details=f"Coverage: {result.coverage_score:.2f}, Missing: {result.missing_topics}",
        )
```

### 5. Research Gap Quality

```python
class GapQualityMetric:
    """Evaluates whether identified gaps are real, specific, and actionable."""

    async def evaluate(self, gap: ResearchGap, papers: list[Paper]) -> MetricResult:
        prompt = f"""
        Research gap: {gap.description}
        Gap type: {gap.gap_type}
        Supporting evidence: {[p.title for p in gap.evidence[:3]]}

        Rate this gap on:
        1. Specificity (0-1): Is it a specific, well-defined gap?
        2. Actionability (0-1): Can a researcher act on this?
        3. Evidence support (0-1): Is the gap supported by cited papers?
        """
        result = await self.llm.infer(prompt, GapQualitySchema)
        composite = (result.specificity + result.actionability + result.evidence_support) / 3
        return MetricResult(
            name="gap_quality",
            score=composite,
            threshold=0.5,
            passed=composite >= 0.5,
            details=f"S={result.specificity:.2f} A={result.actionability:.2f} E={result.evidence_support:.2f}",
        )
```

### 6. Novelty Support

```python
class NoveltySupportMetric:
    """Measures whether claimed novelty is actually supported by overlap analysis."""

    async def evaluate(self, idea: ResearchIdea) -> MetricResult:
        # If overlap_score is low (<0.2), novelty is well-supported
        # If overlap_score is high (>0.6), the claimed novelty needs scrutiny
        overlap = idea.overlap_score
        novelty_score = 1.0 - overlap

        return MetricResult(
            name="novelty_support",
            score=novelty_score,
            threshold=0.4,
            passed=overlap <= 0.6,  # If overlap > 60%, novelty claim is weak
            details=f"Overlap score: {overlap:.2f}, Implied novelty: {novelty_score:.2f}",
        )
```

### 7. Traceability

```python
class TraceabilityMetric:
    """Measures whether every idea/draft claim can be traced to a source paper."""

    async def evaluate(self, draft: PaperDraft, workflow_id: UUID) -> MetricResult:
        traced = 0
        total_citations = 0

        for section in draft.sections:
            for citation in section.citations:
                total_citations += 1
                # Check if the cited paper exists in the workspace
                paper = await self.db.get(Paper, citation.paper_id)
                if paper and paper.doi:
                    traced += 1

        traceability = traced / max(total_citations, 1)
        return MetricResult(
            name="traceability",
            score=traceability,
            threshold=0.95,
            passed=traceability >= 0.95,
            details=f"{traced}/{total_citations} citations traceable to workspace papers",
        )
```

### 8. Completeness

```python
class CompletenessMetric:
    """Checks that all required sections, metadata, and components are present."""

    REQUIRED_SECTIONS = {"abstract", "introduction", "related_work", "conclusion"}
    MIN_WORDS_PER_SECTION = 100

    async def evaluate(self, draft: PaperDraft) -> MetricResult:
        present = set(s.name for s in draft.sections)
        missing = self.REQUIRED_SECTIONS - present
        short_sections = [s.name for s in draft.sections if s.word_count < self.MIN_WORDS_PER_SECTION]

        completeness = 1.0 - (len(missing) + len(short_sections)) / (len(self.REQUIRED_SECTIONS) + len(draft.sections))
        return MetricResult(
            name="completeness",
            score=max(0.0, completeness),
            threshold=0.8,
            passed=len(missing) == 0 and len(short_sections) == 0,
            details=f"Missing: {missing}, Short sections: {short_sections}",
        )
```

## Evaluation Engine

```python
class EvaluationEngine:
    """Central evaluator. Runs all applicable metrics on a workflow output."""

    def __init__(self):
        self.metrics: dict[str, list[Metric]] = {
            "research": [CoverageMetric()],
            "analysis": [GapQualityMetric()],
            "ideas": [NoveltySupportMetric()],
            "draft": [
                CitationAccuracyMetric(),
                GroundednessMetric(),
                HallucinationMetric(),
                TraceabilityMetric(),
                CompletenessMetric(),
            ],
            "review": [],  # Review Agent's own output; evaluated by its internal scores
        }

    async def evaluate(self, workflow: Workflow, phase: str,
                        artifact: Any) -> EvaluationReport:
        phase_metrics = self.metrics.get(phase, [])
        results = []

        for metric in phase_metrics:
            result = await metric.evaluate(artifact)
            results.append(result)

        overall = sum(r.score for r in results) / max(len(results), 1)

        return EvaluationReport(
            workflow_id=workflow.id,
            phase=phase,
            metrics=results,
            overall_score=overall,
            passed=all(r.passed for r in results),
            artifact_id=artifact.id if hasattr(artifact, "id") else None,
        )
```

## Metrics Summary

| Metric | Range | Threshold | Where Evaluated | Implementation Cost |
|---|---|---|---|---|
| Citation Accuracy | 0-1 | ≥0.90 | Draft (Review Agent) | Free (CrossRef API) |
| Groundedness | 0-1 | ≥0.80 | Draft (Evaluation Engine) | 1 LLM call |
| Hallucination Rate | 0-1 | ≤0.05 | Draft (Evaluation Engine) | ~5 LLM calls (sample) |
| Coverage | 0-1 | ≥0.60 | Analysis (Evaluation Engine) | 1 LLM call per theme |
| Gap Quality | 0-1 | ≥0.50 | Analysis (Evaluation Engine) | 1 LLM call per gap |
| Novelty Support | 0-1 | ≥0.40 | Ideas (Evaluation Engine) | Free (score calculation) |
| Traceability | 0-1 | ≥0.95 | Draft (Evaluation Engine) | Free (DB lookup) |
| Completeness | 0-1 | ≥0.80 | Draft (Evaluation Engine) | Free (schema check) |

## Integration

Evaluation runs automatically as the final step of each workflow phase. Results are stored in `evaluation_reports` and displayed on the frontend Evaluation Dashboard.

```
Workflow Phase Complete → EvaluationEngine.evaluate() → Store in PostgreSQL
                                                              ↓
                                                      Frontend Dashboard
                                                              ↓
                                              User sees: Pass/Fail per metric + scores
```
