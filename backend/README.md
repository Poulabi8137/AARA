# AgentWatch API

FastAPI backend for the AARA platform — multi-agent research orchestration, JWT + RBAC security, PostgreSQL persistence, and LLM integration.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
# API at http://localhost:8000, docs at http://localhost:8000/docs
```

## Key Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register |
| POST | `/auth/login` | No | Login |
| POST | `/auth/refresh` | No | Rotate tokens |
| GET | `/auth/me` | JWT | Current user |
| GET/POST | `/projects` | JWT | List/create projects |
| GET/PUT/DELETE | `/projects/{id}` | JWT+Owner | CRUD project |

## Architecture

```
FastAPI → JWT Middleware → Service Layer → SQLAlchemy async → PostgreSQL
                                    ↓
                              Agent Orchestrator → LLM (OpenAI / Gemini / Mock)
                                    ↓
                              ChromaDB (vector store)
```

## Stack

- **Framework:** FastAPI (Python 3.12), SQLAlchemy 2.0 async
- **Auth:** JWT (access + refresh tokens), RBAC (admin/researcher/viewer), ownership validation
- **AI:** LangGraph agent workflows, OpenAI / Gemini / Mock providers
- **Infra:** PostgreSQL 16, ChromaDB, Redis (optional), Docker Compose
- **Observability:** Structured JSON logging, Prometheus metrics, Grafana dashboards

## Tests

```bash
pytest -v                    # 360+ tests
pytest tests/test_security   # Auth-specific tests
```

## Environment

| Variable | Required | Default |
|----------|----------|---------|
| `SECRET_KEY` | Yes | — |
| `DATABASE_URL` | No | `postgresql+asyncpg://...` |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` |

For full documentation, see the [root README](../README.md).
