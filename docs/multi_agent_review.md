# Multi-Agent Orchestration Review

## Agent System Architecture

```
                    ┌─────────────┐
                    │   Planner    │
                    │  (LLM-based) │
                    └──────┬──────┘
                           │ Research plan (JSON)
                           ▼
                    ┌─────────────┐
                    │  Retriever   │
                    │ (Algorithmic)│
                    └──────┬──────┘
                           │ Evidence bundles
                           ▼
                    ┌─────────────┐
                    │  Summarizer  │
                    │ (Algorithmic)│
                    └──────┬──────┘
                           │ Section summaries
                           ▼
                    ┌─────────────┐
                    │ Gap Detector │
                    │ (Algorithmic)│
                    └──────┬──────┘
                           │ Gaps + coverage
                           ▼
                    ┌─────────────┐
                    │    Human     │
                    │   Approval   │  ← Broken: never pauses
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         "approved"   "rerun"      "rejected"
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Report   │  │  Planner │  │  Report   │
        │ Generator │  │ (retry)  │  │ Generator │
        └────┬─────┘  └──────────┘  └────┬─────┘
             │                            │
             ▼                            ▼
           "complete"               "complete"
```

## Agent Coordination Analysis

### Data Flow

| Transition | Data Format | Status |
|-----------|-------------|--------|
| Planner → Retriever | JSON dict with search_queries, subtopics | ✅ Works |
| Retriever → Summarizer | List of evidence bundles with content, source, chunk_id | ✅ Works (may include simulated data) |
| Summarizer → Gap Detector | List of SectionSummary dicts | ✅ Works (summaries are shallow) |
| Gap Detector → Human Approval | List of gap dicts | ✅ Works |
| Human Approval → Report Generator | State dict with gaps + summaries | ❌ Never pauses — always proceeds |

### Error Handling

**Every node** follows the same flawed pattern:

```python
result = await agent.run(state)
if not result.success:
    logger.warning("Agent failed")  # ← Only logs, doesn't stop
state["status"] = "X_complete"       # ← Overrides failure
```

This means:
- If Planner fails → Retrieval runs on empty plan → garbage in, garbage out
- If Retrieval fails → Summarizer runs on empty bundles → fallback triggered
- If Summarizer fails → Gap Detector runs on empty summaries → trivial gaps
- **Error is never propagated to the orchestrator**

### Retry Logic

`_should_continue()` in `research_graph.py` checks `state.get("errors", [])`:
- Errors are never added to state by any node
- Even if they were, retry routes back to Planner/Retrieval AFTER all downstream nodes have executed
- **Retry mechanism is completely non-functional**

## Recommendations

### Immediate (Can be done now)

1. **Fix error propagation**: Have each node append errors to `state["errors"]` and set `state["status"] = "failed"` when `result.success` is False
2. **Add workflow-level timeout**: Prevent hung agents from blocking the graph
3. **Label simulated data clearly**: Already done — changed `[mock]` to `[SIMULATED]`

### Short-term (Requires LLM integration)

4. **Make Summarizer call an LLM**: Pass evidence + system prompt to generate real summaries
5. **Make Gap Detector call an LLM**: Use LLM to identify genuine knowledge gaps
6. **Make Report Generator call an LLM**: Generate fluent prose, not template strings

### Architectural

7. **Fix human approval**: Use LangGraph `interrupt()` or `NodeInterrupt` to pause graph execution
8. **Add proper retry**: Clear downstream state before retrying from Planner/Retrieval
9. **Add agent timeout**: Wrap `arun()` in `asyncio.wait_for()` with configurable timeout
