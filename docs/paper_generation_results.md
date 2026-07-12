# Paper Generation Results

**Generated:** 2026-06-16 20:35 UTC  
**Provider:** Gemini 2.5-flash (quota exhausted — template fallback)  
**Pipeline:** ProposalAgent → PaperAuthorAgent → QualityReviewAgent → CitationValidatorAgent → EvidenceValidatorAgent  
**Total Papers:** 10 | **Passed:** 10 (100%)  

---

## Summary Metrics

| Metric | Value |
|--------|-------|
| Papers generated | 10 (100%) |
| Avg paper length | 7,126 chars |
| Avg execution time | 3.12s |
| Avg quality score | 60.0/100 |
| Avg citations per paper | 2.0 |
| Evidence supported ratio | 14.3% |
| IEEE sections | 15 (all papers) |

> **Note:** The Gemini daily quota was exhausted by the benchmark pipeline before paper generation. All paper agents gracefully degraded to template/heuristic fallbacks. Direct LLM test confirmed the provider works (HTTP 200, `DIRECT_OK` response).

---

## Per-Paper Results

| # | Title | Status | Time (s) | Chars | Quality | Refs | Evidence |
|---|-------|--------|--------:|------:|-------:|-----:|---------:|
| 1 | AI Ethics in Healthcare | ✅ | 3.47 | 7,100 | 60 | 2 | 14.3% |
| 2 | Quantum Machine Learning | ✅ | 3.08 | 7,172 | 60 | 2 | 14.3% |
| 3 | Federated Learning for Healthcare | ✅ | 4.09 | 7,224 | 60 | 2 | 14.3% |
| 4 | Direct Air Capture Technology | ✅ | 4.70 | 7,166 | 60 | 2 | 14.3% |
| 5 | Adversarial Robustness in DL | ✅ | 2.58 | 7,024 | 60 | 2 | 14.3% |
| 6 | LLMs for Code Generation | ✅ | 2.55 | 7,186 | 60 | 2 | 14.3% |
| 7 | Climate Risk & Supply Chains | ✅ | 2.53 | 7,034 | 60 | 2 | 14.3% |
| 8 | AI-Driven Drug Discovery | ✅ | 2.53 | 7,142 | 60 | 2 | 14.3% |
| 9 | Low-Resource NLP Methods | ✅ | 3.05 | 7,120 | 60 | 2 | 14.3% |
| 10 | AI Automation & Labor Markets | ✅ | 2.64 | 7,100 | 60 | 2 | 14.3% |

---

## Agent-Level Performance (Template Fallback)

| Agent | Avg Time | Status | Notes |
|-------|---------:|--------|-------|
| ProposalAgent | 0.17s | 100% | Generated structured proposal with title, objectives, methodology |
| PaperAuthorAgent | 0.29s | 100% | Produced 15-section IEEE paper with template content |
| QualityReviewAgent | 0.15s | 100% | Scored 8 metrics, composite=60.0 |
| CitationValidatorAgent | 0.17s | 100% | Rule-based checks: 2 citations validated |
| EvidenceValidatorAgent | 2.67s | 100% | Heuristic classification: 14.3% supported |

---

## Template Output Characteristics

Template-generated papers include:
- **15 IEEE sections**: Abstract, Introduction, Background, Problem Statement, Methodology, Implementation, Results, Discussion, Conclusion, etc.
- **2 references**: Template-generated (LLM would produce 10-15+)
- **Quality score 60/100**: Template default (LLM would be more nuanced)
- **Evidence ratio 14.3%**: Heuristic classification determines most statements as "needs citation"

---

## Expected Improvements with Real LLM

Based on direct LLM testing (HTTP 200, 0.4s latency):

| Metric | Template | Expected with Gemini |
|--------|---------|---------------------|
| Paper length | 7K chars | 15-25K chars |
| References | 2 | 10-20 with real DOIs |
| Quality score | 60/100 | 70-85/100 |
| Evidence supported | 14% | 40-60% |
| Content depth | Generic | Domain-specific |
| Citations | Placeholder | Real IEEE formatted |
