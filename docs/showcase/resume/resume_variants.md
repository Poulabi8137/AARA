# AARA — Resume Descriptions

## One-Line Description

Built a production-grade multi-agent AI research platform (FastAPI + Next.js 16 + LangGraph) with 392 tests and 4-layer security.

## Two-Line Description

Built an open-source multi-agent AI platform that autonomously conducts literature reviews and generates structured reports via 5 coordinated LangGraph agents. Features defense-in-depth security across 4 layers, 392/395 passing tests, real Gemini API integration, and Docker/CI/CD deployment.

## ATS-Friendly Version

```
Agentic AI Research Assistant (AARA)
- Multi-agent AI research platform using FastAPI, Next.js 16, LangGraph, PostgreSQL, ChromaDB, Redis
- Implemented 5 specialized LangGraph agents: Planner, Retriever, Summarizer, Gap Analyzer, Report Generator
- Built defense-in-depth security: JWT authentication, RBAC, rate limiting (Redis Lua), prompt injection prevention
- Developed 46 REST API endpoints across 13 routers with async SQLAlchemy and Pydantic validation
- Achieved 392/395 tests passing (99.2%) across unit, integration, and E2E test suites
- Integrated Google Gemini and OpenAI LLM providers with graceful degradation fallback
- Configured Docker multi-stage builds (200MB), 4 GitHub Actions CI/CD workflows, Prometheus/Grafana monitoring
- Conducted 10-phase security audit with zero critical findings
- Executed 13 benchmark queries against real Gemini API with 100% completion rate
- Generated 10 IEEE-style papers averaging 16,278 characters with citation management
```

## Google-Style Version

**AARA: Agentic AI Research Assistant**  
*Languages: Python, TypeScript, SQL | Technologies: FastAPI, Next.js 16, LangGraph, PostgreSQL, ChromaDB, Redis, Docker, GitHub Actions, Prometheus, Gemini*

Built a multi-agent AI system that autonomously conducts academic research. The platform uses 5 LangGraph agents working in sequence: a Planner decomposes queries into research plans, a Retriever searches vector databases, a Summarizer synthesizes findings, a Gap Analyzer identifies weaknesses, and a Report Generator produces publication-quality output. Security is handled by 4 independent authentication layers including edge JWT validation, client-side token refresh with 401 queueing, atomic Redis rate limiting, and service-level RBAC/ownership enforcement. The system handles real Gemini API integration with graceful fallback when quota is exhausted — 13 benchmark queries completed at 100%. 392/395 tests pass across unit, integration, and E2E suites. Docker multi-stage builds produce a 200MB image. Prometheus + Grafana provide real-time monitoring with 12 custom metrics.

**Key Results:** 392/395 tests | 13 real Gemini benchmarks | 10 security audits | 46 APIs | 200MB Docker image

## Startup Version

**AARA** — Turn research questions into publication-ready reports. 5 AI agents working together. Built for speed.

I built AARA because existing research tools are either manual (Zotero, Mendeley) or black-box (ChatGPT). AARA is neither — it's a transparent, multi-agent system where every reasoning step is visible, every claim is cited, and every failure is handled gracefully.

What makes it different:
- **5 specialized agents** instead of one generic LLM call — better structure, better citations
- **4-layer security** — because enterprise users won't touch a tool without auth
- **Graceful degradation** — LLM quota exhausted? Still generates reports from templates
- **392 tests** — because shipping AI without tests is reckless

Tech: FastAPI + Next.js 16 + LangGraph + PostgreSQL + ChromaDB + Redis + Docker + Gemini

392/395 tests passing. 13/13 benchmarks completed. Ready to demo.
