# AARA — Autonomous AI Research Assistant

## Documentation Index

### Phase 0.5: Architecture Hardening (31–32)
| # | Document | Description |
|---|----------|-------------|
| 31 | [AI Evaluation Framework](architecture/31-ai-evaluation-framework.md) | 8 quality metrics, evaluation engine, per-phase scoring |
| 32 | [Cost Intelligence](architecture/32-cost-intelligence.md) | Per-workflow cost tracking, budget enforcement, dashboard |

### Phase 0.6: Implementation Readiness (33–35)
| # | Document | Description |
|---|----------|-------------|
| 33 | [Plugin & Extension Architecture](architecture/33-plugin-extension-architecture.md) | Registries, DI container, @decorator registration, plugin discovery |
| 34 | [Configuration & Feature Flags](architecture/34-configuration-feature-flags.md) | Config hierarchy, feature flags, kill switches, gradual rollout |
| 35 | [Comprehensive Testing Strategy](architecture/35-testing-strategy-comprehensive.md) | Contract, agent, security, performance, chaos testing |

### Phase 1: Foundation (01–07)
| # | Document | Description |
|---|----------|-------------|
| 01 | [Implementation Roadmap](architecture/01-implementation-roadmap.md) | 6-phase plan with deliverables and timeline |
| 02 | [Feature Breakdown](architecture/02-feature-breakdown.md) | Features by phase with priority and dependencies |
| 03 | [Folder Structure](architecture/03-folder-structure.md) | Complete project directory layout |
| 04 | [Database Schema](architecture/04-database-schema.md) | 27 tables across auth, workspace, memory, metadata |
| 05 | [ER Diagram](architecture/05-er-diagram.md) | Entity-relationship diagram |
| 06 | [Authentication Flow](architecture/06-authentication-flow.md) | Supabase Auth, RLS, JWT, session management |
| 07 | [Workspace Architecture](architecture/07-workspace-architecture.md) | Workspace lifecycle, isolation, member roles |

### Phase 2: Research Infrastructure (08–13)
| # | Document | Description |
|---|----------|-------------|
| 08 | [Research API Architecture](architecture/08-research-api-architecture.md) | Unified API gateway for 5 external research indices |
| 09 | [PDF Processing Pipeline](architecture/09-pdf-processing-pipeline.md) | 13-stage pipeline from upload to embedding |
| 10 | [Embedding Pipeline](architecture/10-embedding-pipeline.md) | Provider abstraction, chunking, model versioning |
| 11 | [Vector Database Design](architecture/11-vector-database-design.md) | Qdrant collections, HNSW, hybrid search |
| 12 | [Search Pipeline](architecture/12-search-pipeline.md) | Cross-source search with dedup, ranking, filtering |
| 13 | [Research Workspace Flow](architecture/13-research-workspace-flow.md) | Full workspace lifecycle from topic to export |

### Phase 3: Core Agentic AI (14–20)
| # | Document | Description |
|---|----------|-------------|
| 14 | [Agent Interaction Diagrams](architecture/14-agent-interaction-diagrams.md) | 7-agent architecture with tool calls and event flow |
| 15 | [Supervisor Workflow](architecture/15-supervisor-workflow.md) | Supervisor state machine, plan delegation, error recovery |
| 16 | [Agent State Management](architecture/16-agent-state-management.md) | ReAct lifecycle, state persistence, recovery |
| 17 | [Memory Architecture](architecture/17-memory-architecture.md) | 3-layer memory: Session, Workspace, Global |
| 18 | [Prompt Strategy](architecture/18-prompt-strategy.md) | Prompt templates, system prompts, few-shot management |
| 19 | [Context Window Management](architecture/19-context-window-management.md) | Token budgeting, overflow strategies, cross-model portability |
| 20 | [Human-in-the-loop Design](architecture/20-human-in-the-loop-design.md) | 4 approval checkpoints with timeout and recovery |

