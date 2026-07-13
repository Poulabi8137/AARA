# AARA — Agentic AI Research Assistant

**Showcase Document** — v1.0.0

---

## Project Overview

AARA transforms unstructured research queries into publication-quality reports via a coordinated team of 5 specialized LangGraph agents. Built with FastAPI, Next.js 16, and PostgreSQL, it's a production-grade platform demonstrating full-stack AI engineering, defense-in-depth security, and comprehensive testing.

```
User Query → Planner → Retriever → Summarizer → Gap Analyzer → Report Generator → Final Report
```

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js 16)                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐     │
│  │  React   │  │  proxy.ts│  │  Zustand State        │     │
│  │  UI      │  │ JWT Guard│  │  Management           │     │
│  └──────────┘  └──────────┘  └───────────────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP + JWT
┌──────────────────────▼──────────────────────────────────────┐
│                  Backend (FastAPI / Python 3.12)              │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐     │
│  │ API Layer│  │Middleware│  │  Auth Service         │     │
│  │46 Endpts │  │Rate Limit│  │  JWT + RBAC + Owner   │     │
│  └──────────┘  └──────────┘  └───────────────────────┘     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         LangGraph Agent System                        │  │
│  │  Planner → Retriever → Summarizer → Gap Analyzer     │  │
│  │                    → Report Generator                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐     │
│  │ Document │  │ LLM      │  │  Evaluation           │     │
│  │Ingestion │  │Providers │  │  Benchmark Suite      │     │
│  └──────────┘  └──────────┘  └───────────────────────┘     │
└──────┬──────────────┬──────────────┬───────────────────────┘
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

### Agent Workflow

| Step | Agent | Input → Output | Key Tech |
|------|-------|---------------|----------|
| 1 | **Planner** | Query → Research plan (subtopics, queries, methodology) | Few-shot prompting |
| 2 | **Retriever** | Plan → Ranked papers with relevance scores | ChromaDB semantic search |
| 3 | **Summarizer** | Papers → Thematic summaries per subtopic | LLM synthesis |
| 4 | **Gap Analyzer** | Themes → Research gaps (severity, confidence) | Structured classification |
| 5 | **Report Generator** | All outputs → Final report (3 formats, 4 citation styles) | Template + LLM |

---

## Key Achievements

### 🏆 Multi-Agent AI
- 5 specialized LangGraph agents with typed Pydantic state schemas
- Pluggable LLM providers (Gemini, OpenAI, Mock) with graceful degradation
- 13 benchmark queries against real Gemini API — 100% completion
- 10 IEEE-style papers generated (template fallback)
- Average report: 16,278 characters

### 🔒 Production Security
- 4-layer defense-in-depth authentication
- JWT access + refresh token rotation
- RBAC (Admin, Researcher, Viewer) + ownership enforcement
- Atomic Redis rate limiting (Lua scripts, TOCTOU-free)
- 10-phase security audit — zero critical findings

### ✅ Engineering Quality
- 392/395 tests passing (99.24%) in ~40s
- 46 API endpoints across 13 routers
- Docker multi-stage build (200MB, non-root user)
- 4 GitHub Actions CI/CD workflows
- 12 Prometheus metrics + Grafana dashboards
- 5 k6 load test scenarios (up to 500 users)

---

## Screenshots

| Page | Preview |
|------|---------|
| Landing | ![Landing](screenshots/landing.png) |
| Login | ![Login](screenshots/login.png) |
| Dashboard | ![Dashboard](screenshots/dashboard.png) |
| Research Papers | ![Papers](screenshots/research-papers.png) |
| Literature Review | ![Literature Review](screenshots/literature-review.png) |
| Gap Analysis | ![Gap Analysis](screenshots/gap-analysis.png) |
| Report Generation | ![Report Generation](screenshots/report-generation.png) |
| Citation Manager | ![Citation Manager](screenshots/citation-manager.png) |
| Agent Monitoring | ![Agent Monitoring](screenshots/agent-monitoring.png) |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TypeScript 5.7, Tailwind CSS v4, Zustand, Framer Motion |
| Backend | Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic v2, Alembic |
| AI/ML | LangGraph 0.2, ChromaDB 0.5, sentence-transformers, Google Gemini 2.0 Flash |
| Database | PostgreSQL 16 (asyncpg), Redis 7 (redis-py) |
| Infrastructure | Docker multi-stage, Docker Compose, GitHub Actions |
| Monitoring | Prometheus, Grafana, Sentry, k6 |
| Testing | pytest (392 tests), Playwright (13 screenshots) |

