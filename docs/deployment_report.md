# Deployment Report

**Date:** 2026-06-17  
**Status:** Pre-Deployment — Configuration Complete  

---

## Deployment Stack

| Service | Provider | Purpose |
|---------|----------|---------|
| Frontend | Vercel | Next.js 16.2.6 hosting |
| Backend | Render | FastAPI with uvicorn |
| Database | Neon | PostgreSQL 16 (serverless) |
| Cache | Upstash | Redis 7 (serverless) |
| LLM | Gemini | AI Studio free tier key |
| Vector DB | ChromaDB | In-process or hosted |

---

## Configuration

### Environment Variables (All Services)

```bash
# Backend (Render)
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(48))">
ALLOWED_ORIGINS=["https://app.vercel.app"]
LOG_LEVEL=INFO
DEBUG=false
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=AIza...
REDIS_URL=rediss://default:password@region.upstash.io:6379

# Frontend (Vercel)
NEXT_PUBLIC_API_URL=https://api.render.com/api
JWT_SECRET=<must match backend SECRET_KEY>
```

---

## Current Local Deployment

| Component | Status | URL |
|-----------|--------|-----|
| Backend | ✅ Running | http://localhost:8011 |
| Frontend | ✅ Running | http://localhost:3000 |
| Database | ✅ SQLite | `backend/aara.db` |
| LLM | ✅ Gemini | Model: gemini-2.0-flash |
| Screenshots | ✅ Captured | `screenshots/` (13 files) |

---

## Deployment Steps

### Backend (Render)

1. Create a Web Service on Render (Docker)
2. Set `Dockerfile` path: `backend/Dockerfile`
3. Add environment variables from `.env` (without `memory` Redis — use Upstash URL)
4. Deploy

### Frontend (Vercel)

1. Connect GitHub repo to Vercel
2. Set `NEXT_PUBLIC_API_URL` to Render backend URL
3. Set `JWT_SECRET` to match backend `SECRET_KEY`
4. Deploy

### Database (Neon)

1. Create Neon project (free tier)
2. Get connection string
3. Set as `DATABASE_URL` in Render
4. Run migrations (Alembic or `create_all()`)

### Cache (Upstash)

1. Create Upstash Redis (free tier, 100MB)
2. Get `REDIS_URL` (rediss://)
3. Set as `REDIS_URL` in Render

---

## Verification Checklist

- [ ] Backend health endpoint responds (Render URL)
- [ ] Frontend loads (Vercel URL)
- [ ] Login/Signup flow works
- [ ] Dashboard loads with projects
- [ ] Research pipeline executes
- [ ] Paper generation produces IEEE output
- [ ] Citations validate
- [ ] Evidence validates
- [ ] PDF export works
- [ ] DOCX export works
