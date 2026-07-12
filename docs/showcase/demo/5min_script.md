# AARA — 5-Minute Demo Script

## For Technical Interviews / Career Fairs

**Setup**: Have the application running on localhost:3000, with backend on :8011.

---

### Part 1: Project Overview (0:00-1:30)

"AARA is an Agentic AI Research Assistant — an open-source platform that autonomously conducts literature reviews, analyzes research gaps, and generates structured reports.

The core idea: instead of a single LLM call that produces generic text, I built 5 specialized agents that each handle one part of the research process. Each agent has a focused context window, clear input/output contracts, and produces transparent reasoning traces.

The stack: FastAPI backend with async SQLAlchemy, Next.js 16 frontend, LangGraph for agent orchestration, PostgreSQL for relational data, ChromaDB for vector search, and Redis for caching and rate limiting."

---

### Part 2: Agent Architecture (1:30-3:00)

"Let me walk through the agents:

**Planner Agent**: Takes the user query, uses few-shot prompting to generate a structured research plan with subtopics, search queries, and methodology. I use Pydantic models to enforce the output schema.

**Retriever Agent**: Performs semantic search across ChromaDB, re-ranks results by relevance, and deduplicates similar papers. Returns ranked papers with abstracts and relevance scores.

**Summarizer Agent**: Groups papers by subtopic and synthesizes findings. Extracts key claims, methodology notes, and supporting citations.

**Gap Analyzer Agent**: Identifies 5-10 research gaps with severity ratings — high (core question unanswered), medium (partial answers), low (incremental). Each gap includes confidence scores and remediation suggestions.

**Report Generator Agent**: Produces the final report in 3 formats (academic, executive, comprehensive) with 4 citation styles (APA, MLA, Chicago, BibTeX). Includes contradiction detection and hallucination scoring.

The agents communicate through a typed state graph. Each agent reads from shared state, writes its output, and passes control to the next."

---

### Part 3: Security Architecture (3:00-4:00)

"Security was a major focus. I implemented defense-in-depth with 4 independent layers:

**Layer 1 — Edge Proxy**: The Next.js proxy.ts file reads JWT from the auth_token cookie, verifies the HMAC-SHA256 signature, and validates exp/sub claims before any request reaches the backend. Invalid requests get a 401 redirect.

**Layer 2 — Client Interceptor**: The browser-side API client attaches Bearer tokens to every request. When it detects a 401, it queues concurrent requests (so N simultaneous 401s trigger only 1 refresh call) and silently rotates tokens via /auth/refresh.

**Layer 3 — Backend Middleware**: Rate limiting with atomic Redis Lua scripts — this eliminates the TOCTOU race condition where concurrent requests could bypass the limit. Also adds security headers (HSTS, CSP, X-Frame-Options) and structured logging with correlation IDs.

**Layer 4 — Service Layer**: Every protected endpoint verifies JWT signature, checks token type (access vs refresh), validates token version (supports global invalidation), enforces RBAC (Admin/Researcher/Viewer), and verifies resource ownership.

I validated all 46 endpoints across a 10-phase security audit. Zero critical findings."

---

### Part 4: Testing & DevOps (4:00-4:30)

"Testing: 392 tests across unit, integration, and E2E. Auth flows, security validation, agent workflows, document ingestion, and export formats. 99.2% pass rate, runs in 2 minutes.

Infrastructure: Docker multi-stage builds produce a 200MB image with a non-root user and health checks. 4 GitHub Actions workflows handle PR checks, main branch builds, weekly security scans, and manual load tests.

Monitoring: 12 custom Prometheus metrics with p50/p95/p99 latency histograms, pre-built Grafana dashboards, and Sentry error tracking."

---

### Part 5: Results & Close (4:30-5:00)

"Results:
- 13 benchmark queries against the real Gemini API — 100% completion
- 10 IEEE-style papers generated with 15 sections each
- Average 16,278 characters per report
- <0.5s LLM latency on gemini-2.5-flash

When the Gemini free quota was exhausted (20 requests/day), the system gracefully fell back to template-based generation without any user-facing errors.

The repo is at [github link]. It includes architecture docs, deployment guide, benchmark reports, portfolio assets, and 13 verified screenshots. Happy to dive deeper into any aspect."
