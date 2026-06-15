# Interview Talking Points

## Architecture & Design

- **Multi-agent AI system** using LangGraph — not just a single LLM call, but a directed graph of specialized agents (Planner, Retriever, Summarizer, Analyzer, Generator) with state management
- **Defense-in-depth security** — JWT at edge proxy, silent token refresh at client, rate limiting + security headers at middleware, RBAC + ownership enforcement at service layer
- **Clean architecture** — API layer → Service layer → Model/Database layer, with dependency injection throughout
- **46 REST endpoints** organized into 13 domain routers with consistent error handling

## Backend Engineering

- **FastAPI with async everywhere** — async SQLAlchemy sessions, async Redis, async ChromaDB
- **Pydantic v2 schemas** — request validation, response serialization, OpenAPI generation
- **SQLAlchemy 2.0 ORM** — 8 models with proper relationships, cascade deletes, connection pooling
- **Alembic migrations** — 5 migration versions for schema evolution
- **Structured logging** — JSON formatter with correlation IDs, request IDs, user context
- **Prometheus metrics** — 12 custom metrics covering HTTP, agents, LLM, database, errors

## DevOps & Infrastructure

- **Docker multi-stage builds** — 200MB runtime image, non-root user, health checks
- **Docker Compose** — dev (3 services) and staging (7 services with monitoring)
- **GitHub Actions** — 4 workflows: PR checks, main branch, security scan, load test
- **k6 load testing** — 5 scenarios: smoke, average (50 users), stress (300), spike (500), endurance (60 min)
- **Monitoring** — Prometheus + Grafana with pre-built dashboards, Sentry error tracking

## Security

- **JWT HMAC-SHA256** with configurable expiry, refresh rotation, token versioning
- **RBAC** — admin, researcher, viewer roles with endpoint-level enforcement
- **Ownership verification** on 20+ endpoints
- **Rate limiting** — Redis-backed sliding window with atomic Lua scripts (TOCTOU-free)
- **Upload security** — file size limit (10MB), filename sanitization, extension whitelist
- **Security headers** — HSTS, CSP, X-Frame-Options, X-Content-Type-Options, etc.
- **Prompt injection mitigation** — instruction delimiters, system rules

## Testing

- **371 tests** across 13 test files
- **pytest-asyncio** for async test support
- **Service mocking** — DB sessions, Redis, ChromaDB all mocked for unit tests
- **CI integration** — tests run with real PostgreSQL service in CI

## Challenges & Solutions

- **Challenge**: ChromaDB filter bug deleting wrong vectors on document removal
  - **Solution**: Fixed by passing correct `project_id` instead of `document.id`
- **Challenge**: Rate limiter TOCTOU race condition
  - **Solution**: Replaced Python ZCARD/ZADD with atomic Lua script
- **Challenge**: Inefficient COUNT query fetching all rows
  - **Solution**: Replaced `len(result.all())` with `select(func.count())`
- **Challenge**: Upload security — no size limits, no sanitization
  - **Solution**: Added configurable max_upload_size + filename sanitization + 413 response

## STAR Format Questions

### Situation
"AARA is an AI research platform where users query a multi-agent system to generate research reports."

### Task
"I needed to audit and harden the entire backend — security, database integrity, rate limiting, AI safety, and production readiness."

### Action
"I audited all 46 endpoints for auth/RBAC/ownership, fixed 2 missing auth checks, resolved a ChromaDB filter bug, replaced a TOCTOU rate limiter race condition with a Lua script, added upload security controls, applied prompt injection mitigation, and implemented comprehensive monitoring with Prometheus/Grafana."

### Result
"371 tests passing, zero critical or high-severity security findings, production-ready deployment with CI/CD, monitoring, and load testing infrastructure."
