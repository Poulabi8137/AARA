# LinkedIn Project Description

## AARA — Agentic AI Research Assistant

**A production-grade, multi-agent AI research platform that autonomously conducts literature reviews, analyzes research gaps, and generates structured reports.**

### Technical Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, LangGraph, ChromaDB, Redis 7, Dramatiq

**Frontend:** Next.js 16, React 19, TypeScript 5.7, Tailwind CSS v4, Zustand, WebSockets

**Infrastructure:** Docker, Docker Compose, GitHub Actions, Prometheus, Grafana, Sentry, k6

### Key Engineering Achievements

- **46 REST endpoints** with JWT authentication (HMAC-SHA256), RBAC authorization (admin/researcher/viewer), and resource ownership enforcement
- **Multi-agent AI system** using LangGraph — 5 specialized agents collaborate to plan, retrieve, summarize, analyze gaps, and generate reports
- **Production security** — rate limiting with atomic Redis Lua scripts, security headers (HSTS, CSP), upload validation, prompt injection mitigation
- **Monitoring** — Prometheus + Grafana with 12 custom metrics, structured JSON logging with correlation IDs, Sentry error tracking, health check endpoints
- **CI/CD** — GitHub Actions with lint, type checking, security scanning (bandit, pip-audit, CodeQL, Trivy), Docker build verification, and k6 load testing
- **371 passing tests** — pytest-asyncio with mocked dependencies, 13 test files covering unit, integration, and E2E scenarios
- **Clean architecture** — API → Service → Data layers with dependency injection, Pydantic v2 schemas, Alembic migrations

### Impact

AARA transforms unstructured research queries into structured, evidence-grounded reports with citation tracking, contradiction detection, and gap analysis — demonstrating production-grade software engineering across the full stack.
