# Changelog

## [0.1.0] - 2026-06-15

### Security
- JWT authentication with access + refresh token rotation
- HMAC-SHA256 signature verification at proxy and backend layers
- Silent token refresh with concurrent 401 request queueing
- Fail-closed proxy — missing JWT_SECRET blocks all requests
- Cross-tab authentication state synchronization
- RBAC with Admin, Researcher, Viewer roles
- Ownership validation on all project and execution endpoints
- Startup validation of SECRET_KEY (rejects empty/default/short keys)
- Token version support for global invalidation

### Features
- Multi-agent research pipeline (Planner, Retriever, Summarizer, Analyzer, Generator)
- LangGraph agent workflow orchestration with state management
- Evidence panels with confidence scores, source citations, and agent reasoning
- Literature review synthesis with theme extraction
- Research gap analysis with severity classification
- Novel direction generation grounded in identified gaps
- Template-based report generation (academic, executive, comprehensive)
- Citation management (APA, MLA, Chicago, BibTeX)
- Real-time agent execution monitoring dashboard
- Docker Compose deployment for full stack

### Infrastructure
- FastAPI backend with async SQLAlchemy + PostgreSQL
- Next.js 16 frontend with App Router and proxy.ts
- Pluggable LLM providers (OpenAI, Gemini, Mock)
- ChromaDB vector store for semantic paper search
- Prometheus + Grafana monitoring stack (staging)
- 360+ pytest tests covering auth, API, security, and agent workflows
