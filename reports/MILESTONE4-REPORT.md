# Milestone 4 — Agent Runtime Report

## Summary
Multi-agent execution runtime with 7 specialized agents, workflow engine, human approval, and event streaming — all built on the Milestone 3 AI platform.

## Build Status
- **Source files**: 31 files across 4 modules (`agents/`, `workflow/`, `approval/`, `streaming/`)
- **Test files**: 5 files with 261 tests
- **Full project tests**: 1361 passed (0 failures, 0 errors)
- **Lint**: 0 errors (ruff --strict)
- **Type Check**: 0 errors (mypy --strict)
- **Deprecation Warnings**: 0 (fixed `datetime.utcnow()` -> `datetime.now(UTC)`)

## Architecture

```
SupervisorAgent
 ├── PlanningAgent    → ExecutionPlan
 ├── ResearchAgent    → Papers + Citations
 ├── AnalysisAgent    → Themes + Gaps + Contradictions
 ├── IdeaGenerationAgent → Novelty Scores + Recommendations
 ├── WritingAgent     → Draft Sections
 └── ReviewAgent      → Quality Scores + Issues
```

| Module | Files | Purpose |
|--------|-------|---------|
| `agents/models.py` | 1 | All dataclasses (AgentStatus, AgentPhase, AgentContext, AgentOutput, AgentState, ExecutionPlan, WorkflowResult, etc.) |
| `agents/base.py` | 1 | `BaseAgent` abstract class with lifecycle, error handling, token estimation |
| `agents/lifecycle.py` | 1 | State machine with 16 phases per architecture doc 16 |
| `agents/registry.py` | 1 | `@register()` decorator, lazy singleton, `RegistryError` |
| `agents/task_graph.py` | 1 | Topological sort, cycle detection, parallel levels |
| `agents/supervisor.py` | 1 | 6-phase orchestration with 4 human checkpoints |
| `agents/planning.py` | 1 | Query decomposition, dependency wiring, cost estimation |
| `agents/research.py` | 1 | Search expansion, paper collection, relevance rating |
| `agents/analysis.py` | 1 | Clustering, gap detection, contradiction detection |
| `agents/idea_generation.py` | 1 | Novelty scoring, opportunity assessment, prioritization |
| `agents/writing.py` | 1 | Section generation, citation insertion, draft refinement |
| `agents/review.py` | 1 | Quality evaluation (reuses EvaluationEngine), citation verification |
| `workflow/types.py` | 1 | WorkflowDefinition, WorkflowState, WorkflowStepResult, enums |
| `workflow/engine.py` | 1 | Sequential/parallel/dependency execution, pause/resume/cancel/retry/timeout |
| `workflow/checkpoint.py` | 1 | Create/get/list/resolve/expire checkpoints |
| `workflow/idempotency.py` | 1 | SHA-256 key, 24h TTL, deduplication |
| `approval/models.py` | 1 | ApprovalCheckpoint, CheckpointStatus, ApprovalDecision enums |
| `approval/human.py` | 1 | Approve/reject/revise/continue/pause/resume |
| `streaming/events.py` | 1 | 15 EventType values, AgentEvent, WorkflowEvent, ProgressEvent, TokenStreamEvent |
| `streaming/manager.py` | 1 | Queue-based pub/sub, 1000-event history buffer, async generator |

## Agent Design Decisions
- **ReAct Loop**: Plan → Reason → Validate → Output pattern in all agents
- **Supervisor-only communication**: No direct agent-to-agent calls (per doc 14)
- **Deterministic LLM fallbacks**: Research/analysis agents use rule-based logic instead of LLM calls (eliminates `ProviderRouter` dependency for core execution)
- **TaskGraph**: Kahn's algorithm for topological sort with cycle detection
- **WorkflowEngine**: 3 execution modes — SEQUENTIAL, PARALLEL, DEPENDENCY
- **CheckpointManager**: Named checkpoints with expiry (stale after 24h)
- **IdempotencyManager**: SHA-256(key:user:workspace:query) + 24h TTL
- **HumanApprovalManager**: Pause/resume via asyncio.Event

## Test Coverage
| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_foundation.py` | 75 | Models, BaseAgent, Lifecycle, Registry, TaskGraph |
| `test_agents.py` | 77 | All 7 agents (Planning, Research, Analysis, IdeaGen, Writing, Review, Supervisor) |
| `test_workflow.py` | 52 | Types, Engine (seq/par/dep), Checkpoint, Idempotency |
| `test_approval.py` | 21 | Enums, HumanApprovalManager (approve/reject/revise/pause/resume) |
| `test_streaming.py` | 36 | Events, EventStreamManager (pub/sub/history/token streaming) |
| **Total** | **261** | |

## Technical Details
- **Python**: 3.14.2
- **Framework**: pytest + pytest-asyncio
- **Patterns**: Abstract base classes, strategy pattern (agents), observer pattern (streaming), state machine (lifecycle)
- **No new dependencies**: All reuse from Milestone 3 AI platform
- **Zero external LLM calls**: Deterministic logic for research/analysis
