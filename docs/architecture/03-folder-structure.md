# Document 03 — Folder Structure

## Overview

The folder structure follows a modular monolith pattern with clean separation between:
- **`frontend/`** — Next.js 16 App Router with feature-based component colocation
- **`backend/`** — FastAPI with domain-driven modules (agents, tools, providers, pipeline, workflow, event_bus, memory, cost, evaluation, security, auth)
- **`docs/`** — Architecture documents, API specs, prompt templates, ADRs
- **`scripts/`** — Dev automation (setup, seed, reset)

**Design Rationale**:
- Feature colocation over technical splitting: `agents/`, `tools/`, `providers/` each own their entire stack (models, schemas, logic)
- Provider abstraction in `providers/` with `BaseProvider` interfaces — swapping OpenAI for Ollama requires zero agent code changes
- `pipeline/` isolates the complex PDF processing from the rest of the system
- `tests/` mirrors the source tree for clear mapping

## Complete Directory Tree

```
aara/
├── README.md
├── docker-compose.yml                    # Development environment (all services)
├── docker-compose.prod.yml               # Production environment (Railway)
├── .env.example                          # Environment variable template
├── .github/
│   └── workflows/
│       ├── ci.yml                        # Lint, type-check, test
│       └── deploy.yml                    # Railway deploy
│
├── frontend/                             # Next.js 16 App Router
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── components.json                   # shadcn/ui config
│   ├── public/
│   │   ├── logo.svg
│   │   └── icons/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout (providers, theme)
│   │   ├── page.tsx                      # Landing/redirect
│   │   ├── loading.tsx
│   │   ├── error.tsx
│   │   ├── globals.css
│   │   ├── (auth)/                       # Auth route group
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   └── callback/page.tsx         # OAuth callback
│   │   ├── (dashboard)/                  # Authenticated route group
│   │   │   ├── layout.tsx                # Sidebar + header
│   │   │   ├── dashboard/page.tsx        # Workspace grid
│   │   │   ├── workspace/
│   │   │   │   └── [workspace_id]/
│   │   │   │       ├── layout.tsx        # Tabs layout
│   │   │   │       ├── page.tsx          # Workspace overview
│   │   │   │       ├── papers/
│   │   │   │       │   ├── page.tsx      # Paper library
│   │   │   │       │   └── [paper_id]/
│   │   │   │       │       └── page.tsx  # Paper detail
│   │   │   │       ├── analysis/
│   │   │   │       │   ├── page.tsx      # Analysis dashboard
│   │   │   │       │   ├── review/
│   │   │   │       │   │   └── page.tsx  # Literature review
│   │   │   │       │   ├── gaps/
│   │   │   │       │   │   └── page.tsx  # Gap analysis
│   │   │   │       │   └── timeline/
│   │   │   │       │       └── page.tsx  # Research timeline
│   │   │   │       ├── ideas/
│   │   │   │       │   └── page.tsx      # Idea generation
│   │   │   │       ├── draft/
│   │   │   │       │   └── page.tsx      # Paper draft editor
│   │   │   │       ├── export/
│   │   │   │       │   └── page.tsx      # Export dialog
│   │   │   │       └── settings/
│   │   │   │           └── page.tsx      # Workspace settings
│   │   │   └── profile/page.tsx
│   │   └── api/                          # Next.js API routes (optional proxy)
│   │       └── [...path]/route.ts
│   │
│   ├── components/
│   │   ├── ui/                           # shadcn/ui primitives
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── theme-toggle.tsx
│   │   ├── auth/
│   │   │   ├── login-form.tsx
│   │   │   ├── register-form.tsx
│   │   │   └── auth-guard.tsx
│   │   ├── workspace/
│   │   │   ├── workspace-card.tsx
│   │   │   ├── create-workspace-dialog.tsx
│   │   │   └── workspace-settings.tsx
│   │   ├── papers/
│   │   │   ├── paper-list.tsx
│   │   │   ├── paper-card.tsx
│   │   │   ├── paper-detail.tsx
│   │   │   ├── paper-upload.tsx
│   │   │   ├── search-bar.tsx
│   │   │   └── semantic-search.tsx
│   │   ├── analysis/
│   │   │   ├── literature-review.tsx
│   │   │   ├── gap-analysis.tsx
│   │   │   ├── comparison-table.tsx
│   │   │   └── research-timeline.tsx
│   │   ├── agents/
│   │   │   ├── agent-execution-view.tsx   # Live agent visualization
│   │   │   ├── agent-timeline.tsx
│   │   │   ├── agent-log-panel.tsx
│   │   │   └── checkpoint-dialog.tsx      # Human approval UI
│   │   ├── ideas/
│   │   │   ├── idea-card.tsx
│   │   │   └── idea-generator.tsx
│   │   ├── draft/
│   │   │   ├── draft-editor.tsx
│   │   │   └── draft-preview.tsx
│   │   ├── export/
│   │   │   ├── export-dialog.tsx
│   │   │   └── format-selector.tsx
│   │   ├── evaluation/
│   │   │   ├── metrics-display.tsx
│   │   │   └── quality-report.tsx
│   │   └── shared/
│   │       ├── loading-spinner.tsx
│   │       ├── empty-state.tsx
│   │       ├── error-state.tsx
│   │       └── page-header.tsx
│   │
│   ├── lib/
│   │   ├── api-client.ts                 # TanStack Query hooks
│   │   ├── websocket-client.ts           # WebSocket manager + reconnection
│   │   ├── auth-context.tsx               # Auth provider
│   │   ├── theme-context.tsx
│   │   └── utils.ts                      # cn(), formatters
│   │
│   ├── stores/
│   │   ├── workspace-store.ts            # Zustand (current workspace)
│   │   ├── workflow-store.ts             # Zustand (active workflow state)
│   │   └── ui-store.ts                   # Zustand (sidebar, theme, modals)
│   │
│   ├── types/
│   │   ├── api.ts                        # API response/request types
│   │   ├── workspace.ts
│   │   ├── paper.ts
│   │   ├── analysis.ts
│   │   ├── agent.ts
│   │   ├── workflow.ts
│   │   ├── idea.ts
│   │   ├── draft.ts
│   │   └── evaluation.ts
│   │
│   └── hooks/
│       ├── use-workspace.ts
│       ├── use-papers.ts
│       ├── use-analysis.ts
│       ├── use-workflow.ts
│       ├── use-agent-stream.ts           # WebSocket hook
│       └── use-export.ts
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI app factory (startup, shutdown)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                 # Pydantic Settings
│   │   │   ├── database.py               # Async SQLAlchemy engine + session
│   │   │   ├── dependencies.py           # FastAPI dependency injection
│   │   │   ├── exceptions.py             # Custom exception classes
│   │   │   ├── middleware.py             # CORS, rate limiting, request ID
│   │   │   └── events.py                 # Startup/shutdown event handlers
│   │   │
│   │   ├── auth/                         # Authentication
│   │   │   ├── __init__.py
│   │   │   ├── jwt_handler.py            # Cached JWKS verification (doc 06)
│   │   │   ├── rbac.py                   # Role-based access control
│   │   │   └── dependencies.py           # get_current_user, require_role
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py             # v1 route aggregator
│   │   │   │   ├── auth.py               # /auth/* endpoints
│   │   │   │   ├── workspaces.py         # /workspaces/*
│   │   │   │   ├── papers.py             # /papers/*
│   │   │   │   ├── search.py             # /search/*
│   │   │   │   ├── analysis.py           # /analysis/*
│   │   │   │   ├── ideas.py              # /ideas/*
│   │   │   │   ├── drafts.py             # /drafts/*
│   │   │   │   ├── export.py             # /export/*
│   │   │   │   ├── workflows.py          # /workflows/*
│   │   │   │   ├── agents.py             # /agents/* (execution events)
│   │   │   │   ├── evaluation.py         # /evaluation/*
│   │   │   │   └── admin.py              # /admin/*
│   │   │   └── deps.py                   # Shared API dependencies (pagination)
│   │   │
│   │   ├── models/                       # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── workspace.py
│   │   │   ├── paper.py
│   │   │   ├── author.py
│   │   │   ├── citation.py
│   │   │   ├── workflow.py
│   │   │   ├── agent_execution.py
│   │   │   ├── approval_checkpoint.py
│   │   │   ├── analysis.py
│   │   │   ├── idea.py
│   │   │   ├── draft.py
│   │   │   └── audit_log.py
│   │   │
│   │   ├── schemas/                      # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── workspace.py
│   │   │   ├── paper.py
│   │   │   ├── search.py
│   │   │   ├── analysis.py
│   │   │   ├── idea.py
│   │   │   ├── draft.py
│   │   │   ├── export.py
│   │   │   ├── workflow.py
│   │   │   ├── agent.py
│   │   │   ├── evaluation.py
│   │   │   └── common.py                 # Pagination, error response
│   │   │
│   │   ├── services/                     # Business logic (non-agent)
│   │   │   ├── __init__.py
│   │   │   ├── workspace_service.py
│   │   │   ├── paper_service.py
│   │   │   ├── deduplication_service.py  # Multi-pass paper dedup
│   │   │   ├── citation_service.py       # DOI validation + metadata fetch
│   │   │   ├── export_service.py         # File format generation
│   │   │   ├── overlap_service.py        # Research Overlap Analysis
│   │   │   └── embedding_service.py      # Embedding generation facade
│   │   │
│   │   ├── providers/                    # Abstract provider interfaces
│   │   │   ├── __init__.py
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # BaseProvider interface
│   │   │   │   ├── openai.py
│   │   │   │   ├── gemini.py
│   │   │   │   ├── groq.py
│   │   │   │   ├── openrouter.py
│   │   │   │   └── ollama.py
│   │   │   ├── embedding/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # BaseEmbedder interface
│   │   │   │   ├── sentence_transformer.py
│   │   │   │   └── openai_embedding.py
│   │   │   ├── vector_db/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # BaseVectorDB interface
│   │   │   │   ├── qdrant.py
│   │   │   │   └── pgvector.py          # Alternative implementation
│   │   │   ├── storage/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   └── supabase_storage.py
│   │   │   └── research/
│   │   │       ├── __init__.py
│   │   │       ├── base.py              # BaseResearchProvider
│   │   │       ├── semantic_scholar.py
│   │   │       ├── arxiv.py
│   │   │       ├── crossref.py
│   │   │       ├── pubmed.py
│   │   │       └── openalex.py
│   │   │
│   │   ├── agents/                       # Autonomous AI Agents
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # BaseAgent (ReAct lifecycle)
│   │   │   ├── supervisor.py
│   │   │   ├── planner.py
│   │   │   ├── researcher.py
│   │   │   ├── analyst.py
│   │   │   ├── idea_generator.py
│   │   │   ├── writer.py
│   │   │   └── reviewer.py
│   │   │
│   │   ├── tools/                        # Tool Router + built-in tools
│   │   │   ├── __init__.py
│   │   │   ├── router.py                 # ToolRouter (validate, cache, execute)
│   │   │   ├── registry.py               # ToolRegistry (static registration)
│   │   │   ├── mcp_gateway.py            # MCP adapter bridge
│   │   │   ├── builtin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py               # BaseTool interface
│   │   │   │   ├── semantic_scholar_tool.py
│   │   │   │   ├── arxiv_tool.py
│   │   │   │   ├── crossref_tool.py
│   │   │   │   ├── pubmed_tool.py
│   │   │   │   ├── openalex_tool.py
│   │   │   │   ├── qdrant_search_tool.py
│   │   │   │   ├── citation_validate_tool.py
│   │   │   │   └── embedding_tool.py
│   │   │   └── mcp/
│   │   │       ├── __init__.py
│   │   │       └── mcp_tool_adapter.py
│   │   │
│   │   ├── pipeline/                     # PDF Processing Pipeline
│   │   │   ├── __init__.py
│   │   │   ├── pdf_pipeline.py           # Main orchestrator
│   │   │   ├── stages/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py               # PipelineStage interface
│   │   │   │   ├── virus_scan.py
│   │   │   │   ├── validation.py
│   │   │   │   ├── type_detection.py
│   │   │   │   ├── ocr.py
│   │   │   │   ├── layout.py
│   │   │   │   ├── section.py
│   │   │   │   ├── table_extraction.py
│   │   │   │   ├── figure_extraction.py
│   │   │   │   ├── equation_detection.py
│   │   │   │   ├── reference_extraction.py
│   │   │   │   ├── metadata_extraction.py
│   │   │   │   ├── chunking.py
│   │   │   │   └── embedding.py
│   │   │   └── models.py                 # Stage input/output models
│   │   │
│   │   ├── workflow/                     # Workflow Engine
│   │   │   ├── __init__.py
│   │   │   ├── engine.py                 # WorkflowEngine (orchestrator)
│   │   │   ├── executor.py               # SequentialExecutor
│   │   │   ├── state_manager.py          # State persistence + recovery
│   │   │   ├── aggregator.py             # Result aggregation
│   │   │   └── checkpoint.py            # Human-in-the-loop checkpoints
│   │   │
│   │   ├── memory/                       # Memory Architecture
│   │   │   ├── __init__.py
│   │   │   ├── manager.py                # MemoryManager facade
│   │   │   ├── session.py                # SessionMemory (in-memory)
│   │   │   ├── workspace.py              # WorkspaceMemory (PostgreSQL)
│   │   │   └── global_.py                # GlobalMemory (PostgreSQL)
│   │   │
│   │   ├── cost/                         # Cost Control + Intelligence (doc 32)
│   │   │   ├── __init__.py
│   │   │   ├── controller.py             # CostController (budget, tracking)
│   │   │   ├── router.py                 # ProviderRouter (selection logic)
│   │   │   ├── cache.py                  # Response cache (in-memory TTL)
│   │   │   ├── metrics_handler.py        # CostMetricsHandler (Event Bus listener)
│   │   │   └── budget_enforcer.py        # BudgetEnforcer (per-user limits)
│   │   │
│   │   ├── event_bus/                    # Event Bus
│   │   │   ├── __init__.py
│   │   │   ├── bus.py                    # EventBus (in-memory pub/sub)
│   │   │   ├── events.py                 # Event definitions (pydantic)
│   │   │   └── handlers/                 # Event handler registrations
│   │   │       ├── __init__.py
│   │   │       ├── websocket_handler.py  # Stream to frontend
│   │   │       ├── logger_handler.py     # Structured logging
│   │   │       ├── metrics_handler.py    # Prometheus metrics
│   │   │       └── audit_handler.py      # Audit log persistence
│   │   │
│   │   ├── evaluation/                   # AI Evaluation Framework (doc 31)
│   │   │   ├── __init__.py
│   │   │   ├── engine.py                 # EvaluationEngine (central evaluator)
│   │   │   ├── metrics/                  # Metric definitions (one per metric)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── citation_accuracy.py
│   │   │   │   ├── groundedness.py
│   │   │   │   ├── hallucination.py
│   │   │   │   ├── coverage.py
│   │   │   │   ├── gap_quality.py
│   │   │   │   ├── novelty_support.py
│   │   │   │   ├── traceability.py
│   │   │   │   └── completeness.py
│   │   │   └── reports.py                # Report generation
│   │   │
│   │   ├── cost/                         # Cost Control + Intelligence (doc 32)
│   │   │   ├── __init__.py
│   │   │   ├── controller.py             # CostController (budget, tracking)
│   │   │   ├── router.py                 # ProviderRouter (selection logic)
│   │   │   ├── cache.py                  # Response cache (in-memory TTL)
│   │   │   ├── metrics_handler.py        # CostMetricsHandler (Event Bus listener)
│   │   │   └── budget_enforcer.py        # BudgetEnforcer (per-user limits)
│   │   │
│   │   ├── security/                     # LLM Security Layer (doc 26)
│   │   │   ├── __init__.py
│   │   │   ├── input_guard.py            # InputGuard (Stage 1)
│   │   │   ├── prompt_isolation.py       # PromptIsolator (Stage 2)
│   │   │   ├── rag_protection.py         # RAGProtectionLayer (Stage 3)
│   │   │   ├── output_guard.py           # OutputGuard (Stage 4)
│   │   │   └── sanitized_types.py        # SanitizedContent, GuardResult models
│   │   │
│   │   ├── jobs/                         # Background Job Queue
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # JobQueue interface
│   │   │   ├── fastapi_queue.py          # FastAPI BackgroundTasks impl
│   │   │   ├── local_queue.py            # SQLite-backed impl ($0 dev)
│   │   │   └── arq_queue.py              # ARQ + Redis impl (production)
│   │   │
│   │   └── streaming/                    # WebSocket + SSE
│   │       ├── __init__.py
│   │       ├── manager.py                # WebSocketManager
│   │       └── sse.py                    # SSE event stream
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                   # Shared fixtures (test DB, mock LLM)
│   │   ├── unit/
│   │   │   ├── test_dedup_service.py
│   │   │   ├── test_citation_service.py
│   │   │   ├── test_cost_control.py
│   │   │   ├── test_provider_router.py
│   │   │   └── test_tool_router.py
│   │   ├── integration/
│   │   │   ├── test_agent_orchestration.py
│   │   │   ├── test_workflow_executor.py
│   │   │   ├── test_pdf_pipeline.py
│   │   │   ├── test_research_api.py
│   │   │   └── test_export_service.py
│   │   ├── api/
│   │   │   ├── test_auth.py
│   │   │   ├── test_workspaces.py
│   │   │   ├── test_papers.py
│   │   │   ├── test_workflows.py
│   │   │   └── test_export.py
│   │   └── fixtures/
│   │       ├── papers.json               # Recorded paper API responses
│   │       ├── llm_responses/            # VCR-recorded LLM responses
│   │       └── pdfs/                     # Sample PDFs for pipeline tests
│   │
│   └── scripts/
│       ├── seed_data.py                  # Test data seeding
│       └── reset_db.py                   # Dev database reset
│
├── docs/
│   ├── architecture/                     # Architecture documents
│   │   ├── 01-implementation-roadmap.md
│   │   ├── 02-feature-breakdown.md
│   │   ├── 03-folder-structure.md
│   │   └── ...
│   ├── api/                              # OpenAPI specs (exported from FastAPI)
│   ├── prompts/                          # Prompt templates (versioned)
│   │   ├── agents/
│   │   │   ├── planner.md
│   │   │   ├── researcher.md
│   │   │   ├── analyst.md
│   │   │   ├── idea_generator.md
│   │   │   ├── writer.md
│   │   │   └── reviewer.md
│   │   ├── tools/
│   │   │   └── tool_descriptions.md
│   │   └── system/
│   │       ├── supervisor.md
│   │       └── evaluation.md
│   └── decisions/                        # Architecture Decision Records
│       ├── 001-use-supabase-auth.md
│       ├── 002-use-qdrant.md
│       ├── 003-seven-agent-architecture.md
│       └── ...
│
└── scripts/
    ├── setup.sh                          # One-command dev setup
    └── migrate.sh                        # Alembic migration helper
```
