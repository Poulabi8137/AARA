# Supplemental — Technical Requirements Document

## Technology Stack

### Frontend
- Next.js 16 (App Router)
- React 19, TypeScript 5
- TailwindCSS, shadcn/ui, Framer Motion
- TanStack Query, Zustand, React Hook Form, Zod

### Backend
- Python 3.12, FastAPI
- SQLAlchemy 2, Alembic, Pydantic 2

### Infrastructure
- Supabase (PostgreSQL, Auth, Storage)
- Qdrant (Vector DB)
- Docker (Containerization)
- Railway (Deployment)

### AI Providers (Abstracted)
- OpenAI (GPT-4o-mini, GPT-4o, text-embedding-3-small)
- Google Gemini (Gemini 1.5 Pro/Flash)
- Groq (Llama 3, Mixtral)
- OpenRouter (Meta-provider)
- Ollama (Local open models)

## Performance Requirements

| Operation | Max Latency | Strategy |
|---|---|---|
| Semantic search | 500ms | Qdrant HNSW index, caching |
| PDF upload & process (10pp) | 30s | Background job, progress events |
| Agent workflow (lit review, 50 refs) | 120s | Parallel agent execution, streaming |
| Auth (login/register) | 2s | Supabase managed |
| API response (CRUD) | 200ms | Pagination, eager loading |
| Export (PDF, 10pp) | 15s | Background job |

## Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| VALIDATION_ERROR | 400 | Request validation failed |
| UNAUTHORIZED | 401 | Missing/invalid auth token |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource does not exist |
| RATE_LIMITED | 429 | Too many requests |
| PROVIDER_ERROR | 502 | Upstream AI provider failed |
| WORKFLOW_FAILED | 500 | Agent workflow execution error |
| COST_LIMIT_EXCEEDED | 402 | API budget exhausted |
