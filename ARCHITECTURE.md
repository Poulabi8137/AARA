# AARA Architecture

## System Overview

AARA (Agentic AI Research Assistant) is a multi-agent research platform built on a **Next.js 16 frontend** and **FastAPI backend** with **LangGraph agent orchestration**.

```
User Query -> Planner -> Retriever -> Summarizer -> Gap Analyzer -> Report Generator -> Final Report
```

Each agent has a distinct role, and outputs are grounded in actual sources with confidence scores, citation tracking, and transparent reasoning traces.

---

## Architecture Diagram

```mermaid
graph TB
    subgraph Frontend["Frontend (Next.js 16 / React 19)"]
        UI[User Interface]
        Proxy[API Proxy Layer<br/>proxy.ts - JWT Guard]
        Store[Zustand State]
    end

    subgraph Backend["FastAPI Backend (Python 3.12)"]
        API[API Layer<br/>46 Endpoints / 13 Routers]
        Auth[Auth Service<br/>JWT + RBAC + Ownership]
        MW[Middleware Stack<br/>Rate Limit / Logging / Security Headers]
        Agents[LangGraph Agent System<br/>5 Specialized Agents]
        Ingestion[Document Ingestion<br/>PDF / DOCX / TXT / MD]
        LLM[LLM Providers<br/>OpenAI / Gemini / Mock]
    end

    subgraph Storage["Data Layer"]
        PG[(PostgreSQL 16<br/>Users / Projects / Reports)]
        CB[(ChromaDB<br/>Vector Embeddings)]
        RD[(Redis 7<br/>Cache / Rate Limit)]
    end

    subgraph Monitoring["Observability Stack"]
        PM[Prometheus<br/>12 Custom Metrics]
        GF[Grafana<br/>Pre-built Dashboards]
        SN[Sentry<br/>Error Tracking]
    end

    UI --> Proxy
    Proxy --> API
    API --> MW
    MW --> Auth
    API --> Agents
    API --> Ingestion
    Agents --> LLM
    Agents --> PG
    Agents --> CB
    MW --> RD
    Backend --> PM
    PM --> GF
    Backend --> SN
```

---

## Request Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant P as Proxy (proxy.ts)
    participant M as Middleware
    participant A as API Handler
    participant S as Service Layer
    participant D as Database

    C->>P: HTTP Request + JWT
    P->>P: Validate JWT (HMAC-SHA256)
    alt Invalid JWT
        P-->>C: 401 Unauthorized
    end
    P->>M: Forward Request
    M->>M: Generate Request ID
    M->>M: Rate Limit Check (Redis)
    M->>M: Security Headers
    M->>A: Route to Handler
    A->>A: Validate Input (Pydantic)
    A->>S: Business Logic
    S->>D: Query / Mutate
    D-->>S: Result
    S-->>A: Response
    A-->>M: Response
    M->>M: Log + Record Metrics
    M-->>P: Response with X-Request-ID
    P-->>C: JSON Response
```

---

## Agent Architecture

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Planner** | Analyzes query, generates structured research plan | User query | Research plan with subtopics, search queries, methodology |
| **Retriever** | Searches ChromaDB + web for relevant papers | Research plan | Ranked paper list with abstracts and relevance scores |
| **Summarizer** | Synthesizes retrieved papers into themes | Paper list | Thematic summary with key findings per subtopic |
| **Gap Analyzer** | Identifies research gaps and opportunities | Thematic summary | 5-10 research gaps with severity, confidence, remediation |
| **Report Generator** | Produces structured final report | All agent outputs | Publication-quality report with citations, contradictions, executive summary |

---

## Security Architecture (Defense-in-Depth)

```
Layer 1: proxy.ts (Edge)
  - Reads JWT from auth_token cookie
  - Verifies HMAC-SHA256 signature
  - Validates exp and sub claims
  - Redirects to login if invalid

Layer 2: API Client Interceptor (Browser)
  - Attaches Bearer token to every request
  - Detects 401 responses, queues concurrent 401s
  - Silent token refresh via /auth/refresh

Layer 3: FastAPI Middleware (Backend)
  - Rate limiting with Redis (Lua scripting, TOCTOU-free)
  - Security headers (HSTS, CSP, XFO)
  - Structured JSON logging with correlation IDs

Layer 4: Service Layer (Backend)
  - JWT decode + signature verification
  - Token type check (access vs refresh)
  - Token version check (global invalidation)
  - RBAC enforcement (require_role)
  - Ownership verification (require_ownership)
```

---

## Data Model

```mermaid
erDiagram
    User ||--o{ Project : owns
    User ||--o{ ProjectMember : "is member"
    Project ||--o{ ProjectMember : contains
    Project ||--o{ Document : has
    Project ||--o{ Report : generates
    Project ||--o{ AgentExecution : runs
    Document ||--o{ Chunk : split-into
    Chunk ||--o{ Embedding : vectorized

    User {
        uuid id PK
        string email UK
        string username UK
        string password_hash
        string role
        bool is_active
        datetime created_at
    }

    Project {
        uuid id PK
        string title
        string description
        uuid owner_id FK
        datetime created_at
    }

    Document {
        uuid id PK
        string filename
        string file_type
        uuid project_id FK
        datetime uploaded_at
    }

    Report {
        uuid id PK
        uuid project_id FK
        uuid owner_id FK
        string title
        text content
        string format
        datetime generated_at
    }
```

---

## Key Design Decisions

1. **LangGraph over LangChain** — finer-grained control over agent state and workflow transitions
2. **proxy.ts over Next.js middleware** — avoids Next.js 16 middleware deprecation; provides custom JWT validation at edge
3. **Pluggable LLM providers** — supports OpenAI, Gemini, and Mock providers via strategy pattern
4. **Graceful degradation** — Redis, ChromaDB, and LLM failures don't crash the system; fallback modes maintain core functionality
5. **SQLAlchemy async** — non-blocking database access for high concurrency

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript 5.7, Tailwind CSS v4, Zustand |
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0, Pydantic v2 |
| AI/ML | LangGraph, ChromaDB, Gemini 2.0 Flash, OpenAI GPT-4o |
| Database | PostgreSQL 16, Redis 7 |
| Infrastructure | Docker, Docker Compose, GitHub Actions |
| Observability | Prometheus, Grafana, Sentry |
