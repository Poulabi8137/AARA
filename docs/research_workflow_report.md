# Research Workflow Report

## End-to-End Flow

```
User Query → Planner Agent → Retrieval Agent → Summarizer Agent → Gap Detection → Human Approval → Report Generator → Final Report
```

## Step-by-Step Analysis

### 1. Planner Agent (✅ Works — Actually calls LLM)

**Input**: `query`, `objective`, `project_id`
**Output**: JSON research plan with `research_goal`, `research_questions`, `keywords`, `search_queries`, `subtopics`, `methodology`

**How it works**: Sends prompt to configured LLM (OpenAI/Gemini/Mock). Retries up to 3 times with JSON repair. Falls back to template-based plan on failure.

**LLM**: ✅ YES — `await self.llm.generate(prompt=..., system_prompt=...)`

**Issues**: None critical.

### 2. Retrieval Agent (⚠️ Partially works)

**Input**: Planner output (queries, subtopics)
**Output**: Bundles of evidence chunks grouped by subtopic

**How it works**: Runs `multi_collection_search` against ChromaDB for each search query. Ranks results by relevance. Deduplicates. Groups by subtopic.

**LLM**: ❌ NO — purely algorithmic

**Issues**:
- Returns mock data when ChromaDB returns empty (now labeled `[SIMULATED]`)
- Max 8 queries — additional queries silently truncated
- Subtopic matching is naive word overlap

### 3. Summarizer Agent (❌ Broken — Doesn't summarize)

**Input**: Retrieved evidence bundles
**Output**: Section summaries with key findings, citations, contradictions

**How it works**: Extracts keywords via regex. Finds sentences containing keywords. Builds citations by word overlap. Generates "executive summary" via string template interpolation.

**LLM**: ❌ NO

**Critical Bugs**:
- `build_citation_index(evidence)` called but return value discarded
- `compute_evidence_utilization()` called with hardcoded `0` and `[]`
- Executive summary is a concatenated template: `"Analysis of {subtopic} reveals key findings including {findings[0]}"`
- Contradiction detection only compares first 2 evidence chunks
- No actual NLP or LLM summarization

### 4. Gap Detection Agent (⚠️ Limited)

**Input**: Summaries + planner output
**Output**: Gap analysis with severity, coverage metrics

**How it works**: Counts citations per subtopic. Checks if planned subtopics appear in summaries via token overlap. Detects contradictions.

**LLM**: ❌ NO

**Issues**:
- Token-overlap coverage mapping produces false positives
- `_detect_contradictions()` has a `pass` stub (line 161) — if no contradictions found, no gap is raised

### 5. Human Approval (❌ Broken — Never pauses)

**Input**: Gap analysis results
**Output**: Approval record in database

**How it works**: Creates a `HumanApproval` record with `PENDING` status. Returns immediately.

**Critical Bugs**:
- No `interrupt()` or `NodeInterrupt` call — graph never pauses
- `_route_from_approval()` checks `state["approval_status"]` = `"awaiting_approval"` which falls through to `return "approved"`
- **Human approval is entirely cosmetic**

### 6. Report Generator Agent (⚠️ Template-based)

**Input**: Summaries + gaps + planner
**Output**: `ResearchReport` with sections, references, conclusion

**How it works**: Assembles report from pre-written templates. Executive summary, introduction, methodology, conclusion are all string interpolation.

**LLM**: ❌ NO

**Issues**:
- "Executive summary" is assembled from hardcoded templates
- Fallback report may fail its own validation (< 50 chars for short queries)
- `build_citation_list()` return value discarded

## LLM Usage Summary

| Agent | Calls LLM? | What it does instead |
|-------|-----------|---------------------|
| Planner | ✅ YES | Generates research plan |
| Retriever | ❌ | ChromaDB similarity search + ranking |
| Summarizer | ❌ | Keyword extraction + template |
| Gap Detector | ❌ | Citation counting + token overlap |
| Report Generator | ❌ | Template concatenation |

## Workflow Health

| Aspect | Status |
|--------|--------|
| Graph topology (nodes → edges) | ✅ Correct |
| State passing between nodes | ✅ Works |
| Error handling (failures) | ❌ Silently ignored |
| Human approval | ❌ Never pauses |
| Retry logic | ❌ Dead code |
| LLM usage (beyond Planner) | ❌ 4/5 agents don't use LLM |
