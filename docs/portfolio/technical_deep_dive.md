# AARA Technical Deep Dive

## Agent Workflow Engine

### State Management
Each agent receives typed state via Pydantic models. The state graph tracks:
- `current_step`: Which agent is active
- `artifacts`: Accumulated outputs (plan, papers, themes, gaps)
- `errors`: Per-step error context for graceful degradation
- `metadata`: LLM provider, timing, token counts

### Planner Agent
```
Input: User query string
Process: LLM call with structured output schema
Output: ResearchPlan with subtopics[], searchQueries[], methodology
```

The planner uses few-shot prompting with 3 example plans. It decomposes complex queries into researchable subtopics and generates targeted search queries for each.

### Retriever Agent
```
Input: ResearchPlan
Process: ChromaDB similarity search + web search (when available)
Output: RankedPaper[] with title, abstract, relevance_score, source_url
```

Implements multi-collection retrieval with configurable top-K and relevance threshold. Deduplication via title similarity (Levenshtein distance).

### Summarizer Agent
```
Input: ResearchPlan + RankedPaper[]
Process: Thematic clustering + LLM synthesis
Output: ThematicSummary[] with theme, key_findings, supporting_papers
```

Groups papers by subtopic, then synthesizes findings per group. Extracts key claims, methodology notes, and supporting citations.

### Gap Analyzer Agent
```
Input: ThematicSummary[]
Process: Structured gap identification with severity classification
Output: ResearchGap[] with description, severity (high/medium/low), confidence, remediation
```

Classification criteria: High severity = core question unanswered, no existing methodology; Medium = partial answers exist but incomplete; Low = incremental improvements possible.

### Report Generator Agent
```
Input: All previous agent outputs
Process: Template-based + LLM-enhanced generation
Output: Final report in requested format (academic/executive/comprehensive)
```

Supports citation formats: APA, MLA, Chicago, BibTeX. Includes automatic contradiction detection (comparing claims across sources) and hallucination scoring (citation-support overlap).

## Security Implementation

### JWT Token Design
- Access token: 15-minute expiry, HMAC-SHA256 signed
- Refresh token: 7-day expiry, single-use (rotated on each refresh)
- Token version: Integer in DB, incremented for global invalidation

### Rate Limiting (Atomic Lua)
```lua
-- Atomic check-and-increment
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
if current > limit then
    return 0  -- rate limited
end
return 1  -- allowed
```

### defense-in-depth
All 4 layers must pass for a request to succeed. If any layer fails, the request is rejected before reaching business logic.

## Observability

### Structured Logging Format
```json
{
  "timestamp": "2026-06-17T10:30:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "correlation_id": "uuid",
  "user_id": "uuid-or-null",
  "method": "POST",
  "path": "/api/agents/run",
  "status": 200,
  "duration_ms": 1234,
  "error": null
}
```

### Prometheus Metrics
All metrics have `app="aara"` and `env` labels. Histograms use `[0.01, 0.05, 0.1, 0.5, 1, 2.5, 5, 10]` buckets.

## Performance Characteristics

| Operation | p50 | p95 | p99 |
|-----------|-----|-----|-----|
| Auth (login) | 45ms | 120ms | 200ms |
| Agent workflow | 8.2s | 15s | 22s |
| DB query | 3ms | 15ms | 45ms |
| LLM call | 1.2s | 3.5s | 6s |
| File upload | 50ms | 200ms | 500ms |
