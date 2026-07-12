# AARA — 2-Minute Demo Script

## For Recruiters / Quick Overview

**Setup**: Have the landing page or dashboard open on screen.

---

**(0:00-0:20) — The Problem**

"Research is slow. A researcher might spend 30-50% of their time just reviewing literature, finding gaps, and formatting reports. Existing tools like ChatGPT give generic answers with no citations. AARA solves this."

---

**(0:20-0:50) — What It Does**

"AARA is an AI-powered research assistant with 5 specialized agents working together. You type a research question — like 'What are advances in few-shot learning?' — and these agents go to work:

1. The **Planner** breaks your question into research subtopics
2. The **Retriever** searches for relevant papers
3. The **Summarizer** synthesizes findings
4. The **Gap Analyzer** identifies research gaps
5. The **Report Generator** produces a publication-quality report

Every step is visible, every claim is cited."

---

**(0:50-1:20) — Live Demo (if possible)**

*[Navigate to the research page]*

"Let me show you. I'll type a research query..."

*[Type a query, click submit]*

"You can see the agents working in real-time — here's the plan being generated, papers being retrieved..."

*[Point to agent monitoring panel]*

"And here's the final report with citations, contradictions detected, and an executive summary."

---

**(1:20-1:50) — Technical Highlights**

"Under the hood:
- **FastAPI backend**: 46 API endpoints, async SQLAlchemy, Pydantic validation
- **Next.js 16 frontend**: Server Components, Zustand state, Tailwind CSS
- **Security**: 4 layers of authentication — JWT, RBAC, rate limiting, prompt injection protection
- **Testing**: 392 automated tests, 99.2% pass rate
- **Infrastructure**: Docker multi-stage (200MB), GitHub Actions CI/CD, Prometheus monitoring"

---

**(1:50-2:00) — Close**

"It's fully open-source. The repo has architecture docs, deployment guide, and everything you need to run it yourself. Questions?"

---

## Key Talking Points (if interrupted)

- "5 specialized agents, not one generic LLM"
- "4-layer security — not just basic auth"
- "Graceful degradation — survives LLM/Redis/DB failures"
- "392 tests — built for production, not just a demo"
- "Real Gemini API integration — 13 benchmarks completed"
