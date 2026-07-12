# AARA — Interview Cheatsheet

## Quick Facts

| Topic | Answer |
|-------|--------|
| What is AARA? | Multi-agent AI research platform — 5 LangGraph agents conduct literature reviews, analyze gaps, and generate reports |
| Tech stack | FastAPI + Next.js 16 + LangGraph + PostgreSQL + ChromaDB + Redis |
| Test suite | 392/395 passing (99.24%) |
| Security | 4-layer defense-in-depth (JWT + RBAC + rate limiting + ownership) |
| Benchmark | 13 real Gemini queries, 100% completion |
| Docker | Multi-stage build, 200MB image, non-root user |
| CI/CD | 4 GitHub Actions workflows |
| Monitoring | 12 Prometheus metrics, Grafana dashboards, Sentry |
| License | MIT |

## Architecture (45-second explanation)

"5 LangGraph agents working in sequence: Planner decomposes the query into a research plan with subtopics and methodology. Retriever searches ChromaDB and returns ranked papers. Summarizer synthesizes findings into themes. Gap Analyzer identifies research weaknesses with severity ratings. Report Generator produces the final publication-quality report with citations."

## Key Differentiators

1. **Multi-agent vs single LLM**: Specialized agents produce more structured, verifiable outputs
2. **Defense-in-depth**: 4 independent auth layers — most AI projects have 1 or 0
3. **Graceful degradation**: No single dependency (LLM, Redis, DB) can crash the system
4. **Testing discipline**: 392 tests — rare for portfolio AI projects
5. **Real LLM integration**: Successfully tested against Google Gemini API

## STAR Stories

### Rate Limiting Race Condition
**S**: TOCTOU bug in rate limiter under 100+ concurrent requests
**T**: Fix without distributed locks
**A**: Atomic Redis Lua script (INCR + EXPIRE in single EVAL call)
**R**: Zero violations at 500 users, <2ms per check

### Multi-Agent Pipeline
**S**: Single LLM calls produce generic, ungrounded outputs
**T**: Design agent system with transparent reasoning
**A**: 5 typed agents with Pydantic state, clear I/O contracts
**R**: 100% benchmark completion, avg 16K chars per report

### Security Audit
**S**: Open-source project needs enterprise-grade security
**T**: Implement and validate comprehensive auth
**A**: 4 layers + 10-phase audit finding 2 missing auth fixes
**R**: Zero critical findings

## Technical Deep Dives

**LangGraph**: "Finer-grained state control than LangChain. Each agent is a typed node in a state graph with Pydantic schemas. This gives us conditional branching and full traceability."

**Rate Limiting**: "Python check-then-increment has TOCTOU race. Atomic Lua in Redis EVAL fixes it — INCR, set expiry on first hit, return count. One call, no race."

**JWT Design**: "Access tokens: 15-min expiry, HMAC-SHA256. Refresh tokens: 7-day, single-use (rotated on each refresh). Token version for global invalidation."

**Graceful Degradation**: "Three fallback modes: LLM down → template reports. Redis down → disabled rate limiting. ChromaDB down → keyword search."

## Common Questions

**Q**: Why LangGraph over LangChain?
**A**: "LangGraph gives me typed state schemas (Pydantic) per node, conditional branching between agents, and full execution traceability. LangChain chains are simpler but less controllable."

**Q**: How do you handle LLM failures?
**A**: "Strategy pattern with 3 providers (Gemini, OpenAI, Mock). If all fail, template-based generation kicks in — the report structure comes from templates while content uses retrieved data."

**Q**: How many tests and what do they cover?
**A**: "392/395 passing. Unit tests for individual components (mocked), integration tests for DB/Redis/Chroma interactions, and E2E for full auth flows and agent workflows. 3 skipped tests are PostgreSQL-specific."

**Q**: What would you improve?
**A**: "PDF export (currently basic), WebSocket streaming for real-time agent output, and multi-agent collaboration where agents critique each other's work. Also want to add E2E Playwright tests."

## Metrics to Reference

- 46 API endpoints across 13 routers
- 5 agents with typed state schemas
- 4 security layers
- 10 security audit phases
- 13/13 real Gemini benchmarks
- 392/395 tests in 40s
- 12 Prometheus metrics
- 200MB Docker image
- 5 k6 load scenarios (up to 500 users)
