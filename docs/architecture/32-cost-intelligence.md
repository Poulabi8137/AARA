# Document 32 — Cost Intelligence Dashboard

## Purpose

Track and display per-workflow and per-user cost metrics to give the researcher visibility into LLM spending, API usage, and performance bottlenecks.

## Collected Metrics

| Metric | Collection Point | Granularity | Display |
|---|---|---|---|
| LLM tokens (input) | Provider Router | Per LLM call | Workflow + User |
| LLM tokens (output) | Provider Router | Per LLM call | Workflow + User |
| Embedding tokens | Embedding Pipeline | Per batch | Workflow |
| API calls (research) | Tool Router | Per external API | Workflow |
| Cost per provider | Provider Router | Per LLM call | Workflow + User + Provider |
| Cost per agent | Supervisor / Agent Runtime | Per agent execution | Workflow |
| Workflow latency | Workflow Engine | Per workflow | Workflow |
| Cache hit ratio | Cost Control Cache | Per cache check | User |
| Vector search latency | Vector Search Service | Per search | Workflow |
| Total workflow cost | Workflow Engine (aggregated) | Per workflow | Workflow |
| Monthly user cost | Aggregation query | Per user | User dashboard |

## Data Collection Architecture

```
Agent or Service → Event Bus → CostMetricsHandler → PostgreSQL (cost_metrics table)
                         ↓
                    Prometheus (real-time gauges)
                         ↓
                    Frontend Dashboard (visualization)
```

### Event-Based Collection

```python
# Events published by each service
class LLMUsageEvent(Event):
    type = "cost.llm_usage"
    workflow_id: UUID
    agent_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: Decimal
    latency_ms: int

class EmbeddingUsageEvent(Event):
    type = "cost.embedding_usage"
    workflow_id: UUID
    provider: str
    model: str
    chunks_embedded: int
    total_tokens: int
    cost_usd: Decimal

class ToolUsageEvent(Event):
    type = "cost.tool_usage"
    workflow_id: UUID
    tool_name: str
    api_calls: int
    cache_hits: int
    latency_ms: int
```

### Cost Storage Schema

```sql
CREATE TABLE cost_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    workflow_id UUID REFERENCES workflows(id),

    -- Time period
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    date DATE GENERATED ALWAYS AS (recorded_at::date) STORED,

    -- LLM costs
    llm_prompt_tokens INT DEFAULT 0,
    llm_completion_tokens INT DEFAULT 0,
    llm_total_tokens INT DEFAULT 0,
    llm_cost_usd DECIMAL(10,6) DEFAULT 0,

    -- Embedding costs
    embedding_tokens INT DEFAULT 0,
    embedding_cost_usd DECIMAL(10,6) DEFAULT 0,

    -- API costs (research APIs are free, tracked for rate limiting)
    api_calls INT DEFAULT 0,
    cache_hits INT DEFAULT 0,

    -- Latency
    total_latency_ms INT DEFAULT 0,
    vector_search_latency_ms INT DEFAULT 0,

    -- Breakdown
    provider_breakdown JSONB DEFAULT '{}',  -- {"openai": 0.002, "gemini": 0.001}
    agent_breakdown JSONB DEFAULT '{}',     -- {"researcher": 0.001, "analyst": 0.002}

    -- Metadata
    cache_hit_ratio DECIMAL(5,4) DEFAULT 0,
    total_cost_usd DECIMAL(10,6) GENERATED ALWAYS AS (llm_cost_usd + embedding_cost_usd) STORED
);

-- Indexes for dashboard queries
CREATE INDEX idx_cost_user_date ON cost_metrics(user_id, date);
CREATE INDEX idx_cost_workflow ON cost_metrics(workflow_id);
CREATE INDEX idx_cost_workspace ON cost_metrics(workspace_id);

-- Monthly aggregation table
CREATE TABLE monthly_cost_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    year_month VARCHAR(7) NOT NULL,  -- "2026-06"
    total_cost_usd DECIMAL(10,2) DEFAULT 0,
    total_workflows INT DEFAULT 0,
    total_llm_calls INT DEFAULT 0,
    total_embedding_calls INT DEFAULT 0,
    provider_breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, year_month)
);
```

## Cost Metrics Handler

```python
class CostMetricsHandler:
    """Listens to cost-related events and persists metrics."""

    async def handle_llm_usage(self, event: LLMUsageEvent, db: AsyncSession):
        await db.execute(
            insert(CostMetric).values(
                user_id=event.user_id,
                workspace_id=event.workspace_id,
                workflow_id=event.workflow_id,
                llm_prompt_tokens=event.prompt_tokens,
                llm_completion_tokens=event.completion_tokens,
                llm_total_tokens=event.total_tokens,
                llm_cost_usd=event.cost_usd,
                total_latency_ms=event.latency_ms,
                provider_breakdown={event.provider: event.cost_usd},
                agent_breakdown={event.agent_id: event.cost_usd},
            )
        )
        await db.commit()
```

