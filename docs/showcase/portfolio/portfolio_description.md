# AARA — Portfolio Description

## One-Paragraph Pitch

**AARA (Agentic AI Research Assistant)** is a production-grade, multi-agent AI platform that autonomously conducts literature reviews, analyzes research gaps, and generates structured reports — with transparent, evidence-backed reasoning at every step. Built with FastAPI, Next.js 16, and LangGraph, AARA orchestrates 5 specialized agents (Planner, Retriever, Summarizer, Gap Analyzer, Report Generator) through a coordinated research pipeline. The platform features defense-in-depth security (4-layer JWT/RBAC), graceful degradation for LLM/Redis/ChromaDB failures, comprehensive monitoring (Prometheus/Grafana/Sentry), and 392/395 passing tests. It's designed as an open-source portfolio project demonstrating full-stack AI engineering, security best practices, and production DevOps.

## Key Differentiators

| Aspect | AARA | Typical AI Demo |
|--------|------|----------------|
| Architecture | Multi-agent (5 specialized) | Single LLM call |
| Security | 4-layer defense-in-depth | Basic auth or none |
| Resilience | Graceful degradation | Hard fail on dependency loss |
| Testing | 392 automated tests | Manual or minimal |
| Observability | Prometheus + Grafana + Sentry | None |
| Documentation | Full architecture + deployment + portfolio | Minimal README |

## Target Audience

- **Recruiters**: Demonstrates full-stack AI engineering, security mindset, testing discipline
- **Research groups**: Shows practical multi-agent AI for literature review automation
- **Hackathon judges**: Complete production-grade system with CI/CD, monitoring, testing
- **Faculty reviewers**: Demonstrates understanding of RAG, LLMs, vector databases, security

## Technical Scope

- **46 API endpoints** across 13 routers
- **5 LangGraph agents** with typed Pydantic state schemas
- **3 LLM providers**: OpenAI GPT-4o, Google Gemini 2.0 Flash, Mock
- **2 vector stores**: ChromaDB for embeddings, PostgreSQL for relational data
- **4-layer security**: Edge proxy, client interceptor, backend middleware, service layer
- **4 CI/CD workflows**: PR checks, main branch, security scan, load test
- **12 Prometheus metrics** with pre-built Grafana dashboards
- **5 k6 load test scenarios**: up to 500 concurrent users
