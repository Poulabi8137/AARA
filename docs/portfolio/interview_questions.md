# AARA Interview Questions & Answers

## Technical Deep Dives

### Q1: Why multi-agent instead of a single LLM call?
**A**: A single LLM call produces generic, unfocused answers. Our multi-agent pipeline decomposes research into 5 specialized stages: planning, retrieval, summarization, gap analysis, and report generation. Each agent has a focused context window and clear responsibilities. The Planner structures the research approach; the Retriever gathers evidence; the Summarizer synthesizes; the Gap Analyzer identifies weaknesses; the Report Generator composes. This produces more structured, evidence-grounded reports than any single-shot approach.

### Q2: How do you handle LLM failures?
**A**: We use a strategy pattern with pluggable providers (OpenAI, Gemini, Mock). If the primary LLM fails, we fall back through providers. If all fail, template-based generation produces reports from retrieved content — ensuring the system never hard-fails on LLM unavailability. We also implement graceful degradation for Redis and ChromaDB: the system continues with reduced functionality if either is down.

### Q3: What's your security architecture?
**A**: Defense-in-depth with 4 layers: (1) Edge proxy.ts validates JWT from cookies before any request reaches the backend; (2) Client-side interceptor silently refreshes tokens and queues concurrent 401s; (3) FastAPI middleware handles rate limiting (atomic Lua scripts preventing TOCTOU races), security headers, and structured logging; (4) Service layer validates tokens, enforces RBAC, and checks resource ownership on every protected endpoint.

### Q4: How did you achieve 392 tests?
**A**: Comprehensive testing across unit (individual components mocked), integration (database, Redis, ChromaDB), and E2E (full workflows). Tests cover auth flows (register, login, refresh, logout), security validation (RBAC, ownership, rate limiting), agent workflows, document ingestion, and export formats. We use pytest with async fixtures, PostgreSQL test containers, and fakeredis for deterministic test runs.

## Architecture & Design

### Q5: Why LangGraph over LangChain?
**A**: LangGraph provides finer-grained control over agent state and workflow transitions. Each agent is a node in a state graph with typed state schemas (Pydantic). This lets us inject context between steps, implement conditional branching, and maintain full traceability of agent reasoning — critical for research transparency where each output must reference its sources.

### Q6: How does the RAG pipeline work?
**A**: Documents are uploaded, chunked, and embedded into ChromaDB. On query, the Retriever performs semantic search with re-ranking and deduplication. Results include relevance scores and source metadata. The Summarizer then synthesizes retrieved content into thematic findings per subtopic — not just dumping chunks but actually reasoning across them.

### Q7: What metrics do you track?
**A**: 12 custom Prometheus metrics: request rate/latency (p50/p95/p99), error rate by type/service, auth failures by reason, rate limit violations, workflow/agent/LLM/DB duration, active workflows, and queue depth. Pre-built Grafana dashboards visualize these for real-time monitoring.

## Behavioral (STAR)

### Q8: Tell me about a challenging technical problem you solved.
**Situation**: Rate limiting had a TOCTOU (time-of-check-time-of-use) race condition — concurrent requests could exceed limits.
**Task**: Fix it without adding distributed locks (too slow) or changing the Redis architecture.
**Action**: Implemented atomic Lua scripts that check and increment in a single Redis operation. Verified with concurrent test scenarios.
**Result**: Race condition eliminated. 500-user spike test passed with 0 rate-limit violations. Redis calls still complete in <2ms.

### Q9: Tell me about a design decision you made.
**Situation**: Next.js 16 deprecated middleware.ts — our auth proxy was at risk.
**Task**: Migrate to a supported pattern without losing JWT validation at the edge.
**Action**: Renamed middleware.ts to proxy.ts, switched export to a `proxy()` function, and updated the Next.js config. Kept the same JWT verification logic (HMAC-SHA256, cookie-based).
**Result**: Seamless migration. All auth tests pass. Server renders HTTP 200 on all routes.