---

## Metrics Dashboard

```
┌─────────────────────────────┬───────────┐
│ Metric                      │ Value     │
├─────────────────────────────┼───────────┤
│ Test Suite                  │ 392/395   │
│ API Endpoints               │ 46        │
│ LangGraph Agents            │ 5         │
│ LLM Providers               │ 3         │
│ Security Layers             │ 4         │
│ Security Audit Phases       │ 10        │
│ Benchmark Queries (Real)    │ 13        │
│ Benchmark Completion        │ 100%      │
│ Docker Image Size           │ 200MB     │
│ CI/CD Workflows             │ 4         │
│ Load Test Scenarios         │ 5         │
│ Prometheus Metrics          │ 12        │
│ Screenshots Captured        │ 13        │
└─────────────────────────────┴───────────┘
```

---

## Demo Instructions

### Quick Start (Local)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY and GEMINI_API_KEY
uvicorn app.main:app --reload --port 8011

# Frontend (separate terminal)
npm install
npm run dev

# Open http://localhost:3000
```

### Docker (Full Stack)

```bash
cd backend
docker compose up --build
# Frontend: http://localhost:3000
# API:      http://localhost:8000/docs
```

### Demo Walkthrough

1. **Register** a new account at `/auth/signup`
2. **Login** at `/auth/login`
3. **Create a project** from the dashboard
4. **Start research**: enter a query like *"What are the latest advances in few-shot learning for NLP?"*
5. **Watch agents work** in the monitoring dashboard
6. **Review the gap analysis** and generated report
7. **Export** in any format (MD, JSON, HTML, PDF, DOCX)

---

## Portfolio Assets

| Asset | Location |
|-------|----------|
| Resume summary | [docs/showcase/portfolio/portfolio_description.md](docs/showcase/portfolio/portfolio_description.md) |
| Project highlights | [docs/showcase/portfolio/project_highlights.md](docs/showcase/portfolio/project_highlights.md) |
| Technical summary | [docs/showcase/portfolio/technical_summary.md](docs/showcase/portfolio/technical_summary.md) |
| Recruiter summary | [docs/showcase/portfolio/recruiter_summary.md](docs/showcase/portfolio/recruiter_summary.md) |
| Resume variants | [docs/showcase/resume/resume_variants.md](docs/showcase/resume/resume_variants.md) |
| Interview cheatsheet | [docs/showcase/resume/interview_cheatsheet.md](docs/showcase/resume/interview_cheatsheet.md) |
| STAR stories | [docs/showcase/portfolio/STAR_story.md](docs/showcase/portfolio/STAR_story.md) |
| LinkedIn posts | [docs/showcase/linkedin/linkedin_posts.md](docs/showcase/linkedin/linkedin_posts.md) |
| Demo scripts | [docs/showcase/demo/](docs/showcase/demo/) |
| GitHub images | [docs/showcase/github/](docs/showcase/github/) |
| Interview Q&A | [docs/showcase/interview/](docs/showcase/interview/) |
| Presentation slides | [docs/showcase/presentation/](docs/showcase/presentation/) |

---

## Links

- **Repository**: [GitHub](https://github.com/your-username/aara)
- **Documentation**: [docs/](docs/)
- **License**: MIT

---

*Built with FastAPI, Next.js, LangGraph, and a lot of curiosity about what happens when you let AI agents plan their own research.*
