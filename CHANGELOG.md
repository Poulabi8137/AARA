# Changelog

## [0.2.0] - 2026-06-17

### Final Polish & Launch Sprint
- Production-quality README with 30+ sections and live screenshots
- ARCHITECTURE.md with system diagrams and data model (ERD)
- ROADMAP.md with completed, short-term, medium-term, and long-term goals
- CASE_STUDY.md with architecture highlights, metrics, and sample workflows
- CODE_OF_CONDUCT.md for community standards
- Expanded .gitignore (18 → 38 entries) covering Python, Node, IDE, and OS artifacts
- Updated CHANGELOG.md with complete release history
- docs/ cleanup: archived 30+ temporary iteration reports to docs/archive/
- Screenshot capture: 13 pages verified across entire application
- Gemini API integration verified (2.5 Flash and 2.0 Flash, <0.5s latency)
- 13 benchmark queries executed (7 real Gemini, 6 template fallback)
- 10 IEEE papers generated (template fallback after quota exhaustion)
- 392/395 tests passing (2m03s execution, 3 skipped for PostgreSQL features)
- Removed middleware.ts (Next.js 16 deprecation), kept proxy.ts only
- Removed temp diagnostic scripts from repo root
- Deployment report, benchmark report, paper generation report, final validation report generated

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
