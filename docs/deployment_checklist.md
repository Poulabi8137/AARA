# AARA — Deployment Checklist

## Prerequisites

### Accounts (create before starting)
- [ ] [Vercel](https://vercel.com) — Frontend hosting (Free tier)
- [ ] [Render](https://render.com) — Backend API + ChromaDB (Free tier)
- [ ] [Neon](https://neon.tech) — PostgreSQL database (Free tier)
- [ ] [Upstash](https://upstash.com) — Redis (Free tier)
- [ ] [Google AI Studio](https://aistudio.google.com) — Gemini API key (Free tier)

### Local Tools
- [ ] Node.js 20+
- [ ] Python 3.12+
- [ ] Git
- [ ] Docker & Docker Compose (for local ChromaDB testing)

---

## Environment Variables

### Backend (`backend/.env` or Render dashboard)

| Variable | Source | Required |
|----------|--------|----------|
| `DATABASE_URL` | Neon dashboard → connection string | Yes |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` | Yes |
| `ALLOWED_ORIGINS` | `["https://aara.vercel.app"]` | Yes |
| `GEMINI_API_KEY` | Google AI Studio → API key | Yes |
| `REDIS_URL` | Upstash dashboard → REST URL | No (falls back to memory) |
| `SENTRY_DSN` | Sentry dashboard | No |
| `LLM_PROVIDER` | `gemini` (default) | No |
| `LLM_MODEL` | `gemini-2.0-flash` (default) | No |
| `LOG_LEVEL` | `INFO` (default) | No |

### Frontend (Vercel dashboard)

| Variable | Value | Required |
|----------|-------|----------|
| `NEXT_PUBLIC_API_URL` | `https://aara-api.onrender.com/api` | Yes |
| `JWT_SECRET` | Must match backend `SECRET_KEY` | Yes |

---

## Deployment Steps

### 1. Database — Neon
- [ ] Create a Neon project (any region)
- [ ] Copy the connection string (PostgreSQL with asyncpg)
- [ ] Save as `DATABASE_URL` for Render
- [ ] Run migrations: `alembic upgrade head`

### 2. Redis — Upstash
- [ ] Create a Redis database (any region)
- [ ] Copy the REST URL
- [ ] Save as `REDIS_URL` for Render

### 3. Backend — Render
- [ ] Create a new Web Service
- [ ] Connect your GitHub repository
- [ ] Choose "Docker" as runtime
- [ ] Set Dockerfile path: `backend/Dockerfile`
- [ ] Set health check path: `/health`
- [ ] Add all environment variables
- [ ] Deploy

### 4. ChromaDB — Render (optional, second service)
- [ ] Create a new Web Service
- [ ] Use `Dockerfile.chromadb`
- [ ] Set health check path: `/api/v1/heartbeat`
- [ ] Deploy

### 5. Frontend — Vercel
- [ ] Import GitHub repository
- [ ] Framework: Next.js
- [ ] Root directory: `./` (project root)
- [ ] Build command: `next build`
- [ ] Add environment variables
- [ ] Deploy

### 6. Verify
- [ ] Frontend loads: `https://aara.vercel.app`
- [ ] API responds: `https://aara-api.onrender.com/health`
- [ ] Login flow works
- [ ] Research workflow completes
- [ ] Report generation works
- [ ] Export works

---

## Post-Deployment

- [ ] Set up custom domain (optional)
- [ ] Enable HTTPS (automatic with Vercel + Render)
- [ ] Configure Sentry error tracking (optional)
- [ ] Set up database backups (Neon automatic)
- [ ] Monitor logs via Render dashboard
- [ ] Test with real Gemini API key

---

## Rollback Plan

1. **Frontend**: Vercel → Deployments → select previous deployment → Promote to Production
2. **Backend**: Render → Environment → point to previous Docker image tag
3. **Database**: Neon → Branches → create branch from pre-deployment point
4. **Redis**: Upstash → Backup → restore from latest backup
