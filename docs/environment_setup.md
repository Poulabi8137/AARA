# AARA — Environment Setup Guide

## Overview

AARA requires environment variables for database, security, LLM, Redis, and observability. This guide covers development and production configuration.

---

## Backend Environment

Create `backend/.env` from the example:

```bash
cp .env.example backend/.env
# or copy manually
```

### Required Variables

```ini
# ── Database ──────────────────────────────────────────────
# Development (SQLite):
DATABASE_URL=sqlite+aiosqlite:///./aara.db

# Production (Neon PostgreSQL):
# DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.region.neon.tech/database?sslmode=require

# ── Security ──────────────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=your-64-char-random-secret

# ── CORS ──────────────────────────────────────────────────
# Development:
ALLOWED_ORIGINS=["http://localhost:3000"]
# Production:
# ALLOWED_ORIGINS=["https://aara.vercel.app"]

# ── LLM ───────────────────────────────────────────────────
# Gemini (free tier — recommended):
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your-key-from-aistudio.google.com

# OpenAI (paid alternative):
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o
# OPENAI_API_KEY=sk-...

# ── Redis ─────────────────────────────────────────────────
# Development (in-memory, no Redis needed):
REDIS_URL=memory

# Production (Upstash):
# REDIS_URL=rediss://default:password@region.upstash.io:6379
```

### Optional Variables

```ini
# Logging
LOG_LEVEL=INFO           # DEBUG for verbose output
LOG_FORMAT=json          # or "text" for development

# Database pool
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Security
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15

# Vector store (ChromaDB)
CHROMA_HOST=localhost
CHROMA_PORT=8001
VECTORSTORE_PERSIST_DIR=./chroma_data
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Workflow
WORKFLOW_MAX_RETRIES=3
WORKFLOW_NODE_TIMEOUT=120
REQUIRE_HUMAN_APPROVAL=false

# Observability
ENV=development
SENTRY_DSN=
```

---

## Frontend Environment

Create `.env.local` in the project root:

```ini
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8011/api

# JWT secret (MUST match backend SECRET_KEY for proxy.ts to verify tokens)
JWT_SECRET=must-match-backend-secret-key
```

### Production Frontend (Vercel)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://aara-api.onrender.com/api` |
| `JWT_SECRET` | Same as backend `SECRET_KEY` |

---

## Quick Start (Development)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set SECRET_KEY, GEMINI_API_KEY
uvicorn app.main:app --reload --port 8011
```

### Frontend

```bash
# From project root
npm install
npm run dev
```

### Docker (full stack with PostgreSQL + ChromaDB + Redis)

```bash
cd backend
docker compose up --build
```

---

## Checking Configuration

Verify your setup is correct:

```bash
# Backend
curl http://localhost:8011/health
# Expected: {"status":"healthy","services":{"database":"connected",...}}

# Frontend
curl http://localhost:3000
# Expected: HTML (200 OK)
```

---

## Common Issues

| Issue | Fix |
|-------|-----|
| `SECRET_KEY` too short | Generate with `secrets.token_urlsafe(48)` |
| CORS errors | Update `ALLOWED_ORIGINS` to match frontend URL |
| Gemini quota exhausted | Wait for daily reset (~07:00 UTC) or use `LLM_PROVIDER=mock` |
| Redis connection refused | Set `REDIS_URL=memory` for local dev without Redis |
| Alembic migration fails | Run `alembic upgrade head` from `backend/` directory |
| `proxy.ts` blocking routes | Set `JWT_SECRET` in `.env.local` matching backend `SECRET_KEY` |