## Dashboard API Endpoints

```
# Per-workflow cost detail
GET /api/v1/workflows/{workflow_id}/cost
  → {workflow_id, total_cost, llm_cost, embedding_cost,
     provider_breakdown, agent_breakdown, cache_hit_ratio,
     total_tokens, total_latency_ms}

# Per-user cost summary
GET /api/v1/users/me/cost?from=2026-06-01&to=2026-06-30
  → {total_cost, monthly_budget, budget_remaining,
     workflows_count, avg_cost_per_workflow,
     provider_breakdown: {openai: $X, gemini: $Y, ...}}

# Per-workspace cost
GET /api/v1/workspaces/{workspace_id}/cost
  → {total_cost, workflow_count, avg_cost_per_workflow}

# Active cost (real-time)
GET /api/v1/cost/active
  → {active_workflow_count, estimated_running_cost,
     current_hour_cost, today_cost}
```

## Dashboard UI Specification

```
┌─────────────────────────────────────────────────────────────────┐
│  Cost Dashboard                                                 │
│  ┌──────────────────────────────────────────────────────────────┤
│  │ Monthly Budget: $5.00    Spent: $1.23    Remaining: $3.77  │
│  │ [███████████████████░░░░░░░░░░░░░░░░░░░░░░] 24.6% used     │
│  └──────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┬───────────┬───────────┬───────────┬─────────────┐│
│  │ Workflows │ Avg Cost  │ LLM Calls │ Cache Hit │ Avg Latency ││
│  │    12     │  $0.04    │    187    │   72%     │   4.2 min   ││
│  └───────────┴───────────┴───────────┴───────────┴─────────────┘│
│                                                                 │
│  ┌──── Cost by Provider ──────────────────────────────────────┐ │
│  │ OpenAI:    $0.78  ████████████████████████████░░░░  63%   │ │
│  │ Gemini:    $0.22  ████████░░░░░░░░░░░░░░░░░░░░░░  18%   │ │
│  │ Groq:      $0.12  ████░░░░░░░░░░░░░░░░░░░░░░░░░░  10%   │ │
│  │ Local:     $0.00  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──── Cost by Agent ────────────────────────────────────────┐ │
│  │ Writing:   $0.48  ██████████████████████████░░░░░  39%   │ │
│  │ Analysis:  $0.31  ████████████████░░░░░░░░░░░░░░  25%   │ │
│  │ Research:  $0.22  ███████████░░░░░░░░░░░░░░░░░░░  18%   │ │
│  │ Review:    $0.15  ███████░░░░░░░░░░░░░░░░░░░░░░░  12%   │ │
│  │ Planner:   $0.07  ███░░░░░░░░░░░░░░░░░░░░░░░░░░░   6%   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──── Recent Workflows ──────────────────────────────────────┐ │
│  │ Workflow      Type        Cost     Tokens   Latency  Date │ │
│  │ ────────────────────────────────────────────────────────── │ │
│  │ ViT Survey    lit_review  $0.04    12,340   3m 12s  Jun 22│ │
│  │ GAN Analysis  gap_anlys   $0.02    6,781    1m 45s  Jun 22│ │
│  │ LLM Paper     full_res    $0.12    38,492   8m 30s  Jun 21│ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Budget Enforcement

```python
class BudgetEnforcer:
    """Checks budget limits before allowing expensive operations."""

    async def check_workflow_budget(self, user_id: UUID, estimated_cost: Decimal) -> bool:
        """Return False if user would exceed monthly budget."""
        monthly = await self._get_monthly_cost(user_id)
        user = await self.db.get(User, user_id)
        if monthly + estimated_cost > user.monthly_budget_usd:
            logger.warning(f"User {user_id} budget exceeded: {monthly} + {estimated_cost} > {user.monthly_budget_usd}")
            return False
        return True

    async def check_provider_budget(self, user_id: UUID, provider: str, cost: Decimal) -> bool:
        """Check per-provider budget if configured."""
        limits = await self._get_provider_limits(user_id)
        return limits.get(provider, Decimal("inf")) >= cost
```

## Trade-offs

| Decision | Rationale |
|---|---|
| Cost metrics stored in PostgreSQL (not Prometheus) | Enables per-user/per-workflow queries; Prometheus is for aggregates |
| Event-based collection (not polling) | Zero overhead when no costs to track; natural integration with Event Bus |
| Generated columns for total_cost | Avoids application-level calculation inconsistency |
| Monthly pre-aggregation table | Dashboard queries don't scan millions of rows |
| Per-LLM-call granularity | Enables detailed debugging; aggregation handles dashboard-level queries |
