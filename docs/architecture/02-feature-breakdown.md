# Document 02 — Feature Breakdown

## Phase 0.5 Features (Architecture Hardening)

| ID | Feature | Description | Effort (hrs) | Priority |
|---|---|---|---|---|
| F0.1 | LLM Security Layer | Input guard, prompt isolation, instruction hierarchy, RAG protection, output guard | 10 | P0 |
| F0.2 | Cached JWKS Verification | Local JWT verification with 1h cache + Supabase fallback | 4 | P0 |
| F0.3 | Batch Embedding Pipeline | `embed_batch()` interface + per-provider batch support | 3 | P0 |
| F0.4 | Qdrant Payload Indexes | Index on workspace_id, paper_id, model_id at collection creation | 2 | P0 |
| F0.5 | Workflow Idempotency | Idempotency-Key header, DB uniqueness, 24h TTL | 4 | P0 |
| F0.6 | Batch State Persistence | Async flush + forced flush on checkpoints | 4 | P0 |
| F0.7 | Async Event Bus | Non-blocking queue, per-handler retry, failure isolation | 4 | P0 |
| F0.8 | AI Evaluation Framework | 8 metrics, evaluation engine, per-phase evaluation, quality report | 8 | P1 |
| F0.9 | Cost Intelligence Dashboard | Event-based cost collection, cost_metrics table, budget enforcement | 8 | P1 |
| F0.10 | Plugin & Extension Architecture | Agent/Tool/Provider/Workflow registries, DI container, plugin discovery | 6 | P1 |
| F0.11 | Configuration & Feature Flag System | Config hierarchy, env vars, feature flags, kill switches, validation | 6 | P1 |
| F0.12 | Comprehensive Testing Architecture | Contract, agent, security, performance, chaos testing | 8 | P1 |

## Phase 1 Features (Foundation)

| ID | Feature | Description | Effort (hrs) | Priority | Acceptance |
|---|---|---|---|---|---|
| F1.1 | User Authentication | Email + Google OAuth via Supabase Auth | 12 | P0 | Login, register, password reset work |
| F1.2 | JWT Session Management | Auto-refresh, httpOnly cookies, logout | 6 | P0 | Tokens refresh silently; 401 redirects to login |
| F1.3 | Workspace CRUD | Create, read, update, delete research topic workspaces | 8 | P0 | Full CRUD with ownership enforcement |
| F1.4 | Dashboard | Workspace grid view, recent activity, empty state | 8 | P0 | Lists user's workspaces with metadata |
| F1.5 | Workspace Detail | Tabbed layout (Papers, Analysis, Settings) | 6 | P1 | Tabs render correctly; settings page functional |
| F1.6 | Profile Management | Display name, avatar, API key input | 4 | P1 | User can update profile and add API keys |
| F1.7 | Dark/Light Theme | System-aware + manual toggle | 3 | P1 | Theme persists across sessions |
| F1.8 | RBAC + RLS | Role-based access + Row Level Security | 6 | P0 | Viewer/Editor/Admin roles enforced at DB level |

## Phase 2 Features (Research Infrastructure)

| ID | Feature | Description | Effort (hrs) | Priority |
|---|---|---|---|---|
| F2.1 | Multi-Source Search | Search Semantic Scholar, arXiv, Crossref, PubMed, OpenAlex | 20 | P0 |
| F2.2 | Paper Deduplication | DOI → title similarity → author+year | 6 | P0 |
| F2.3 | Paper Ranking | Relevance + citation count + recency scoring | 4 | P1 |
| F2.4 | Paper Import by ID/DOI | Import specific papers by identifier | 4 | P0 |
| F2.5 | PDF Upload | File upload with virus scan, validation | 4 | P0 |
| F2.6 | PDF Text Extraction | PyMuPDF text extraction + section parsing | 6 | P0 |
| F2.7 | PDF OCR Fallback | Tesseract for scanned PDFs | 6 | P1 |
| F2.8 | PDF Table Extraction | pdfplumber table detection | 6 | P1 |
| F2.9 | PDF Reference Extraction | Regex + heuristic reference parsing | 8 | P0 |
| F2.10 | Semantic Chunking | Section-bounded with overlap | 4 | P0 |
| F2.11 | Embedding Generation | Sentence Transformers (local) + OpenAI (cloud) | 6 | P0 |
| F2.12 | Qdrant Integration | Collection per model, upsert, search | 6 | P0 |
| F2.13 | Embedding Model Versioning | Model-specific collections, lazy re-embedding | 4 | P0 |
| F2.14 | Semantic Search API | Natural language query → vector search | 6 | P0 |
| F2.15 | Cost Control Cache | In-memory TTL cache for LLM responses | 6 | P0 |
| F2.16 | Provider Router | Selection logic (cost, latency, context) | 8 | P0 |
| F2.17 | LLM Provider Adapters | OpenAI, Gemini, Groq, OpenRouter, Ollama | 12 | P0 |
| F2.18 | Tokenizer Interface | tiktoken + SentencePiece unified wrapper | 4 | P0 |

