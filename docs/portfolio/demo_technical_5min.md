# 5-Minute Technical Demo Script

## 1. Project Overview (1 minute)

"This is AARA — Agentic AI Research Assistant. It's a full-stack application that uses a multi-agent AI system to automate research workflows. The frontend is Next.js 16 with React 19, the backend is FastAPI with Python 3.12, and we use LangGraph for agent orchestration."

## 2. API Walkthrough (1.5 minutes)

"Let me show you the API. At /docs we have full OpenAPI documentation with 46 endpoints organized into 13 routers. The auth system uses JWT with HMAC-SHA256. Let me demonstrate:

- POST /auth/register creates a user with bcrypt-hashed password
- POST /auth/login returns access and refresh tokens with rotation
- GET /projects lists only the user's projects (ownership enforcement)

Notice the security headers on every response — HSTS, CSP, X-Frame-Options."

## 3. Agent System (1.5 minutes)

"The core of AARA is the LangGraph-based agent system. When a user submits a research query:

1. Planner Agent creates a structured research plan with subtopics and search queries
2. Retrieval Agent searches ChromaDB vector store using semantic similarity
3. Summarizer Agent synthesizes evidence into section summaries with citations
4. Gap Analysis Agent identifies missing knowledge and contradictions
5. Report Generator produces a publication-quality report with validation

Each agent runs in a LangGraph workflow with error handling, retry logic, and metrics recording."

## 4. Infrastructure & DevOps (1 minute)

"The system is fully containerized. The Dockerfile uses multi-stage builds — 200MB base with a non-root user and health checks. Docker Compose supports both dev (3 services) and staging (7 services with Redis, Prometheus, Grafana).

Monitoring includes:
- /health, /ready, /live endpoints for orchestration
- Prometheus metrics at /metrics with 12 custom metrics
- Pre-built Grafana dashboards
- Sentry error tracking
- Structured JSON logging with correlation IDs"

## 5. Testing & Quality (30 seconds)

"371 tests across 13 test files cover unit, integration, and E2E scenarios. GitHub Actions runs lint, type checking, security scanning with bandit and pip-audit, and Docker build verification on every push. k6 load testing covers 5 scenarios up to 500 concurrent users."
