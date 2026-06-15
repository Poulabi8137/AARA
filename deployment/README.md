# Deployment Guide

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js     │────▶│  Proxy       │────▶│  FastAPI     │
│  Frontend    │     │  (proxy.ts)  │     │  Backend     │
│  :3000       │     │  JWT Guard   │     │  :8000       │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌───────────────────────────┼───────────┐
                    │                           │           │
               ┌────▼────┐              ┌──────▼─────┐ ┌───▼────┐
               │PostgreSQL│              │  ChromaDB   │ │ Redis  │
               │  :5432   │              │  :8001      │ │ :6379  │
               └─────────┘              └────────────┘ └────────┘
```

## Prerequisites

- Docker & Docker Compose
- Python 3.12+ (for local dev)
- PostgreSQL 16 (for local dev)

## Local Development

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env  # Edit as needed
uvicorn app.main:app --reload --port 8000

# Frontend (root directory)
npm install
npm run dev
```

## Docker Deployment

### Development Stack

```bash
cd backend
docker compose up -d
```

This starts:
- `db`: PostgreSQL 16
- `chromadb`: Vector store
- `api`: FastAPI backend (auto-migrates on startup)

### Staging Stack

```bash
cd backend
docker compose -f docker-compose.staging.yml up -d
```

Additional services:
- `redis`: Cache & rate limiting
- `worker`: Dramatiq background task processor (2 replicas)
- `prometheus`: Metrics collection
- `grafana`: Dashboards & visualization

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | — | JWT signing key (min 32 chars) |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch` | PostgreSQL connection string |
| `OPENAI_API_KEY` | Optional | — | OpenAI API key |
| `GEMINI_API_KEY` | Optional | — | Google Gemini API key |
| `REDIS_URL` | No | `memory` | Redis connection string |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `ENV` | No | `development` | Environment name |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Production Checklist

- [ ] `SECRET_KEY` set to a cryptographically random 64-character string
- [ ] `DATABASE_URL` uses production PostgreSQL credentials
- [ ] `REDIS_URL` configured for production Redis
- [ ] HTTPS termination at reverse proxy / load balancer
- [ ] `ENV=production`
- [ ] `LOG_LEVEL=WARNING` (reduce log volume)
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Monitoring stack deployed (Prometheus + Grafana)
- [ ] Sentry DSN configured
- [ ] Backup strategy in place for PostgreSQL + ChromaDB volumes

## Security

- JWT tokens use HMAC-SHA256 with configurable expiry
- Token versioning allows global invalidation
- Refresh token rotation invalidates old tokens
- Rate limiting by user/IP with Redis-backed sliding window
- All passwords hashed with bcrypt
- CORS restricted to allowed origins
- Security headers set on every response (HSTS, CSP, X-Frame-Options, etc.)
- Filename sanitization on all uploads
- File size limited to 10 MB
- Non-root user in Docker container
