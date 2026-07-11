# Document 30 — CI/CD Pipeline

## Pipeline Overview

```mermaid
graph LR
    DEV[Developer Push] --> CI[GitHub Actions CI]
    CI --> LINT[Lint & Type Check]
    CI --> UNIT[Unit Tests]
    CI --> INTEGRATION[Integration Tests]
    
    LINT --> BUILD[Build]
    UNIT --> BUILD
    INTEGRATION --> BUILD
    
    BUILD --> PUBLISH[Docker Build & Push]
    PUBLISH --> STAGING[Deploy to Staging]
    STAGING --> E2E[E2E Tests]
    
    E2E -->|Manual Approval| PRODUCTION[Deploy to Production]
```

## GitHub Actions Workflow

### CI Pipeline (`.github/workflows/ci.yml`)
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install dependencies
        run: |
          cd backend
          pip install ruff mypy
          pip install -r requirements.txt
      - name: Lint with ruff
        run: cd backend && ruff check app/
      - name: Type check with mypy
        run: cd backend && mypy app/ --strict

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Lint
        run: cd frontend && npm run lint
      - name: Type check
        run: cd frontend && npx tsc --noEmit

  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: aara_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y tesseract-ocr tesseract-ocr-eng pandoc
      - name: Install Python dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run unit + integration tests
        run: |
          cd backend
          pytest tests/unit tests/integration -x --timeout=60 -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/aara_test
          QDRANT_URL: http://localhost:6333
          ENV: test

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: cd frontend && npm test -- --coverage
      - name: Build
        run: cd frontend && npm run build
```

### Deploy Pipeline (`.github/workflows/deploy.yml`)
```yaml
name: Deploy

on:
  workflow_run:
    workflows: ["CI"]
    branches: [main]
    types:
      - completed

jobs:
  deploy-staging:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy backend to Railway
        uses: railway/action@v3
        with:
          projectId: ${{ secrets.RAILWAY_PROJECT_ID }}
          serviceId: ${{ secrets.RAILWAY_BACKEND_SERVICE_ID }}
          environment: staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy frontend to Railway
        uses: railway/action@v3
        with:
          projectId: ${{ secrets.RAILWAY_PROJECT_ID }}
          serviceId: ${{ secrets.RAILWAY_FRONTEND_SERVICE_ID }}
          environment: staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  e2e-tests:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt pytest pytest-asyncio httpx
      - name: Run E2E tests against staging
        run: |
          cd backend
          pytest tests/e2e -x --timeout=300 -v
        env:
          STAGING_URL: ${{ secrets.STAGING_URL }}
          E2E_API_KEY: ${{ secrets.E2E_API_KEY }}

  deploy-production:
    needs: e2e-tests
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://aara.app
    steps:
      - uses: actions/checkout@v4

      - name: Deploy backend to production
        uses: railway/action@v3
        with:
          projectId: ${{ secrets.RAILWAY_PROJECT_ID }}
          serviceId: ${{ secrets.RAILWAY_BACKEND_SERVICE_ID }}
          environment: production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy frontend to production
        uses: railway/action@v3
        with:
          projectId: ${{ secrets.RAILWAY_PROJECT_ID }}
          serviceId: ${{ secrets.RAILWAY_FRONTEND_SERVICE_ID }}
          environment: production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Branch Strategy

```mermaid
gitGraph
    commit
    branch develop
    checkout develop
    commit id: "Phase 1 scaffold"
    branch feature/auth
    checkout feature/auth
    commit id: "Supabase auth"
    commit id: "Login/Register UI"
    checkout develop
    merge feature/auth
    branch feature/workspace
    commit id: "Workspace CRUD"
    checkout develop
    merge feature/workspace
    checkout main
    merge develop tag: "v1.0.0-alpha"
```

| Branch | Purpose | Deploys To |
|---|---|---|
| `main` | Production-ready code | Production Railway |
| `develop` | Integration branch | Staging Railway |
| `feature/*` | Individual features | None (CI only) |
| `fix/*` | Bug fixes | None (CI only) |

## Secrets Management

```yaml
# GitHub Repository Secrets
# Settings → Secrets and variables → Actions

RAILWAY_TOKEN:              # Railway API token
RAILWAY_PROJECT_ID:         # AARA Railway project ID
RAILWAY_BACKEND_SERVICE_ID: # Backend service ID
RAILWAY_FRONTEND_SERVICE_ID:# Frontend service ID
E2E_API_KEY:               # Test API key for staging
STAGING_URL:               # Staging deployment URL

SUPABASE_URL:              # Supabase project URL
SUPABASE_SERVICE_KEY:      # Supabase service role key

OPENAI_API_KEY:            # OpenAI API key (for E2E tests)
ENCRYPTION_KEY:            # Fernet key for API key encryption
```

## Versioning Strategy

```
Semantic Versioning: vMAJOR.MINOR.PATCH

v1.0.0-alpha  — Phase 1 complete (Foundation)
v1.0.0-beta   — Phase 2 complete (Research Infrastructure)
v1.0.0-rc1    — Phase 3 complete (Core Agentic AI)
v1.0.0        — Phase 4 complete (Full MVP)
v1.1.0        — Phase 5 complete (Production Readiness)
```

## Rollback Strategy

```yaml
# Railway dashboard: manual rollback to previous version

# Command-line rollback:
# railway service rollback --service <service-id> --deployment <deployment-id>

# Criteria for rollback:
# - Error rate > 5% after deployment
# - E2E tests fail in production
# - Critical security vulnerability discovered
# - Database migration error
```
