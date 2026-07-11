# Document 14 — Agent Interaction Diagrams

## Agent Communication Model

All agents communicate **exclusively through the Supervisor Agent**. No agent directly calls another. This ensures:
- **Loose coupling**: Replace any agent without affecting others
- **Observability**: Supervisor logs every message
- **Retry capability**: Central retry control
- **Audit trail**: Every interaction is captured

```
Supervisor
  ├──[command]──→ Planning Agent
  ├──[command]──→ Research Agent
  ├──[command]──→ Analysis Agent
  ├──[command]──→ Idea Generation Agent
  ├──[command]──→ Writing Agent
  └──[command]──→ Review Agent

Each agent ──[result]──→ Supervisor (only)
```

## Full Workflow Sequence

```mermaid
sequenceDiagram
    participant User
    participant SUP as Supervisor Agent
    participant PLAN as Planning Agent
    participant RES as Research Agent
    participant TOOL as Tool Router
    participant ANA as Analysis Agent
    participant IDEA as Idea Generation Agent
    participant WRI as Writing Agent
    participant REV as Review Agent

    User->>SUP: Submit query + workspace_id

    SUP->>PLAN: execute(query)
    Note over PLAN: ReAct: Plan → Reason → Validate
    PLAN-->>SUP: ExecutionPlan

    Note over SUP: Phase 1: Research

    SUP->>RES: execute(SearchQuery)

    Note over RES: ReAct Loop
    RES->>TOOL: semantic_scholar.search(q)
    TOOL-->>RES: Papers
    RES->>TOOL: arxiv.search(q)
    TOOL-->>RES: Papers
    Note over RES: Reflect → Refine → Validate
    RES-->>SUP: PaperCollection

    Note over SUP: CHECKPOINT 1 — User reviews papers

    SUP->>User: checkpoint.awaiting_approval
    User-->>SUP: approve

    Note over SUP: Phase 2: Analysis

    SUP->>ANA: execute(Papers + Topic)
    Note over ANA: ReAct Loop
    ANA->>TOOL: qdrant.similarity_search()
    TOOL-->>ANA: Clusters
    ANA-->>SUP: AnalysisReport

    Note over SUP: CHECKPOINT 2 — User reviews analysis

    SUP->>User: checkpoint.awaiting_approval
    User-->>SUP: approve

    Note over SUP: Phase 3: Idea Generation

    SUP->>IDEA: execute(AnalysisReport)
    IDEA->>TOOL: qdrant.overlap_analysis()
    TOOL-->>IDEA: Overlap scores
    IDEA-->>SUP: IdeaProposal

    Note over SUP: CHECKPOINT 3 — User selects ideas

    SUP->>User: checkpoint.awaiting_approval
    User-->>SUP: approve

    Note over SUP: Phase 4: Drafting

    SUP->>WRI: execute(AnalysisReport + Ideas)
    WRI-->>SUP: PaperDraft

    Note over SUP: CHECKPOINT 4 — User reviews draft

    SUP->>User: checkpoint.awaiting_approval
    User-->>SUP: approve

    Note over SUP: Phase 5: Review

    SUP->>REV: execute(PaperDraft)
    REV->>TOOL: crossref.validate_citations()
    TOOL-->>REV: Validation
    REV-->>SUP: ReviewReport

    Note over SUP: Phase 6: Evaluation + Cost

    SUP->>SUP: EvaluationEngine.evaluate("draft", PaperDraft)
    Note over SUP: Checks: citation accuracy, groundedness,<br/>hallucination rate, traceability, completeness
    SUP->>SUP: CostMetricsHandler.handle_llm_usage()
    Note over SUP: Publishes cost events via async EventBus

    SUP-->>User: WorkflowResult
```

## Agent Message Schema

```python
class AgentMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex[:12]}")
    workflow_id: str
    source_agent: str
    target_agent: str  # "supervisor" for all result messages
    message_type: Literal["command", "result", "error", "status_update"]
    payload: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: str
    correlation_id: str
```

## Agent Handoff Protocol (Supervisor Internal)

```python
class SupervisorAgent(BaseAgent):
    """Coordinates agent execution with state persistence."""

    async def execute_step(self, step: WorkflowStep) -> AgentResult:
        agent = self.agent_registry.get(step.agent_id)

        for attempt in range(agent.max_retries):
            try:
                # 1. Load input from workflow state
                input_data = await self.state_manager.get_step_input(step.id)

                # 2. Execute agent
                result = await agent.execute(AgentContext(
                    workflow_id=self.workflow_id,
                    step_id=step.id,
                    input=input_data,
                    trace_id=self.trace_id,
                ))

                # 3. Validate output
                if not await agent.validate_output(result):
                    raise ValidationError(f"Agent {step.agent_id} returned invalid output")

                # 4. Persist state
                await self.state_manager.set_step_output(step.id, result)
                await self.state_manager.persist_workflow_state(self.workflow_id)

                # 5. Emit event
                await self.event_bus.publish(AgentCompleted(
                    agent_id=step.agent_id,
                    workflow_id=self.workflow_id,
                    output_summary=result.summary(),
                    duration_ms=result.duration_ms,
                ))

                return result

            except RetryableError as e:
                if attempt < agent.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    await self.event_bus.publish(AgentRetrying(
                        agent_id=step.agent_id,
                        attempt=attempt + 1,
                        error=str(e),
                    ))
                    continue
                raise
```

## Parallel Execution Rules

| Agents | Parallel? | Condition |
|---|---|---|
| Planning + anything | No | Planning must complete first |
| Research + PDF processing | Yes | Independent processes |
| Analysis + PDF processing | Yes | Analysis reads from PostgreSQL where PDF is stored |
| Analysis + Idea Generation | No | Ideas depend on analysis |
| Writing + Review | No | Review depends on writing |
| Analysis + Export | No | Export needs complete results |

## Error Handling Protocol

```mermaid
stateDiagram-v2
    [*] --> Running: Agent started
    Running --> Success: Valid output
    Running --> Retrying: Retryable error (429, timeout)
    Retrying --> Running: Retry attempt
    Retrying --> Failed: Max retries exceeded
    Running --> Failed: Non-retryable error
    Failed --> SupervisorDecision: Error escalated
    SupervisorDecision --> SkipStep: Mark step as failed, continue
    SupervisorDecision --> AbortWorkflow: Critical step failed
    SupervisorDecision --> FallbackAgent: Route to alternative
    SkipStep --> [*]: Partial results
    AbortWorkflow --> [*]: Workflow failed
    FallbackAgent --> Running: Execute fallback
```

## Agent Timeout Configuration

| Agent | Timeout (s) | Max Retries | Retry Backoff |
|---|---|---|---|
| Supervisor | 300 | 0 | N/A (delegates retries) |
| Planning | 30 | 2 | 1s, 4s |
| Research | 60 | 3 | 1s, 4s, 16s |
| Analysis | 120 | 3 | 1s, 4s, 16s |
| Idea Generation | 90 | 2 | 1s, 4s |
| Writing | 180 | 3 | 1s, 4s, 16s |
| Review | 60 | 2 | 1s, 4s |
