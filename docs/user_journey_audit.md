# User Journey Audit

**Generated**: June 2026
**Scope**: Full-stack audit from a real user's perspective walking through every route

---

## Journey Map

```
Create Project → Submit Query → Launch Research → Monitor Progress → View Findings → View Citations → Export Report
     (1)            (2)             (3)              (4)              (5)            (6)              (7)
```

---

## Step 1: Create a Research Project

**Route**: `/research/new`
**Status**: ✅ **WORKS**
**Assessment**: The page loads, shows preset topic cards, accepts custom queries, submits to `POST /projects`, and redirects to `/research/[id]` on success. Loading and error states are handled.

---

## Step 2: Submit a Research Question

**Route**: `/research/new`
**Status**: ✅ **WORKS** (part of the creation flow)
**Assessment**: The objective textarea allows detailed research questions. The API accepts it.

---

## Step 3: Launch Research

**Route**: `/research/[id]`
**Status**: ⚠️ **PARTIAL**
**Assessment**: The page has a "Run Agents" button but it does nothing — no handler is wired. The button is `<Button><Play /> Run Agents</Button>` with no `onClick`. The page fetches project data from `GET /projects/{id}` (works), but the user cannot actually launch the research workflow from the UI.

**Fix needed**: Wire "Run Agents" to `POST /agents/run` or `POST /projects/{id}/execute`

---

## Step 4: Monitor Progress

**Route**: `/research/monitoring`
**Status**: ❌ **BROKEN — 100% mock data**
**Assessment**: Every piece of data on this page is hardcoded:

| Element | Source | Reality |
|---------|--------|---------|
| Stats cards | `{ Completed: '2', Running: '1', Pending: '1', Failed: '0' }` | Hardcoded numbers |
| Agent executions | `agentExecutions[]` | Hardcoded array of 4 fake agents |
| Timeline chart | `timelineData[]` | Hardcoded 10 data points |
| Communication graph | `agentCommunications[]` | Hardcoded 4 edges |
| Execution logs | Hardcoded 12 log lines | Fake timestamps and messages |
| AgentFlow component | Renders the visualizer | No real data connected |

**Fix needed**: Connect to `GET /agents/executions/{id}/status` and `GET /agents/executions` with polling

---

## Step 5: View Findings

### Route: `/research/papers`
**Status**: ⚠️ **PARTIAL — falls back to mock**
**Assessment**: The page calls `fetchPapers(projectId)` which hits `GET /research/{id}/papers` — but this endpoint **does not exist** on the backend. The API call fails, the `safeFetch` catches the error, and the page falls back to `mockPapers[]`.

### Route: `/research/literature`
**Status**: ❌ **BROKEN — 100% mock data**
**Assessment**: Hardcoded stats (`Papers Analyzed: 147`, `Key Themes: 12`), hardcoded themes array, and `mockEvidenceData` from `lib/mock-data.ts`. No API call is made at all.

### Route: `/research/gaps`
**Status**: ⚠️ **PARTIAL — falls back to mock**
**Assessment**: Calls `fetchGapAnalysis(projectId)` which hits `GET /research/{id}/gap-analysis` — endpoint **does not exist**. Falls back to `fallbackGaps[]`.

### Route: `/research/directions`
**Status**: ⚠️ **PARTIAL — falls back to mock**
**Assessment**: Calls `fetchNovelDirections(projectId)` which hits `GET /research/{id}/novel-directions` — endpoint **does not exist**. Falls back to `fallbackDirections[]`.

**Fix needed**: Create backend endpoints for research outputs, or consolidate into a single `/projects/{id}/outputs` endpoint

---

## Step 6: View Citations

**Route**: `/research/citations`
**Status**: ❌ **BROKEN — 100% mock data**
**Assessment**: Format cards are static. "Generated Citations" section renders 5 hardcoded citation cards. "Generate All Citations" and "Export Bibliography" buttons do nothing — no handlers. No API calls are made.

**Fix needed**: Connect to real citations from agent output, wire button handlers

---

## Step 7: Export Report

**Route**: `/research/report`
**Status**: ❌ **BROKEN — setTimeout simulation**
**Assessment**: Selecting a template, naming the report, and clicking "Generate Report" triggers a `setTimeout(() => {...}, 2000)` that clears the form — no actual report is generated. "Generated Reports" section shows 3 hardcoded entries. Export format buttons (PDF, DOCX, Markdown, LaTeX) do nothing.

**Fix needed**: Wire to `POST /reports/generate` and `POST /reports/export`

---

## Side Routes

### Route: `/dashboard`
**Status**: ❌ **BROKEN — 100% mock data**
**Assessment**: Stats cards (`Active Projects: 3`, `Total Papers: 145`, `Research Gaps: 25`) are hardcoded. Recent Research list shows 3 hardcoded entries with fake paper/gap/direction counts. No API calls are made.

**Fix needed**: Connect to `GET /projects` and `GET /agents/executions`

### Route: `/settings`
**Status**: ❌ **BROKEN — toast-only "save"**
**Assessment**: "Save Changes" shows a success toast that disappears after 3 seconds — no data is persisted. No backend endpoint exists for user profile updates. API key configuration and preferences are decorative.

**Fix needed**: Add `PUT /auth/me` endpoint on backend, wire frontend to persist

---

## Cross-Cutting Issues

| Issue | Impact |
|-------|--------|
| No `loading.tsx` files anywhere | Blank white screens during navigation; no skeleton loading state |
| No `error.tsx` files anywhere | Unhandled errors crash the entire page — no graceful error boundaries |
| `apiClient` calls routes that don't exist | Every research page silently fails and falls back to mock data |
| No WebSocket integration | Monitoring page is static — no real-time updates |
| No route protection for settings | Unauthenticated users can access `/settings` |
| Dashboard is disconnected entirely | No real project or execution data shown to the user |

---

## Summary

| Step | Route | Status | Impact to User |
|------|-------|--------|---------------|
| 1. Create project | `/research/new` | ✅ Works | User creates project successfully |
| 2. Submit query | `/research/new` | ✅ Works | Query is submitted with project |
| 3. Launch research | `/research/[id]` | ⚠️ Button does nothing | User cannot start research |
| 4. Monitor progress | `/research/monitoring` | ❌ Mock visuals | User sees fake but convincing charts |
| 5. View findings | Multiple routes | ❌ All fall back to mock | User sees fake papers/gaps/directions |
| 6. View citations | `/research/citations` | ❌ Mock citations | User cannot generate or export citations |
| 7. Export report | `/research/report` | ❌ setTimeout simulation | Report generation is completely fake |

**Overall**: 1 of 7 core journey steps works end-to-end. The UI is visually polished but functionally incomplete.