### Phase 4: Generation & Review (21–25)
| # | Document | Description |
|---|----------|-------------|
| 21 | [Research Gap Analysis](architecture/21-research-gap-analysis-design.md) | Theme extraction, gap identification, overlap analysis |
| 22 | [Research Idea Generation](architecture/22-research-idea-generation.md) | Idea proposal, novelty scoring, diversity ranking |
| 23 | [Paper Draft Generation](architecture/23-paper-draft-generation.md) | Structured multi-section draft with inline citations |
| 24 | [Review Pipeline](architecture/24-review-pipeline.md) | Multi-criteria review, citation validation, revision |
| 25 | [Export Pipeline](architecture/25-export-pipeline.md) | PDF, Markdown, DOCX, LaTeX, BibTeX export |

### Phase 5: Production (26–30)
| # | Document | Description |
|---|----------|-------------|
| 26 | [Security Design](architecture/26-security-design.md) | Auth, RLS, RBAC, rate limiting, input validation, LLM Security Layer, RAG Protection |
| 27 | [Testing Strategy](architecture/27-testing-strategy.md) | Unit, integration, E2E, VCR-recorded, CI gates |
| 28 | [Monitoring & Logging](architecture/28-monitoring-and-logging.md) | Event Bus, structured logs, metrics, tracing |
| 29 | [Deployment Architecture](architecture/29-deployment-architecture.md) | Containerized stack, Supabase, Qdrant, Railway |
| 30 | [CI/CD Pipeline](architecture/30-ci-cd-pipeline.md) | GitHub Actions, Docker build, staged deploy |

### Supplemental Documents
| Document | Description |
|----------|-------------|
| [Architecture Review](sup/architecture-review.md) | Assessment of original design and resolution of weaknesses |
| [Product Requirements](sup/prd.md) | Vision, target users, user stories, non-functional requirements |
| [Technical Requirements](sup/trd.md) | Stack, performance targets, error codes |
| [Final Architect Review](sup/final-architect-review.md) | 8.5/10 evaluation and final approval verdict |

### Diagrams
| File | Source Document |
|------|-----------------|
| [System Context](diagrams/system-context.mmd) | 08 — Research API Architecture |
| [Workflow Sequence](diagrams/workflow-sequence.mmd) | 14 — Agent Interaction Diagrams |
| [PDF Pipeline](diagrams/pdf-pipeline.mmd) | 09 — PDF Processing Pipeline |
| [Agent Lifecycle](diagrams/agent-lifecycle.mmd) | 16 — Agent State Management |
| [Supervisor State Machine](diagrams/supervisor-state-machine.mmd) | 15 — Supervisor Workflow |
| [Human-in-the-loop](diagrams/human-in-the-loop.mmd) | 20 — Human-in-the-loop Design |
| [Memory Architecture](diagrams/memory-architecture.mmd) | 17 — Memory Architecture |
| [CI/CD Pipeline](diagrams/ci-cd-pipeline.mmd) | 30 — CI/CD Pipeline |

## Key Architecture Decisions

- **7 Agents**: Supervisor, Planning, Research, Analysis, Idea Generation, Writing, Review — all with ReAct lifecycle
- **Provider Router**: Cost/latency/context-aware LLM selection across OpenAI, Gemini, Groq, OpenRouter, Ollama
- **Tool Router + Registry**: Agents never call APIs directly; all external calls through Tool Router
- **MCP Gateway**: Agent-to-tool gateway supporting Model Context Protocol
- **Event Bus** (Async): Non-blocking event queue with per-handler retry and failure isolation
- **Workflow Engine**: Sequential executor (replaceable) with idempotency and batch state persistence
- **Human-in-the-loop**: 4 checkpoints at phase transitions
- **3-Layer Memory**: Session (in-memory), Workspace (PostgreSQL+Qdrant), Global (PostgreSQL)
- **Embedding Versioning**: Per-model Qdrant collections, lazy re-embedding, batch embedding
- **LLM Security Layer**: Defense-in-depth with Input Guard, Prompt Isolation, RAG Protection, Output Guard
- **AI Evaluation Framework**: 8 metrics evaluating citation accuracy, groundedness, hallucination rate, coverage, gap quality, novelty support, traceability, completeness
- **Cost Intelligence**: Per-workflow cost tracking with event-based collection and budget enforcement
- **Vector DB**: Qdrant (primary) with payload indexes on workspace_id, paper_id, model_id
- **Auth**: Supabase Auth with cached JWKS verification (local RS256, 1h TTL)

For implementation planning, see [01-implementation-roadmap.md](architecture/01-implementation-roadmap.md).
