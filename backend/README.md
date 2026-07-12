# AARA API

FastAPI backend for the AARA platform — multi-agent research orchestration, JWT + RBAC security, PostgreSQL persistence, and LLM integration.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
# API at http://localhost:3000, docs at http://localhost:8000/docs
```

## Production Deployment

For production deployment, copy the template and populate with secrets from your deployment platform:

```bash
cp .env.production.example .env.production
# Edit .env.production to add your secrets from deployment platform variables
# Example deployment commands (replace with your actual commands):
# docker compose -f docker-compose.production.yml up --build
# # Or use your deployment platform's secrets injection mechanism
```

See [production.md](../production.md) for detailed deployment instructions.

## Environment Configuration

### Local Development

Use `.env.example` for local development:

```bash
# Copy development template
cp .env.example .env
# Edit .env for local development
e.g., DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aara
```

### Production Deployment

Use `.env.production.example` for production:

```bash
# Copy production template
cp .env.production.example .env.production
# Production secrets are injected via deployment platform
# Never commit secrets to version control
```

### Environment Variables

| File | Purpose | Secrets | Use Case |
|------|---------|---------|----------|
| `.env.example` | Local development template | Placeholder values | Local development |
| `.env.production.example` | Production configuration template | Placeholder values | Production deployment |
| `.env` | Local development configuration | Local secrets | Local development |
| `.env.production` | Production configuration | Production secrets | Production deployment |

## File Security

Both `.env.example` and `.env.production.example` contain placeholder values only and should never be committed with actual secrets. The actual secrets should be injected by your deployment platform using one of these methods:

- Kubernetes secrets
- AWS Secrets Manager
- Docker secrets
- Environment variables
- Terraform variables

See [production.md](../production.md) for deployment details.

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
pytest -v                    # 395 tests (392 passing)
pytest tests/test_security   # Auth-specific tests
```

## Environment

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SECRET_KEY` | Yes | — | JWT signing key (32+ chars) |
| `DATABASE_URL` | No | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` | CORS allowed domains |
| `LLM_PROVIDER` | No | `mock` | OpenAI, Gemini, Anthropic, or mock |

## Environment Files

- **`.env.example`**: Local development template (keep .gitignore'd)
- **`.env.production.example`**: Production configuration template (keep .gitignore'd)
- **`.env`**: Local development configuration (keep .gitignore'd)

### Usage

Local Development:
```bash
# Copy development template and edit
cp .env.example .env
# Edit .env with local database credentials, API keys, etc.
docker compose up --build
```

Production Deployment:
```bash
# Copy production template and edit with deployment platform secrets
cp .env.production.example .env.production
# Edit .env.production using secrets injected by your deployment platform
# Use environment variables: kubectl create secret, docker secrets, etc.
# Deploy using your infrastructure-as-code (Terraform, Kubernetes, etc.)
```

For full documentation, see the [root README](../README.md).
