# Resume Bullet Suggestions

## Software Engineering

- Architected and built a production-grade FastAPI backend with 46 REST endpoints, JWT authentication with refresh token rotation, RBAC authorization, and resource ownership enforcement
- Implemented a multi-agent AI research system using LangGraph with 5 specialized agents (Planner, Retriever, Summarizer, Analyzer, Generator) orchestrating research workflows
- Designed a defense-in-depth security architecture with rate limiting, security headers, CORS, input validation, prompt injection mitigation, and upload security controls
- Built 13 Python Pydantic v2 schemas with automatic OpenAPI documentation generation
- Achieved 371 passing tests across 13 test files with pytest-asyncio and mocked service dependencies

## DevOps & Infrastructure

- Containerized the application with Docker multi-stage builds achieving 200MB runtime images with non-root users and health checks
- Configured Docker Compose stacks for development (3 services) and staging (7 services including Redis, Prometheus, Grafana)
- Designed GitHub Actions CI/CD with 4 workflows: PR checks, main branch build, security scanning (bandit, pip-audit, CodeQL, Trivy), and load testing
- Implemented k6 load testing framework with 5 scenarios: smoke, average (50 users), stress (300 users), spike (500 users), and endurance (60 minutes)

## Monitoring & Observability

- Implemented structured JSON logging with correlation IDs, request IDs, and user context across all microservices
- Built Prometheus metrics instrumentation with 12 custom metrics tracking HTTP, agents, LLM, database, errors, and auth failures
- Configured Grafana dashboards with pre-built visualizations for system health, API performance, and business metrics
- Implemented health check endpoints (/health, /ready, /live) for container orchestration
- Integrated Sentry error tracking with FastAPI and SQLAlchemy instrumentation

## Security Engineering

- Audited 46 API endpoints for authentication, RBAC, and ownership compliance — fixed 2 missing auth checks
- Resolved a TOCTOU race condition in Redis-based rate limiter by replacing Python ZCARD/ZADD with an atomic Lua script
- Patched a ChromaDB filter bug that caused incorrect vector deletion during document removal
- Optimized database query performance by replacing N+1 COUNT patterns with efficient SQL aggregation
- Added upload security controls: configurable file size limits (10MB), filename sanitization, extension whitelist
- Implemented prompt injection mitigation with instruction delimiters and system-level guards
