# Document 05 — ER Diagram

```mermaid
erDiagram
    USERS ||--o{ WORKSPACES : owns
    USERS ||--o{ WORKSPACE_MEMBERS : member_of
    USERS ||--o{ USER_PREFERENCES : "configures"
    USERS ||--o{ USER_API_KEYS : manages
    USERS ||--o{ AUDIT_LOGS : performs
    USERS ||--o{ WORKFLOWS : initiates
    USERS ||--o{ COST_METRICS : accrues
    USERS ||--o{ MONTHLY_COST_SUMMARY : summarizes

    WORKSPACES ||--o{ WORKSPACE_MEMBERS : has
    WORKSPACES ||--o{ WORKSPACE_SETTINGS : "configured_by"
    WORKSPACES ||--o{ PAPERS : contains
    WORKSPACES ||--o{ WORKFLOWS : runs
    WORKSPACES ||--o{ ANALYSES : stores
    WORKSPACES ||--o{ IDEAS : generates
    WORKSPACES ||--o{ DRAFTS : produces

    PAPERS ||--o{ PAPER_AUTHORS : "authored_by"
    PAPERS ||--o{ CITATIONS : "cited_by"
    PAPERS ||--o{ PAPER_REFERENCES : references
    PAPERS ||--o{ PAPER_CHUNKS : "chunked_into"
    PAPERS ||--o{ PAPER_EMBEDDINGS : "embedded_as"

    AUTHORS ||--o{ PAPER_AUTHORS : "appears_in"

    PAPER_CHUNKS ||--o{ PAPER_EMBEDDINGS : "vectorized_as"

    WORKFLOWS ||--o{ WORKFLOW_STEPS : "composed_of"
    WORKFLOWS ||--o{ AGENT_STATES : tracks
    WORKFLOWS ||--o{ AGENT_EXECUTION_LOGS : logs
    WORKFLOWS ||--o{ APPROVAL_CHECKPOINTS : requires
    WORKFLOWS ||--o{ EVALUATION_REPORTS : "evaluated_by"
    WORKFLOWS ||--o{ COST_METRICS : "cost_of"

    WORKFLOW_STEPS ||--o{ APPROVAL_CHECKPOINTS : "may_require"

    DRAFTS ||--o{ DRAFT_CITATIONS : cites

    PAPERS ||--o{ DRAFT_CITATIONS : "referenced_in"
```

## Entity Summary

| Entity | Type | Description |
|---|---|---|
| users | Core | User accounts synced with Supabase Auth |
| workspaces | Core | Research topic containers |
| workspace_members | Join | User-workspace membership with role |
| workspace_settings | Extension | Per-workspace configuration |
| papers | Core | Research papers (imported or uploaded) |
| authors | Core | Paper authors (deduplicated globally) |
| paper_authors | Join | Paper-author relationship with ordering |
| citations | Detail | Papers cited BY a paper |
| paper_references | Detail | References contained IN a paper |
| paper_chunks | Detail | Text chunks for embedding |
| paper_embeddings | Detail | Vector embeddings (per model) |
| workflows | Core | Research workflow executions |
| workflow_steps | Detail | Individual agent steps in a workflow |
| agent_states | Detail | Per-agent ReAct state persistence for crash recovery |
| agent_execution_logs | Audit | Per-agent execution telemetry |
| approval_checkpoints | Detail | Human-in-the-loop pause points |
| analyses | Detail | Generated analysis reports |
| ideas | Detail | Generated research ideas |
| drafts | Core | Generated paper drafts |
| draft_citations | Detail | Citations within a draft |
| evaluation_reports | Detail | Quality evaluation metrics |
| audit_logs | Audit | Security and action audit trail |
| user_preferences | Extension | User-level settings |
| user_api_keys | Detail | Encrypted LLM provider API keys |
| global_memory | Detail | Cross-workspace persistent memory |
| cost_metrics | Detail | Per-workflow cost and usage telemetry |
| monthly_cost_summary | Summary | Monthly cost aggregation per user |
