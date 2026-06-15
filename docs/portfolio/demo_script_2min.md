# 2-Minute Recruiter Demo Script

## Opening (15 seconds)

"AARA is a production-grade AI research assistant platform. It uses a multi-agent AI system with LangGraph to automatically conduct literature reviews, analyze research gaps, and generate structured reports."

## Architecture (30 seconds)

"The backend is a FastAPI service with 46 endpoints, JWT authentication with refresh rotation, RBAC authorization, and Redis-backed rate limiting. PostgreSQL stores relational data, ChromaDB handles vector embeddings for semantic search, and the entire system is containerized with Docker."

## Key Technical Highlights (45 seconds)

"On the security side, we have multi-layered defense — JWT at the proxy, token rotation at the client, backend middleware for rate limiting and security headers, and RBAC with ownership enforcement at the service layer. All logging is structured JSON for ELK/Loki integration, and we have full Prometheus/Grafana monitoring with pre-built dashboards."

## Testing & CI/CD (20 seconds)

"371 tests pass with 3 skipped due to ChromaDB availability. We have GitHub Actions CI/CD with lint, type checking, security scanning, and Docker build verification. Load testing with k6 covers smoke, average, stress, spike, and endurance scenarios."

## Closing (10 seconds)

"Full documentation, architecture diagrams, OpenAPI spec at /docs, and production deployment guide included. The codebase demonstrates production-ready software engineering practices end-to-end."
