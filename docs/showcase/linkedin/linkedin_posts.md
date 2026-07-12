# LinkedIn Posts for AARA

---

## Post 1: Launch Announcement

**Headline**: I built an open-source multi-agent AI research assistant. Here's why.

**Body**:

After months of building, I'm excited to open-source AARA — an Agentic AI Research Assistant that autonomously conducts literature reviews, analyzes research gaps, and generates structured reports.

Instead of a single LLM call, AARA runs 5 specialized LangGraph agents:
1. Planner → decomposes queries into research plans
2. Retriever → searches vector databases for relevant papers
3. Summarizer → synthesizes findings into themes
4. Gap Analyzer → identifies research weaknesses
5. Report Generator → produces publication-quality output

Key numbers:
• 392/395 tests passing (99.2%)
• 13 real Gemini API benchmarks completed
• 10 security audit phases with zero critical findings
• 4-layer defense-in-depth authentication
• Docker multi-stage build (200MB)
• Prometheus + Grafana monitoring

Built with: FastAPI, Next.js 16, LangGraph, PostgreSQL, ChromaDB, Redis, Docker, GitHub Actions

The entire project is open-source. Check it out, contribute, or just stare at the architecture diagrams.

#opensource #ai #machinelearning #langgraph #fastapi #nextjs #aagents

---

## Post 2: Project Showcase

**Headline**: Under the hood of my multi-agent AI project: Architecture, security, and 392 tests

**Body**:

I've been asked a lot: "How is AARA different from just calling ChatGPT?"

Great question. Here's the difference:

1. **Multi-agent architecture**: A single LLM call produces generic text. AARA's 5 agents each have specialized roles — planning, retrieval, summarization, gap analysis, report generation. Each agent has focused context and clear responsibilities.

2. **Security matters**: AARA has 4 independent authentication layers. Edge proxy validation → client token refresh → backend middleware (rate limiting, headers) → service-level RBAC and ownership checks. I spent 10 audit phases making sure every endpoint is protected.

3. **Resilience**: What happens when the LLM API is down? AARA generates template-based reports. Redis down? Rate limiting degrades gracefully. ChromaDB offline? Keyword search fallback. No single dependency can crash the system.

4. **Testing discipline**: 392 automated tests. Auth flows, security validation, agent workflows, document ingestion, export formats. Each CI run takes 2 minutes.

5. **Observability**: 12 Prometheus metrics, pre-built Grafana dashboards, Sentry error tracking, structured JSON logging with correlation IDs. You can see exactly what every agent is doing.

The repo is at [link]. Built with FastAPI, Next.js 16, LangGraph, PostgreSQL, ChromaDB, and Redis.

What questions do you have about building multi-agent AI systems?

#aiengineering #softwareengineering #systemdesign #portfolio

---

## Post 3: Technical Deep Dive

**Headline**: Rate limiting with atomic Redis Lua scripts: How I fixed a TOCTOU race condition

**Body**:

Here's a bug that's easy to miss in concurrent systems — and how I fixed it in AARA.

**The problem**: Our rate limiter used a check-then-increment pattern:
```
if redis.get(key) < limit:
    redis.incr(key)
    allow_request()
```

Under 100+ concurrent requests, multiple threads could pass the check before any counter was incremented. TOCTOU (time-of-check-time-of-use) race condition — the rate limit was effectively bypassed.

**The fix**: Replace the Python pattern with an atomic Lua script that runs inside Redis:
```lua
local current = redis.call('INCR', key)
if current == 1 then redis.call('EXPIRE', key, window) end
if current > limit then return 0 else return 1 end
```

One Redis EVAL call. No race condition. No distributed locks needed.

**Verification**: Added concurrent test scenarios with 500 virtual users. Zero violations.

This is the kind of bug that production systems catch and demos don't. AARA has 392 tests specifically because I wanted to catch these before they reach production.

The repo is open-source if you want to see the full implementation.

#systemdesign #redis #concurrency #python #softwareengineering
