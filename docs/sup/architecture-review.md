# Supplemental — Architecture Review (Session 1)

## Original Design Assessment

The original AARA specification contained 17 agents, 37+ documents, and a broad feature set spanning literature discovery through publication-ready drafts. An honest engineering assessment surfaced the following structural weaknesses:

| Weakness | Severity | Resolution |
|---|---|---|
| 17 agents — many were deterministic functions, not autonomous agents | Critical | Collapsed to 7 true agents; remaining logic moved to reusable services |
| Novelty Estimation — unachievable for LLMs; risk of misleading users | High | Renamed to Research Overlap Analysis; outputs similarity metrics, not novelty claims |
| Full paper generation without disclaimers — academic integrity risk | High | Redefined as AI-assisted structured draft with prominent disclaimers; researcher remains in control |
| No cost control layer — no budget per workflow, no caching strategy | High | Added dedicated Cost Control layer as a first-class module |
| No background job architecture — FastAPI alone cannot handle 30s+ research workflows | Medium | Abstract JobQueue interface designed; FastAPI BackgroundTasks for v1, ARQ documented as production path |
| No streaming/WebSocket layer — user would stare at spinners | Medium | WebSocket + SSE as first-class architectural features |
| No knowledge graph for citation relationships | Low | Relational citation graph (PostgreSQL adjacency) in v1; full KG in Phase 2 |
| Two hosting platforms (Vercel + Railway) — doubled operational complexity | Low | Consolidated to single hosting platform with containerized full-stack deploy |
| Clerk Auth + Supabase DB — redundant external dependencies | Low | Consolidated to Supabase Auth + Supabase PostgreSQL |

## Final Architecture Summary

| Dimension | Decision |
|---|---|
| **Agents** | 7: Supervisor, Planning, Research, Analysis, Idea Generation, Writing, Review |
| **Services** | Cost Control, Export, PDF Pipeline, Citation Validation, Embedding (each reusable, non-agent) |
| **Vector Database** | Qdrant (primary), pgvector documented as alternative |
| **Relational Database** | Supabase PostgreSQL |
| **Authentication** | Supabase Auth (built-in, RLS compatible) |
| **Background Jobs** | Abstract JobQueue → FastAPI BackgroundTasks (v1), ARQ (documented upgrade) |
| **Streaming** | WebSocket (primary) + SSE (fallback) |
| **LLM Abstraction** | Provider-agnostic interface: OpenAI, Gemini, Groq, OpenRouter, Ollama |
| **Embeddings** | Abstract EmbeddingProvider → Sentence Transformers (local), OpenAI/text-embedding-3-small |
| **Knowledge Graph** | Relational citation graph in PostgreSQL (v1); semantic KG (Phase 2) |
| **Cost Control** | Budget tracking, response caching, prompt optimization, provider routing, rate limiting |
| **Storage** | Supabase Storage (PDFs, assets) |
| **Deployment** | Single platform (Railway or Render), Docker containerized |
| **Testing** | Unit (mocked providers) + Integration (VCR-recorded) + E2E (limited real LLM) designed from day one |
