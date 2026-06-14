# AgentWatch Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2026-06-13

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Environment Variables Reference](#2-environment-variables-reference)
3. [Quick Start (Local Development)](#3-quick-start-local-development)
4. [Staging Deployment](#4-staging-deployment)
5. [Production Deployment](#5-production-deployment)
6. [Docker Setup](#6-docker-setup)
7. [Scaling Guidelines](#7-scaling-guidelines)
8. [Monitoring Setup](#8-monitoring-setup)
9. [Backup Procedures](#9-backup-procedures)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Runtime |
| PostgreSQL | 16+ | Primary database |
| Redis | 7+ | Caching, rate limiting, task queue |
| Docker | 24+ | Containerization (optional but recommended) |
| Docker Compose | 2.20+ | Multi-service orchestration |
| Alembic | 1.13+ | Database migrations |

### Infrastructure Requirements

- **Development:** 4 GB RAM, 2 CPU cores, 20 GB disk
- **Staging:** 8 GB RAM, 4 CPU cores, 50 GB disk
- **Production:** 16 GB RAM minimum, 8 CPU cores, 100 GB+ SSD disk

### Accounts & Credentials

- OpenAI API key (for LLM provider)
- Gemini API key (optional, for multi-provider setup)
- Sentry DSN (optional, for error tracking)
- Docker Hub / container registry account (for image storage)

---

## 2. Environment Variables Reference

### Core Application

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_NAME` | `AgentWatch API` | No | Application display name |
| `ENV` | `development` | No | Runtime environment (`development`, `staging`, `production`) |
| `DEBUG` | `false` | No | Enable debug mode (verbose errors, hot reload) |
| `LOG_LEVEL` | `INFO` | No | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | `json` | No | Log output format: `json` or `text` |
| `SECRET_KEY` | `change-me-in-production` | **Yes** | JWT signing secret (min 32 chars, use `openssl rand -hex 32`) |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | **Yes** | CORS origins as JSON array |
| `CORS_ALLOW_CREDENTIALS` | `true` | No | Allow credentials in CORS |

### Database

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://agentwatch:agentwatch@localhost:5432/agentwatch` | **Yes** | Async PostgreSQL connection string |
| `DATABASE_ECHO` | `false` | No | Log all SQL queries |
| `DATABASE_POOL_SIZE` | `10` | No | SQLAlchemy connection pool size |
| `DATABASE_MAX_OVERFLOW` | `20` | No | Max overflow connections beyond pool size |

### Authentication & Security

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | No | JWT refresh token TTL |
| `ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `TOKEN_VERSION` | `1` | No | Increment to invalidate all existing tokens |
| `PASSWORD_MIN_LENGTH` | `8` | No | Minimum password length |
| `PASSWORD_MAX_LENGTH` | `128` | No | Maximum password length |
| `MAX_LOGIN_ATTEMPTS` | `5` | No | Failed attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | No | Lockout duration after max attempts |
| `RESET_TOKEN_EXPIRE_HOURS` | `1` | No | Password reset token TTL |
| `REQUIRE_EMAIL_VERIFICATION` | `false` | No | Require email verification before login |

### LLM Provider

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LLM_PROVIDER` | `mock` | No | Provider: `mock`, `openai`, or `gemini` |
| `LLM_MODEL` | `gpt-4o` | No | Model name for the provider |
| `LLM_TEMPERATURE` | `0.0` | No | LLM temperature (0.0–2.0) |
| `LLM_MAX_TOKENS` | `4096` | No | Max output tokens |
| `OPENAI_API_KEY` | `` | When using OpenAI | OpenAI API key |
| `GEMINI_API_KEY` | `` | When using Gemini | Google Gemini API key |

### Redis / Caching

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `REDIS_URL` | `memory` | No | Redis connection string (use `memory` for in-process fallback) |
| `REDIS_POOL_SIZE` | `10` | No | Redis connection pool size |
| `REDIS_MAX_RETRIES` | `3` | No | Max retry attempts for Redis operations |
| `REDIS_SOCKET_TIMEOUT` | `5` | No | Redis socket timeout in seconds |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5` | No | Redis connect timeout in seconds |
| `REDIS_HEALTH_CHECK_INTERVAL` | `30` | No | Redis health check interval in seconds |
| `DEFAULT_CACHE_TTL` | `300` | No | Default cache TTL in seconds |

### Vector Store / Documents

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CHROMA_HOST` | `localhost` | No | ChromaDB hostname |
| `CHROMA_PORT` | `8000` | No | ChromaDB port |
| `VECTORSTORE_PERSIST_DIR` | `./chroma_data` | No | ChromaDB persistence directory |
| `VECTORSTORE_COLLECTION_COUNT` | `5` | No | Max vector collections |
| `CHUNK_SIZE` | `1000` | No | Document chunk size (characters) |
| `CHUNK_OVERLAP` | `200` | No | Chunk overlap (characters) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | No | Embedding model name |

### Workflow / Agents

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `WORKFLOW_MAX_RETRIES` | `3` | No | Max retries per workflow node |
| `WORKFLOW_NODE_TIMEOUT` | `120` | No | Node timeout in seconds |

### Observability

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SENTRY_DSN` | `` | No | Sentry project DSN |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | No | Sentry traces sample rate (0.0–1.0) |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.0` | No | Sentry profiling sample rate (0.0–1.0) |

### Secret Management

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SECRETS_BACKEND` | `env` | No | Backend: `env`, `aws`, `azure`, `gcp` |
| `AWS_SECRET_NAME` | `agentwatch/production` | When using AWS | AWS Secrets Manager secret name |
| `AWS_REGION` | `us-east-1` | When using AWS | AWS region |
| `AZURE_KEY_VAULT_URL` | `` | When using Azure | Azure Key Vault URL |
| `GCP_PROJECT_ID` | `` | When using GCP | GCP project ID |

---

## 3. Quick Start (Local Development)

### Option A: Docker (Recommended)

```bash
# Clone and enter the repository
cd backend

# Copy environment file
cp .env.example .env
# Edit .env: set SECRET_KEY, OPENAI_API_KEY if needed

# Build and start all services
docker compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option B: Local Python

```bash
# Prerequisites: PostgreSQL 16 running locally, Redis running locally

cd backend

# Create virtual environment
python -m venv venv

# Windows
venv\Scripts\Activate.ps1
# Linux/Mac
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, SECRET_KEY

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}
```

---

## 4. Staging Deployment

### Infrastructure

- **Purpose:** Pre-production validation, integration testing, UAT
- **Environment:** Isolated VPS or Kubernetes namespace
- **Domain:** `staging.agentwatch.ai`
- **SSL:** Let's Encrypt via reverse proxy (nginx/Caddy)

### Using Docker Compose (Staging)

```bash
# Set required environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export STAGING_DB_PASSWORD=$(openssl rand -hex 16)
export OPENAI_API_KEY="sk-..."
export SENTRY_DSN="https://..."

# Deploy
docker compose -f docker-compose.staging.yml up --build -d

# Verify
curl -f https://staging.agentwatch.ai/health
```

### Manual Staging Setup

```bash
# Create database
createdb agentwatch_staging

# Run migrations
alembic upgrade head

# Start with uvicorn (4 workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --limit-concurrency 100
```

### Staging Checklist

- [ ] Environment variables set for staging (not defaults)
- [ ] Strong `SECRET_KEY` generated (`openssl rand -hex 32`)
- [ ] Database password overridden
- [ ] `REQUIRE_EMAIL_VERIFICATION=true`
- [ ] `ALLOWED_ORIGINS` set to staging domain
- [ ] Sentry DSN configured with staging project
- [ ] Debug routes disabled (`DEBUG=false`)
- [ ] Rate limiting enabled (default is enabled)
- [ ] Monitoring stack (Prometheus + Grafana) deployed
- [ ] Health check endpoint accessible

---

## 5. Production Deployment

### Infrastructure Requirements

- **Minimum:** 2 instances behind load balancer (HA)
- **Database:** PostgreSQL 16 with HA (RDS, Cloud SQL, or self-managed with Patroni)
- **Redis:** Redis 7 with sentinel or cluster mode
- **ChromaDB:** Dedicated instance with persistent volume
- **Reverse Proxy:** nginx or Cloudflare with WAF
- **CDN:** Optional, for static assets

### Production Architecture

```
                         ┌─────────────┐
                         │  Cloudflare  │
                         │  / AWS WAF   │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │   nginx      │
                         │  (TLS term)  │
                         └──────┬──────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              ┌─────▼────┐ ┌───▼───┐ ┌───▼───┐
              │  API      │ │ API   │ │ API   │
              │ Instance1 │ │Inst.2 │ │Inst.3 │
              └─────┬────┘ └───┬───┘ └───┬───┘
                    │           │           │
         ┌──────────┴───────────┴───────────┴──────────┐
         │                   │                         │
   ┌─────▼──────┐    ┌──────▼──────┐    ┌─────────────▼──┐
   │ PostgreSQL │    │   Redis 7   │    │   ChromaDB     │
   │  (Primary) │    │  (Cluster)  │    │  (Persistent)  │
   └─────┬──────┘    └─────────────┘    └────────────────┘
         │
   ┌─────▼──────┐
   │ PostgreSQL │
   │  (Replica) │
   └────────────┘
```

### Deployment Steps

#### Step 1: Database Setup

```sql
-- Create production database
CREATE DATABASE agentwatch_prod;
CREATE USER agentwatch_prod WITH PASSWORD '<strong-password>';
GRANT ALL PRIVILEGES ON DATABASE agentwatch_prod TO agentwatch_prod;

-- Create read-only user for replicas
CREATE USER agentwatch_readonly WITH PASSWORD '<strong-password>';
GRANT CONNECT ON DATABASE agentwatch_prod TO agentwatch_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agentwatch_readonly;
```

#### Step 2: Environment Configuration

```bash
cat << 'EOF' > /etc/agentwatch/production.env
ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

SECRET_KEY=<openssl rand -hex 32>
ALLOWED_ORIGINS=["https://app.agentwatch.ai", "https://admin.agentwatch.ai"]

DATABASE_URL=postgresql+asyncpg://agentwatch_prod:<password>@db-primary:5432/agentwatch_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

REDIS_URL=redis://redis-cluster:6379/0
REDIS_POOL_SIZE=20

LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=<your-key>

CHROMA_HOST=chromadb-prod
CHROMA_PORT=8000

SENTRY_DSN=<production-dsn>
SENTRY_TRACES_SAMPLE_RATE=0.1

REQUIRE_EMAIL_VERIFICATION=true
PASSWORD_MIN_LENGTH=12
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15

SECRETS_BACKEND=env
EOF
```

#### Step 3: Deploy API Instances

```yaml
# docker-compose.production.yml (partial)
services:
  api:
    image: registry.agentwatch.ai/agentwatch-api:${TAG}
    env_file: /etc/agentwatch/production.env
    restart: always
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "4"
          memory: "8g"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
```

#### Step 4: SSL / TLS

```bash
# Using nginx + certbot
server {
    listen 443 ssl http2;
    server_name app.agentwatch.ai;

    ssl_certificate /etc/letsencrypt/live/app.agentwatch.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.agentwatch.ai/privkey.pem;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Production Launch Checklist

See [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) for the full 50+ item checklist.

---

## 6. Docker Setup

### Building the Image

```bash
# Production build
docker build -t agentwatch-api:latest .

# With version tag
docker build -t registry.agentwatch.ai/agentwatch-api:1.0.0 .

# Multi-arch build (for ARM deployments)
docker buildx build --platform linux/amd64,linux/arm64 -t agentwatch-api:latest .
```

### Docker Compose Profiles

| Profile | File | Purpose |
|---------|------|---------|
| Development | `docker-compose.yml` | Local dev with hot reload |
| Staging | `docker-compose.staging.yml` | Pre-production validation |
| Production | `docker-compose.production.yml` | Production deployment |

### Image Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `staging` | Latest staging build |
| `1.x.x` | Semantic version tags |
| `sha-<commit>` | Specific commit build |

---

## 7. Scaling Guidelines

### Horizontal Scaling (API)

- Run 3+ API instances behind a load balancer
- Stateless design — sessions use JWT, not server-side storage
- Shared PostgreSQL and Redis across instances
- Each instance handles 500+ concurrent requests

### Database Scaling

- **Read replicas:** Offload read queries to replicas
- **Connection pooling:** Use PgBouncer or built-in pool (current: max_overflow=40)
- **Indexing:** Ensure all queried columns are indexed
- **Archival:** Archive sessions and reports older than 90 days

### Redis Scaling

- **Memory:** Monitor `used_memory_rss`; keep below 75% of total
- **Cluster mode:** For production, use Redis Cluster with 3+ nodes
- **Eviction policy:** `allkeys-lru` for cache, `noeviction` for task queue

### ChromaDB Scaling

- **Collection limits:** Keep under 100 collections per instance
- **Embedding dimensions:** Use 384-dim models for efficiency
- **Batch indexing:** Index documents in batches of 100

### Worker Scaling

- Start with 2 workers, each with 8 threads
- Monitor queue depth via Prometheus (`queue_depth`)
- Add workers when queue consistently exceeds 100

### Resource Planning

| Users (concurrent) | API Instances | Worker Instances | DB CPU | DB RAM |
|--------------------|---------------|------------------|--------|--------|
| 0–100 | 2 | 1 | 2 cores | 4 GB |
| 100–1,000 | 4 | 2 | 4 cores | 16 GB |
| 1,000–10,000 | 8 | 4 | 8 cores | 32 GB |
| 10,000+ | 16+ | 8+ | 16+ cores | 64+ GB |

---

## 8. Monitoring Setup

### Prometheus Metrics

All metrics exposed at `/metrics` endpoint:

**HTTP Metrics:**
- `http_requests_total{method,path,status}` — request count
- `http_request_duration_seconds{method,path}` — latency histogram

**Workflow Metrics:**
- `workflow_duration_seconds{status}` — workflow execution time
- `agent_duration_seconds{agent_name,status}` — per-agent time
- `active_workflows` — current concurrent workflows

**LLM Metrics:**
- `llm_request_duration_seconds{provider}` — provider latency

**Database:**
- `db_query_duration_seconds{operation}` — query latency histogram

**Business Metrics:**
- `auth_failures_total{reason}` — auth failure count
- `rate_limit_violations_total{client_type,path}` — rate limit hits
- `queue_depth{queue_name}` — task queue depth
- `errors_total{error_type,service}` — error count by type

### Alerting Rules (Prometheus + Alertmanager)

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | `error_rate > 5%` for 5m | Critical |
| HighAPILatency | `p99 > 5s` for 5m | Warning |
| HighAuthFailureRate | `auth_failures > 10/s` for 5m | Warning |
| WorkflowFailures | `workflow failures > 0` for 5m | Critical |
| QueueDepthHigh | `queue_depth > 100` for 5m | Warning |
| InstanceDown | `up == 0` for 1m | Critical |
| RateLimitViolationSpike | `violations > 50/s` for 5m | Warning |

### Grafana Dashboards

1. **API Overview:** Request rate, error rate, p50/p95/p99 latency, active users
2. **Workflows:** Execution count, success/failure rate, duration, agent breakdown
3. **Database:** Connection count, query latency, cache hit ratio
4. **LLM:** Provider latency, token usage, cost per request
5. **Infrastructure:** CPU, memory, disk, network per service

### Logging

- **Format:** Structured JSON (see `app/core/logging.py`)
- **Log levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Shipping:** Filebeat → Elasticsearch or Loki for production
- **Retention:** 30 days operational logs, 1 year audit logs

---

## 9. Backup Procedures

### Database (PostgreSQL)

```bash
# Daily full backup
pg_dump -U agentwatch_prod -h localhost agentwatch_prod | gzip > /backups/db/agentwatch_$(date +%Y%m%d).sql.gz

# Automated (cron)
0 2 * * * pg_dump -U agentwatch_prod -h localhost agentwatch_prod | gzip > /backups/db/agentwatch_$(date +\%Y\%m\%d).sql.gz && find /backups/db -mtime +30 -delete

# Restore
gunzip -c /backups/db/agentwatch_20260613.sql.gz | psql -U agentwatch_prod agentwatch_prod
```

### ChromaDB

```bash
# Backup persist directory
rsync -avz /data/chroma/ /backups/chroma/$(date +%Y%m%d)/
```

### Redis

```bash
# Save RDB snapshot
redis-cli SAVE
cp /var/lib/redis/dump.rdb /backups/redis/dump_$(date +%Y%m%d).rdb
```

### Application Config

```bash
# Backup env files and config
tar czf /backups/config/agentwatch_config_$(date +%Y%m%d).tar.gz /etc/agentwatch/
```

### Backup Schedule

| Data | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| PostgreSQL | Daily | 30 days | `pg_dump` → S3/GS |
| ChromaDB | Daily | 14 days | Filesystem rsync |
| Redis | Hourly | 7 days | RDB snapshot |
| Config | Per deploy | 90 days | Git (infra repo) |
| Audit logs | Real-time | 1 year | Elasticsearch / SIEM |

---

## 10. Troubleshooting

### Common Issues

#### API Won't Start

```
Error: "Required secret 'secret_key' is not configured"
```
**Fix:** Ensure `SECRET_KEY` environment variable is set. Generate with `openssl rand -hex 32`.

```
Error: "Cannot connect to database"
```
**Fix:** Verify `DATABASE_URL` is correct. Check PostgreSQL is running and accepting connections.

#### Database Migration Fails

```bash
# Check current revision
alembic current

# View migration history
alembic history

# Manual upgrade to specific revision
alembic upgrade <revision_hash>

# Rollback
alembic downgrade -1
```

#### High Memory Usage

- **PostgreSQL:** Check `shared_buffers` config (should be 25% of RAM)
- **API workers:** Reduce `--workers` count or add memory limits
- **ChromaDB:** Reduce collection count or purge old collections

#### Redis Connection Failures

```bash
# Test connectivity
redis-cli -h redis -p 6379 ping

# Check max connection limit
redis-cli CONFIG GET maxclients

# Monitor active connections
redis-cli CLIENT LIST | wc -l
```

#### LLM Provider Errors

```
Error: "OPENAI_API_KEY is required when LLM_PROVIDER='openai'"
```
**Fix:** Set `OPENAI_API_KEY` in environment. Verify key has sufficient quota.

```
Error: "Rate limit exceeded for OpenAI API"
```
**Fix:** Reduce `LLM_MAX_TOKENS` or implement request queuing.

### Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Basic health | `{"status":"ok","version":"0.1.0"}` |
| `GET /metrics` | Prometheus metrics | Prometheus text format |
| `GET /docs` | Swagger UI | HTML documentation |

### Getting Help

- **GitHub Issues:** https://github.com/agentwatch/agentwatch/issues
- **Internal Runbook:** `/docs/runbook/` (operational runbooks)
- **On-call:** PagerDuty escalation (production incidents)

---

## Appendix: Production .env Template

```bash
# === Core ===
ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALLOWED_ORIGINS=["https://app.agentwatch.ai"]

# === Database ===
DATABASE_URL=postgresql+asyncpg://agentwatch_prod:<password>@<host>:5432/agentwatch_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# === Auth ===
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_MIN_LENGTH=12
PASSWORD_MAX_LENGTH=128
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
REQUIRE_EMAIL_VERIFICATION=true

# === Redis ===
REDIS_URL=redis://<host>:6379/0
REDIS_POOL_SIZE=20
DEFAULT_CACHE_TTL=300

# === LLM ===
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# === Vector Store ===
CHROMA_HOST=chromadb
CHROMA_PORT=8000
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# === Observability ===
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
SENTRY_TRACES_SAMPLE_RATE=0.1

# === Secrets ===
SECRETS_BACKEND=env
```
