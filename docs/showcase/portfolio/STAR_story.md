# AARA — STAR Stories

## Story 1: Fixing a TOCTOU Race Condition in the Rate Limiter

**Situation**: During load testing of AARA, I discovered a TOCTOU (time-of-check-time-of-use) race condition in the rate limiter. When 100+ concurrent requests arrived simultaneously, multiple threads could pass the `if redis.get(key) < limit` check before any counter was incremented — effectively bypassing the rate limit entirely.

**Task**: Eliminate the race condition without introducing distributed locks (which add latency and complexity) or changing the Redis infrastructure.

**Action**: I replaced the Python check-then-increment pattern with an atomic Lua script that performs both operations in a single Redis `EVAL` call:
```lua
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current > limit then return 0 else return 1 end
```
I also added 5 new concurrent test scenarios with 500 virtual users to verify the fix under load.

**Result**: The race condition was eliminated. Load tests with 500 concurrent users showed zero rate-limit violations. Each Redis call still completes in <2ms. The fix was verified by 5 new test cases covering concurrent edge cases.

**Skills demonstrated**: System design, concurrency, Redis, security, testing

---

## Story 2: Building a Multi-Agent Research Pipeline

**Situation**: I needed to build an AI system that could produce high-quality, verifiable research reports. A single LLM call produced generic, ungrounded outputs with no transparency into the reasoning process.

**Task**: Design a system that decomposes the research process into specialized stages, with each stage producing verifiable outputs that feed into the next — and full traceability of every reasoning step.

**Action**: I implemented 5 LangGraph agents with typed Pydantic state schemas: Planner (query decomposition into research plan with subtopics and methodology), Retriever (ChromaDB semantic search returning ranked papers with relevance scores), Summarizer (thematic synthesis across subtopics), Gap Analyzer (structured gap identification with severity classification), and Report Generator (publication-quality output with citations, contradictions, and executive summary). Each agent has focused context windows and clear I/O contracts.

**Result**: The pipeline produces structured, evidence-grounded reports. Benchmark showed 100% completion rate across 13 real Gemini queries. Average report length: 16,278 characters. Average quality score: 60/100 across 15 standardized sections.

**Skills demonstrated**: AI/ML, LangGraph, LLM integration, RAG, system design

---

## Story 3: Production-Grade Security in 10 Audit Phases

**Situation**: As an open-source portfolio project targeting recruiters and academic reviewers, AARA needed enterprise-grade security — not just basic authentication. Users needed to trust that their research data was protected.

**Task**: Implement and validate a comprehensive security architecture covering authentication, authorization, data protection, and AI safety — then prove it with a thorough audit.

**Action**: I implemented 4 defense-in-depth layers: (1) Edge proxy.ts validates JWT from cookies before any request reaches the backend; (2) Client-side interceptor silently refreshes tokens and queues concurrent 401s to avoid multiple refresh calls; (3) FastAPI middleware handles atomic Redis rate limiting (Lua scripting), security headers (HSTS, CSP, XFO), and structured logging; (4) Service layer validates tokens, enforces RBAC (Admin, Researcher, Viewer), and checks resource ownership on every protected endpoint. I then conducted a 10-phase security audit covering authorization, database integrity, secrets management, upload validation, rate limiting, and AI prompt injection prevention.

**Result**: Zero critical findings across all 10 audit phases. All 46 endpoints audited with proper authentication. 2 missing auth protections were found and fixed during the audit. Token rotation, global invalidation, and prompt injection mitigation all validated.

**Skills demonstrated**: Security engineering, JWT, RBAC, system design, auditing

---

## Story 4: Building a 392-Test Suite for an AI Platform

**Situation**: With 46 API endpoints, 5 agents, 3 LLM providers, multiple database backends (SQLite + PostgreSQL), and complex auth flows, manual testing was impossible. Every code change risked regressions across the system.

**Task**: Build a comprehensive automated test suite that catches regressions, is fast enough to run in CI (<3 minutes), and doesn't become flaky or fragile.

**Action**: I structured tests into 13 files across three layers: unit tests (individual components with mocks), integration tests (database, Redis, ChromaDB interactions), and E2E tests (full auth flows, agent workflows, export formats). Used pytest with async fixtures, SQLAlchemy test sessions with rollback isolation, fakeredis for deterministic rate-limit tests, and mock LLM providers for deterministic agent tests. Added concurrent test scenarios for race condition verification.

**Result**: 392/395 tests pass in ~40s (99.24% pass rate). The 3 skipped tests are for PostgreSQL-specific features (JSONB, full-text search) not available in CI's SQLite environment. Coverage spans auth flows, RBAC enforcement, agent workflows, document ingestion, and all export formats. No regressions since test suite was established.

**Skills demonstrated**: Testing, pytest, CI/CD, quality engineering
