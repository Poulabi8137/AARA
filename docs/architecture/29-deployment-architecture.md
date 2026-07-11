# Document 29 — Deployment Architecture

## Development Environment (Docker Compose)

```yaml
# docker-compose.yml

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_SUPABASE_URL=${SUPABASE_URL}
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:aara_dev@postgres:5432/aara
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - JOB_QUEUE_BACKEND=local
      - ENV=development
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_started
      redis:
        condition: service_started

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: python -m app.jobs.worker
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:aara_dev@postgres:5432/aara
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - JOB_QUEUE_BACKEND=arq
      - ENV=development
    depends_on:
      - backend

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: aara
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: aara_dev
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"  # REST
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
  qdrant_data:
```

## Production Environment (Railway)

```mermaid
graph TB
    subgraph "Railway Project: aara"
        FE[Frontend Service<br/>Next.js SSR<br/>Port 3000]
        BE[Backend Service<br/>FastAPI + Uvicorn<br/>Port 8000]
        WK[Worker Service<br/>ARQ Job Queue]
        
        FE -->|HTTP| BE
        BE -->|Enqueue| WK
    end

    subgraph "Supabase (External)"
        PG[(PostgreSQL)]
        AUTH[Auth Service]
        STORAGE[File Storage]
    end

    subgraph "Qdrant (External)"
        QD[(Vector DB)]
    end

    subgraph "Redis (External)"
        RD[(Job Queue)]
    end

    subgraph "External APIs"
        LLM[LLM Providers<br/>OpenAI/Gemini/Groq]
        RS[Research APIs<br/>SS/arXiv/Crossref]
    end

    BE --> PG
    BE --> QD
    BE --> RD
    BE --> LLM
    BE --> RS
    BE --> AUTH
    WK --> PG
    WK --> QD
    WK --> RD
    WK --> LLM
    FE --> AUTH
```

## Dockerfile (Production)

### Backend
```dockerfile
# backend/Dockerfile

FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-deps -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    pandoc \
    texlive-latex-base \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend
```dockerfile
# frontend/Dockerfile

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000
CMD ["npm", "start"]
```

## Environment Variables

| Variable | Dev | Production | Secret |
|---|---|---|---|
| `DATABASE_URL` | local PostgreSQL | Supabase PostgreSQL URL | ✅ |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant Cloud URL | — |
| `QDRANT_API_KEY` | (empty) | Qdrant API key | ✅ |
| `REDIS_URL` | `redis://localhost:6379` | Redis Cloud URL | ✅ |
| `SUPABASE_URL` | Supabase project URL | Same | — |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Same | ✅ |
| `OPENAI_API_KEY` | User-provided or dev key | User-provided | ✅ |
| `JOB_QUEUE_BACKEND` | `local` | `arq` | — |
| `ENCRYPTION_KEY` | Dev key | Secure generated key | ✅ |
| `ENV` | `development` | `production` | — |
| `LOG_LEVEL` | `DEBUG` | `INFO` | — |
| `MONTHLY_BUDGET_DEFAULT` | `5.00` | `5.00` | — |
| `CORS_ORIGINS` | `http://localhost:3000` | Production domain | — |

## Railway Configuration

```json
// railway.json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "backend/Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 10,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

## Scaling Strategy

| Component | Scale Method | Limit |
|---|---|---|
| Backend | Increase `--workers` | 4 per instance (Railway limit) |
| Worker | Increase replicas | 2-3 replicas |
| Frontend | Static export + CDN | Railway handles |
| Qdrant | Upgrade Cloud tier | Free: 1GB, $0 until needed |
| PostgreSQL | Supabase upgrade | Free: 500MB, $0 until needed |

## Trade-offs

| Decision | Alternative | Rationale |
|---|---|---|
| Single Railway project | Separate Vercel + Railway | Simpler deployment, single CI/CD, less config |
| Docker Compose for dev | Manual service setup | Reproducible environment; new contributors run one command |
| Supabase external | Self-hosted PostgreSQL | Zero-ops database; free tier sufficient for MVP |
| Qdrant Cloud (free) | Self-hosted Qdrant | Free 1GB cluster; avoids managing another container |
| Railway autoscaling disabled | Kubernetes | Overkill for student project; manual scale when needed |
