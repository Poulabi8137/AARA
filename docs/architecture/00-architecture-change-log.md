# Architecture Change Log — Phase 0.5 Hardening

| ID | Change | Documents Affected | Status |
|---|---|---|---|
| CL-01 | Replaced regex PromptSanitizer with 4-stage defense-in-depth LLM Security Layer | 26 | Applied |
| CL-02 | Added RAG Protection Layer (Stage 3) — sanitizes all retrieved content before agent context | 26 | Applied |
| CL-03 | Batch embedding: `embed_batch()` default implementation, updated Pipeline and OverlapAnalysis | 10 | Applied |
| CL-04 | SentenceTransformer embedder: added batch `embed_batch()` override | 10 | Applied |
| CL-05 | Qdrant payload indexes: `workspace_id`, `paper_id`, `model_id` created at collection init | 11 | Applied |
| CL-06 | Cached JWKS verification: replaces per-request Supabase API call with local RS256 verification (1h TTL) | 06 | Applied |
| CL-07 | Workflow idempotency: `IdempotencyManager`, `idempotency_key` column, `Idempotency-Key` header support | 15, 04 | Applied |
| CL-08 | Batch state persistence: `BatchedStateManager` with async flush + checkpoint-forced flush | 15 | Applied |
| CL-09 | Async Event Bus: non-blocking queue, per-handler retry, failure isolation | 28 | Applied |
| CL-10 | AI Evaluation Framework: 8 metrics, EvaluationEngine, per-phase evaluation | 31 (new) | Applied |
| CL-11 | Cost Intelligence Dashboard: event-based cost collection, cost_metrics table, budget enforcement | 32 (new) | Applied |
| CL-12 | Fixed workflow sequence diagram (nested loop → 5 sequential phases) | 14 | Applied |
| CL-13 | Added `agent_states` table to canonical database schema and ER diagram | 04, 05 | Applied |
| CL-14 | Added `cost_metrics` and `monthly_cost_summary` tables to schema and ER diagram | 04, 05 | Applied |
| CL-15 | Updated folder structure with `security/`, expanded `cost/`, expanded `evaluation/` | 03 | Applied |
| CL-16 | Added Phase 0.5 to implementation roadmap and feature breakdown | 01, 02 | Applied |
| CL-17 | Added security layer and evaluation tests to testing strategy | 27 | Applied |
| CL-18 | Added Phase 0.5 and hardening sections to README | README | Applied |

**Total changes: 18**
