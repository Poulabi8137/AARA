# Feature Gap Analysis

**Date**: June 2026
**Scope**: Full-stack audit — backend (FastAPI) and frontend (Next.js)

---

## Executive Summary

AARA has a well-architected foundation with significant gaps between the designed capabilities and the implemented functionality. The agent system orchestrates correctly but only 1 of 5 agents (Planner) actually uses an LLM. The frontend is visually polished but only auth pages connect to real APIs. All other pages use hardcoded mock data.

---

## Critical Gaps (Blocking Demo)

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| 1 | **proxy.ts not wired as middleware** | `proxy.ts` exports `proxy()` not `middleware()` — Next.js never invokes it | All protected routes are publicly accessible |
| 2 | **Broken navigation** | Dashboard links to `/research/new` and `/research/[id]` — neither route exists | 404 errors for core user flows |
| 3 | **All research pages use mock data** | `papers/`, `literature/`, `gaps/`, `directions/`, `citations/` | No real data flows through the system |
| 4 | **Report generation is setTimeout** | `research/report/page.tsx` | Report generation is completely simulated |
| 5 | **TypeScript errors hidden** | `next.config.mjs` has `ignoreBuildErrors: true` | Broken types never caught |

## High-Impact Gaps

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| 6 | **Only Planner calls an LLM** | Agents: Retriever, Summarizer, Gap Detector, Report Generator are all rule-based | No AI-driven content understanding |
| 7 | **Summarizer doesn't summarize** | `summarizer_agent.py` — keyword extraction + template interpolation only | "Summaries" are meaningless |
| 8 | **Human approval never pauses** | `human_approval_node.py` — no `interrupt()`, no waiting | Cosmetic feature |
| 9 | **Mock data injected silently** | `retrieval_agent.py` — fake documents enter pipeline without clear labeling | Users see fake evidence as real |
| 10 | **No research state persistence** | `lib/store.ts` — no research Zustand store exists | Refresh loses all data |
| 11 | **WebSocket client never used** | `lib/websocket-client.ts` — complete but never imported | Real-time monitoring is static |
| 12 | **PDF/DOCX exports are stubs** | `report_generator.py` — returns "not yet implemented" message | Key feature is broken |

## Medium-Impact Gaps

| # | Gap | Location | Impact |
|---|-----|----------|--------|
| 13 | **Errors silently swallowed** | `graphs/nodes.py` — agent failures logged but status overridden to "complete" | Workflow never fails, produces garbage |
| 14 | **Retry routing non-functional** | `graphs/research_graph.py` — errors never propagated to state | Retry mechanism is dead code |
| 15 | **Missing loading/error boundaries** | Frontend — no `loading.tsx` or `error.tsx` files anywhere | Blank screens on errors |
| 16 | **Empty states missing** | All pages — no "no data" messages | Empty arrays render blank UIs |
| 17 | **Settings page non-functional** | `app/settings/page.tsx` | "Save Changes" does nothing |
| 18 | **Buttons without handlers** | Evidence panel "Export as Citation", directions "View Details" | Dead click targets |
| 19 | **SkeletonLine Tailwind bug** | `components/ui/skeleton.tsx` — runtime template literal in className | Broken skeleton animation |
| 20 | **Dead code imports** | `package.json` — `swr`, `d3-hierarchy`, `d3-shape` installed but unused | Unnecessary dependencies |

---

## Fixes Applied

During this audit, the following fixes were applied:

- **proxy.ts**: Renamed `proxy()` → `middleware()`, created `middleware.ts` re-export — route protection now works
- **Missing routes**: Created `/research/new` and `/research/[id]` pages with proper API integration
- **Research store**: Created `useResearchStore` in `lib/store.ts` with `fetchProjects` and `createProject`
- **next.config.mjs**: Removed `ignoreBuildErrors: true`, configured `remotePatterns` for images
- **package.json**: Renamed from `my-project` to `aara`
- **SkeletonLine**: Changed `w-[${width}]` to `style={{ width }}` for proper Tailwind JIT compat
- **PDF/DOCX exports**: Replaced stub messages with full HTML export content
- **Retrieval mock data**: Changed from `[mock]` to `[SIMULATED]` with realistic content and proper labeling
- **Dead code**: Removed re-import of `multi_collection_search` inside exception handler

## Fixes Not Applied (Requires Architectural Changes)

| Gap | Why deferred | Workaround |
|-----|-------------|------------|
| Only 1/5 agents calls LLM | Requires adding LLM calls to 4 agents + prompt engineering | Demo uses Planner output quality as showcase |
| Human approval interrupt | Requires LangGraph `interrupt()` which changes graph flow | Approval record created; manual bypass in demo |
| Mock data in all pages | Frontend pages need full API integration | Created `/research/new` and `[id]` pages as templates for future integration |
| Settings page persistence | Requires backend user profile endpoint | Docs explain limitation |