## Phase 3 Features (Core Agentic AI)

| ID | Feature | Description | Effort (hrs) | Priority |
|---|---|---|---|---|
| F3.1 | BaseAgent Class | ReAct lifecycle, structured output, retry, logging | 8 | P0 |
| F3.2 | Event Bus | In-memory pub/sub | 6 | P0 |
| F3.3 | Tool Router / Tool Registry | Validation, caching, retry, static registration | 10 | P0 |
| F3.4 | WebSocket Manager | Per-user WebSocket connections, reconnection | 8 | P0 |
| F3.5 | SSE Fallback | Server-Sent Events for non-WebSocket clients | 4 | P1 |
| F3.6 | Supervisor Agent | Workflow orchestration, error handling, aggregation | 8 | P0 |
| F3.7 | Planning Agent | Query decomposition, execution plan generation | 8 | P0 |
| F3.8 | Research Agent | Multi-source search via tools, dedup, ranking | 12 | P0 |
| F3.9 | Analysis Agent | Theme extraction, gap analysis, comparison | 12 | P0 |
| F3.10 | Workflow Engine | Sequential executor, state manager, aggregator | 12 | P0 |
| F3.11 | Workflow State Persistence | Per-step state save to PostgreSQL | 4 | P0 |
| F3.12 | Human-in-the-Loop | Approval checkpoints, pause/resume | 6 | P0 |
| F3.13 | MCP Gateway | Adapter for external MCP servers | 6 | P2 |
| F3.14 | Agent Execution UI | Live view, progress bars, logs, timeline | 12 | P0 |
| F3.15 | Literature Review UI | Theme cards, gap display, comparison tables | 8 | P1 |
| F3.16 | Global Memory | Prompt templates, user preferences | 4 | P1 |

## Phase 4 Features (Generation & Review)

| ID | Feature | Description | Effort (hrs) | Priority |
|---|---|---|---|---|
| F4.1 | Idea Generation Agent | Gap-to-idea mapping, Research Overlap Analysis | 10 | P0 |
| F4.2 | Writing Agent | Structured draft with inline citations, sections | 12 | P0 |
| F4.3 | Review Agent | Quality check, citation validation, structured feedback | 10 | P0 |
| F4.4 | Evaluation Engine | Objective metrics (citation accuracy, coverage, latency, cost) | 8 | P0 |
| F4.5 | Export: PDF | ReportLab/pandoc | 8 | P0 |
| F4.6 | Export: Markdown | Direct string generation | 3 | P0 |
| F4.7 | Export: DOCX | python-docx | 6 | P1 |
| F4.8 | Export: LaTeX | Template-based .tex generation | 6 | P1 |
| F4.9 | Export: BibTeX | Bibliography generation | 4 | P1 |
| F4.10 | Template System | IEEE, ACM, Springer format presets | 10 | P2 |
| F4.11 | Idea Explorer UI | Card view, filtering, approval | 6 | P1 |
| F4.12 | Draft Editor UI | Monaco Editor + section management | 10 | P0 |
| F4.13 | Review Panel UI | Score display, issue list, suggestions | 6 | P1 |
| F4.14 | Export Dialog | Format selector + download | 4 | P0 |

## Phase 5 Features (Production)

| ID | Feature | Description | Effort (hrs) | Priority |
|---|---|---|---|---|
| F5.1 | Rate Limiting | Token bucket per-user, per-endpoint, per-provider | 6 | P0 |
| F5.2 | Security Hardening | OWASP review, prompt injection protection | 8 | P0 |
| F5.3 | Volume Testing | 10 concurrent workflows, 50 PDFs, 1K search queries | 6 | P1 |
| F5.4 | Performance Optimization | SQL profiling, N+1 fixes, indexing, caching | 8 | P1 |
| F5.5 | Cost Dashboard UI | Per-user, per-workflow, per-provider cost display | 8 | P1 |
| F5.6 | Agent Performance Dashboard | Latency, success rate, retry stats | 6 | P1 |
| F5.7 | Evaluation Dashboard | Metric visualization per workflow | 6 | P1 |
| F5.8 | CI/CD Pipeline | GitHub Actions → Railway deploy | 8 | P0 |
| F5.9 | Monitoring | Error rate + budget threshold alerts | 4 | P2 |
| F5.10 | Documentation | Setup guide + user guide | 10 | P1 |
| F5.11 | Final E2E Tests | Full workflow regression suite | 8 | P2 |

## Total Effort Summary

| Phase | Total Features | Total Hours |
|---|---|---|
| Phase 0.6 — Implementation Readiness | 3 | 20 |
| Phase 0.5 — Architecture Hardening | 9 | 47 |
| Phase 1 — Foundation | 8 | 53 |
| Phase 2 — Research Infrastructure | 18 | 120 |
| Phase 3 — Core Agentic AI | 16 | 122 |
| Phase 4 — Generation & Review | 14 | 99 |
| Phase 5 — Production Readiness | 11 | 76 |
| **Total** | **79** | **537** |
