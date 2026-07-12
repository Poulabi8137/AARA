# AARA — Technical Summary

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (Next.js 16)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  React    │  │  proxy.ts│  │  Zustand State       │   │
│  │  UI       │  │ JWT Guard│  │  Management          │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP + JWT
┌──────────────────────▼──────────────────────────────────┐
│                  Backend (FastAPI / Python 3.12)          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ API Layer│  │Middleware│  │  Auth Service         │   │
│  │46 Endpts │  │Rate Limit│  │  JWT + RBAC + Owner   │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐    │
│  │         LangGraph Agent System                    │    │
│  │  Planner → Retriever → Summarizer → Gap Analyzer │    │
│  │                    → Report Generator             │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ Document │  │ LLM      │  │  Evaluation           │   │
│  │Ingestion │  │Providers │  │  Benchmark Suite      │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
└──────┬──────────────┬──────────────┬───────────────────┘
       │              │              │
┌──────▼─────┐ ┌─────▼──────┐ ┌─────▼──────────────┐
│ PostgreSQL │ │  ChromaDB  │ │  Redis 7            │
│ Users/     │ │  Vector    │ │  Cache/Rate Limit   │
│ Projects   │ │  Store     │ │                     │
└────────────┘ └────────────┘ └─────────────────────┘
       │              │              │
┌──────▼─────────────────────────────▼──────────────────┐
│              Observability Stack                        │
│  Prometheus (12 metrics) → Grafana (dashboards)        │
│  Sentry (error tracking) → Structured JSON logs        │
└────────────────────────────────────────────────────────┘
```

## Agent Workflow

| Step | Agent | Input | Output | Key Tech |
|------|-------|-------|--------|----------|
| 1 | **Planner** | User query | Research plan (subtopics, queries, methodology) | Few-shot prompting, structured output |
| 2 | **Retriever** | Research plan | Ranked papers with relevance scores | ChromaDB semantic search, re-ranking |
| 3 | **Summarizer** | Ranked papers | Thematic summaries per subtopic | LLM synthesis, theme extraction |
| 4 | **Gap Analyzer** | Themes | Research gaps (severity, confidence, remediation) | Structured classification |
| 5 | **Report Generator** | All outputs | Final report (3 formats, 4 citation styles) | Template + LLM enhancement |

## Security Architecture

```
Layer 1: proxy.ts — Edge JWT validation (cookie-based)
Layer 2: API Client — Bearer token, silent refresh, 401 queueing
Layer 3: Middleware — Rate limiting (Lua), security headers, logging
Layer 4: Service — JWT verify, RBAC, ownership enforcement
```

## Key Technical Decisions

1. **LangGraph over LangChain**: Finer-grained state control, typed schemas, conditional branching
2. **proxy.ts over middleware.ts**: Next.js 16 compatibility, custom JWT validation at edge
3. **Pluggable LLM providers**: Strategy pattern for OpenAI, Gemini, Mock
4. **Async SQLAlchemy**: Non-blocking database access for high concurrency
5. **Atomic Lua rate limiting**: Eliminates TOCTOU race condition in concurrent scenarios
