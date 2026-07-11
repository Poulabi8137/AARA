# Supplemental — Product Requirements Document

## Product Vision

AARA is an **Agentic AI Research Intelligence Platform** that deploys multiple autonomous AI agents to collaborate on academic research workflows. It is not a chatbot or a paper generator — it is an **AI research team** that assists researchers from literature discovery through structured research drafting, while keeping the researcher in full control.

## Target Users

| Persona | Background | Primary Need |
|---|---|---|
| Graduate Student | MS/PhD student writing thesis | Accelerate literature review, identify gaps |
| PhD Researcher | Publishing regularly | Automated literature monitoring, trend detection |
| Industry R&D Engineer | ML engineer at startup | Rapid literature survey, experiment planning |
| Undergraduate | Final-year capstone | Guided research workflow, structured output |

## User Stories (Phase 1-5)

### Phase 1 — Foundation
- As a user, I can create an account using email or Google OAuth.
- As a user, I can create a research topic workspace.
- As a user, I can see a dashboard of all my workspaces.

### Phase 2 — Research Infrastructure
- As a user, I can search for papers using a research query.
- As a user, I can import papers from Semantic Scholar, arXiv, PubMed, Crossref.
- As a user, I can upload PDF files for processing.
- As a user, I can search across my paper library using natural language.

### Phase 3 — Core Agentic AI
- As a user, I can start a research workflow that searches and analyzes literature.
- As a user, I can see agents executing in real-time with status updates.
- As a user, I can view a generated literature review organized by themes.
- As a user, I can view research gap analysis with supporting citations.

### Phase 4 — Research Assistance
- As a user, I can generate research ideas based on gap analysis.
- As a user, I can generate an AI-assisted research paper draft.
- As a user, I can request an AI peer review of my draft.
- As a user, I can validate citations in my draft against real sources.
- As a user, I can export my work in PDF, Markdown, DOCX, LaTeX, BibTeX.

### Phase 5 — Production
- As an admin, I can view system usage metrics.
- As an admin, I can configure rate limits and budget caps.
- As a user, I can see my API usage and cost breakdown.

## Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | PDF processing time | <30s for 10-page paper |
| Performance | Semantic search latency | <500ms |
| Performance | Agent workflow (lit review) | <120s |
| Scalability | Concurrent workspaces | >50 per instance |
| Security | Auth | OWASP-compliant |
| Security | Data isolation | Row Level Security enforced |
| Cost | Monthly infra spend | $0 (all services on free tier) |
| Cost | LLM API cost per workflow | <$0.10 (optimized with caching) |
