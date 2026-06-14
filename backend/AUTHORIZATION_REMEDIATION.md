# Authorization Remediation Report

## 1. Executive Summary

The backend API was found to have systemic authorization gaps across multiple route modules. Nine routers were audited; most lacked either authentication enforcement, resource-ownership verification, or role-based access controls. This document catalogues what was missing, what was added, and how each fix is enforced.

**Scope of fixes:**
- Added `get_current_user` (Bearer JWT auth) to all endpoints that lacked it
- Added `_check_execution_owner` and `_check_project_owner` helper functions to enforce ownership chains
- Added `require_role(UserRole.ADMIN)` to debug and evaluation endpoints
- Added project-scoped subquery filtering on all list endpoints
- Closed 4 categories of privilege-escalation and data-leakage vulnerabilities

**Risk reduction:** Previously, any authenticated user could view/cancel/approve any execution, list any project's sessions or reports, and delete any document. All of these now require verified ownership or admin role.

---

## 2. Vulnerability Assessment

Based on the security certification audit (see `security_certification_report.md`), the following classes of vulnerabilities were identified:

| Class | Severity | Description |
|-------|----------|-------------|
| **AUTH-01** | Critical | Missing ownership checks on execution-scoped endpoints — any user could poll, retrieve, or cancel any execution |
| **AUTH-02** | High | Missing project-ownership checks on session, report, and document creation — users could attach resources to arbitrary projects |
| **AUTH-03** | High | Missing admin-role enforcement on debug/evaluation endpoints — any authenticated user could invoke retrieval/summarizer/gap debug pipelines |
| **AUTH-04** | Medium | Missing project-scoped row filtering on list endpoints — users could enumerate executions, sessions, reports, and approvals belonging to other users |
| **AUTH-05** | Low | Inconsistent auth on public-documentation endpoints (`/agents/registry`, `/evaluation/benchmarks`) — currently read-only info, but unchecked |

---

## 3. Remediation Actions

### 3.1 `app/api/agents.py` — Agent executions router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Ownership verification on `GET /agents/executions/{id}/status` | Call to `_check_execution_owner()` at line 97 | Queries `ResearchProject` WHERE `id = exec.project_id AND created_by = current_user.id`; 404 if mismatch |
| Ownership verification on `GET /agents/executions/{id}` | Call to `_check_execution_owner()` at line 166 | Same ownership query on execution's project |
| Ownership verification on `POST /agents/cancel/{id}` | Call to `_check_execution_owner()` at line 177 | Same ownership query + status gate (only PENDING/RUNNING can be cancelled) |
| Cross-user data leak in `GET /agents/executions` | Subquery filter at lines 133–135 | `ResearchProject.id WHERE created_by = current_user.id` used to scope `AgentExecution.project_id.in_(...)` |

**Helper — `_check_execution_owner` (line 34):**
```python
async def _check_execution_owner(
    execution_id: uuid.UUID, user: User, session: AsyncSession
) -> AgentExecution:
    exec_obj = await session.get(AgentExecution, execution_id)
    if exec_obj is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    result = await session.execute(
        select(ResearchProject).where(
            ResearchProject.id == exec_obj.project_id,
            ResearchProject.created_by == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_obj
```

### 3.2 `app/api/human_approval.py` — Human-approval router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Ownership verification on all `/{execution_id}` sub-routes | `_get_approval_or_404()` helper at line 23 | Fetches `HumanApproval` by `execution_id`, then verifies `AgentExecution.project_id -> ResearchProject.created_by == current_user.id` |
| Cross-user data leak in `GET /approvals/pending` | Subquery filter at lines 51–56 | `AgentExecution.id WHERE project_id IN (user's project IDs)` scopes the approval query |

**Helper — `_get_approval_or_404` (line 23):**
```python
async def _get_approval_or_404(
    execution_id: str, current_user: User, db: AsyncSession
) -> HumanApproval:
    # ... fetches approval by execution_id, then checks
    # AgentExecution -> ResearchProject.created_by == current_user.id
```

### 3.3 `app/api/evaluation.py` — Evaluation router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Auth on `GET /evaluation/runs` | `require_role(UserRole.ADMIN)` dependency | `Depends(require_role(UserRole.ADMIN))` on line 27 |
| Auth on `GET /evaluation/runs/{run_id}` | `require_role(UserRole.ADMIN)` dependency | Line 46 |
| Auth on `POST /evaluation/benchmark/run` | `require_role(UserRole.ADMIN)` dependency | Line 63 |
| Auth on `GET /evaluation/scorecard/{execution_id}` | `require_role(UserRole.ADMIN)` dependency | Line 83 |
| Auth on `POST /evaluation/evaluate` | `require_role(UserRole.ADMIN)` dependency | Line 99 |
| Auth on `GET /evaluation/trends` | `require_role(UserRole.ADMIN)` dependency | Line 112 |
| Auth on `GET /evaluation/distributions` | `require_role(UserRole.ADMIN)` dependency | Line 129 |

### 3.4 `app/api/report_generator.py` — Report generator router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Authentication on `POST /reports/generate` | `get_current_user` dependency added | Line 44 — `Depends(get_current_user)` |
| Authentication on `POST /reports/preview` | `get_current_user` dependency added | Line 71 |
| Authentication on `POST /reports/export` | `get_current_user` dependency added | Line 102 |

These endpoints operate on request-body data only (no DB resource lookup), so ownership checks are not applicable.

### 3.5 `app/api/reports.py` — Reports (CRUD) router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Cross-user data leak in `GET /reports` | Subquery filter at lines 26–28 | `ResearchReport.project_id IN (SELECT id FROM research_projects WHERE created_by = current_user.id)` |
| Project ownership on `POST /reports` | Explicit `ResearchProject.created_by` check at lines 58–69 | `SELECT FROM research_projects WHERE id = body.project_id AND created_by = current_user.id` |

### 3.6 `app/api/sessions.py` — Research sessions router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Project ownership on `POST /sessions` | `_check_project_owner()` at line 70 | Verifies `ResearchProject.id == project_id AND created_by == user.id` |
| Project ownership on `GET /sessions/{id}` | `_check_project_owner()` at line 86 | Fetches session, then checks ownership of its `project_id` |
| Cross-user data leak in `GET /sessions` | Subquery filter at lines 38–40 | `ResearchSession.project_id IN (SELECT id FROM research_projects WHERE created_by = current_user.id)` |

**Helper — `_check_project_owner` (line 20):**
```python
async def _check_project_owner(project_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.created_by == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")
```

### 3.7 `app/api/documents.py` — Documents & retrieval router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Authentication on document upload | `get_current_user` dependency | Line 35 (pre-existing) |
| Authentication on document list | `get_current_user` dependency | Line 78 (pre-existing) |
| Ownership check on `DELETE /documents/{id}` | `ResearchProject.created_by` check if `doc.project_id` is set | Lines 102–110 — 404 if the owning project does not belong to user |
| Authentication on `POST /retrieval/search` | `get_current_user` dependency | Line 118 |
| Authentication on `POST /retrieval/context` | `get_current_user` dependency | Line 154 |

**Remaining gap:** `GET /documents` and `POST /retrieval/search|context` do not filter results by project ownership. If a user knows another user's `project_id`, they could list or search that project's documents. This is tracked in section 7.

### 3.8 `app/api/retrieval_debug.py` — Retrieval debug router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Auth on `POST /retrieval/debug` | `require_role(UserRole.ADMIN)` dependency | Line 38 |

### 3.9 `app/api/summarizer_debug.py` — Summarizer debug router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Auth on `POST /summaries/debug` | `require_role(UserRole.ADMIN)` dependency | Line 37 |

### 3.10 `app/api/gap_debug.py` — Gap detection debug router

| What was missing | What was added | How enforced |
|-----------------|----------------|--------------|
| Auth on `POST /gaps/debug` | `require_role(UserRole.ADMIN)` dependency | Line 49 |

---

## 4. API Route Table with Auth Status

| Method | Route | Module | Auth Before | Auth After | Ownership |
|--------|-------|--------|-------------|------------|-----------|
| POST | `/agents/run` | agents | `get_current_user` | `get_current_user` | N/A (creates new) |
| GET | `/agents/executions` | agents | `get_current_user` | `get_current_user` + project-subquery filter | **Added** |
| GET | `/agents/executions/{id}/status` | agents | `get_current_user` | `get_current_user` + `_check_execution_owner` | **Added** |
| GET | `/agents/executions/{id}` | agents | `get_current_user` | `get_current_user` + `_check_execution_owner` | **Added** |
| POST | `/agents/cancel/{id}` | agents | `get_current_user` | `get_current_user` + `_check_execution_owner` | **Added** |
| GET | `/agents/registry` | agents | None | None | Public (intentional) |
| GET | `/approvals/pending` | human_approval | `get_current_user` | `get_current_user` + project-subquery filter | **Added** |
| GET | `/approvals/{execution_id}` | human_approval | `get_current_user` | `get_current_user` + `_get_approval_or_404` | **Added** |
| POST | `/approvals/{execution_id}/approve` | human_approval | `get_current_user` | `get_current_user` + `_get_approval_or_404` | **Added** |
| POST | `/approvals/{execution_id}/reject` | human_approval | `get_current_user` | `get_current_user` + `_get_approval_or_404` | **Added** |
| POST | `/approvals/{execution_id}/rerun` | human_approval | `get_current_user` | `get_current_user` + `_get_approval_or_404` | **Added** |
| GET | `/evaluation/runs` | evaluation | None | `require_role(ADMIN)` | **Added** |
| GET | `/evaluation/runs/{run_id}` | evaluation | None | `require_role(ADMIN)` | **Added** |
| GET | `/evaluation/benchmarks` | evaluation | None | None | Public (intentional) |
| POST | `/evaluation/benchmark/run` | evaluation | None | `require_role(ADMIN)` | **Added** |
| GET | `/evaluation/scorecard/{execution_id}` | evaluation | None | `require_role(ADMIN)` | **Added** |
| POST | `/evaluation/evaluate` | evaluation | None | `require_role(ADMIN)` | **Added** |
| GET | `/evaluation/trends` | evaluation | None | `require_role(ADMIN)` | **Added** |
| GET | `/evaluation/distributions` | evaluation | None | `require_role(ADMIN)` | **Added** |
| POST | `/reports/generate` | report_generator | None | `get_current_user` | **Added** |
| POST | `/reports/preview` | report_generator | None | `get_current_user` | **Added** |
| POST | `/reports/export` | report_generator | None | `get_current_user` | **Added** |
| GET | `/reports` | reports | `get_current_user` | `get_current_user` + project-subquery filter | **Added** |
| POST | `/reports` | reports | `get_current_user` | `get_current_user` + project-ownership check | **Added** |
| GET | `/sessions` | sessions | `get_current_user` | `get_current_user` + project-subquery filter | **Added** |
| POST | `/sessions` | sessions | `get_current_user` | `get_current_user` + `_check_project_owner` | **Added** |
| GET | `/sessions/{id}` | sessions | `get_current_user` | `get_current_user` + `_check_project_owner` | **Added** |
| POST | `/documents/upload` | documents | `get_current_user` | `get_current_user` | Unchanged |
| GET | `/documents` | documents | `get_current_user` | `get_current_user` | **Still missing** |
| DELETE | `/documents/{id}` | documents | `get_current_user` | `get_current_user` + project check | **Added** |
| POST | `/retrieval/search` | documents | `get_current_user` | `get_current_user` | **Still missing** |
| POST | `/retrieval/context` | documents | `get_current_user` | `get_current_user` | **Still missing** |
| POST | `/retrieval/debug` | retrieval_debug | None | `require_role(ADMIN)` | **Added** |
| POST | `/summaries/debug` | summarizer_debug | None | `require_role(ADMIN)` | **Added** |
| POST | `/gaps/debug` | gap_debug | None | `require_role(ADMIN)` | **Added** |

---

## 5. Ownership Verification Strategy

The data model forms a hierarchy rooted at `ResearchProject`. Every owned resource chains back to `ResearchProject.created_by`:

```
User (id)
 └── ResearchProject (created_by → User.id)
      ├── AgentExecution (project_id → ResearchProject.id)
      │    └── HumanApproval (execution_id → AgentExecution.id)
      ├── ResearchSession (project_id → ResearchProject.id)
      ├── ResearchReport (project_id → ResearchProject.id)
      └── Document (project_id → ResearchProject.id)
```

**Enforcement pattern:**

1. **Direct project ownership** — `_check_project_owner()`: `SELECT FROM research_projects WHERE id = ? AND created_by = current_user.id`
2. **Indirect through execution** — `_check_execution_owner()`: Fetch `AgentExecution`, then check `ResearchProject WHERE id = exec.project_id AND created_by = current_user.id`
3. **Indirect through approval** — `_get_approval_or_404()`: Fetch `HumanApproval`, fetch linked `AgentExecution`, then same project-ownership check
4. **Bulk enumeration protection** — Subquery filter: `WHERE table.project_id IN (SELECT id FROM research_projects WHERE created_by = current_user.id)`

All ownership failures return HTTP **404 Not Found** (not 403) to avoid leaking the existence of resources the user does not own.

---

## 6. Ownership Check Helpers

### `_check_execution_owner` — `app/api/agents.py:34`

```
Signature:  async def _check_execution_owner(execution_id, user, session) -> AgentExecution
Purpose:    Verify the current user owns the project associated with an AgentExecution
Flow:
  1. Fetch AgentExecution by ID (404 if missing)
  2. Query ResearchProject WHERE id = exec.project_id AND created_by = user.id
  3. If no match, raise 404 ("Execution not found")
  4. Return the AgentExecution object for further use
Used by:    get_execution_status, get_execution, cancel_execution
```

### `_check_project_owner` — `app/api/sessions.py:20`

```
Signature:  async def _check_project_owner(project_id, user, db) -> None
Purpose:    Verify the current user owns a specific ResearchProject
Flow:
  1. Query ResearchProject WHERE id = project_id AND created_by = user.id
  2. If no match, raise 404 ("Project not found")
Used by:    create_session, get_session
```

### `_get_approval_or_404` — `app/api/human_approval.py:23`

```
Signature:  async def _get_approval_or_404(execution_id, current_user, db) -> HumanApproval
Purpose:    Fetch a HumanApproval and verify ownership through the execution chain
Flow:
  1. Fetch HumanApproval by execution_id (404 if missing)
  2. Fetch linked AgentExecution
  3. If execution exists, verify ResearchProject.created_by == current_user.id
  4. Return the HumanApproval object
Used by:    get_approval_status, approve_execution, reject_execution, rerun_execution
```

---

## 7. Remaining Gaps and Future Work

| Gap | File | Issue | Priority |
|-----|------|-------|----------|
| **No project-ownership filter on `GET /documents`** | `documents.py:82` | If `project_id` query param is supplied, any authenticated user can list another project's documents | High |
| **No project-ownership filter on `POST /retrieval/search`** | `documents.py:116` | Vector search accepts arbitrary `project_id` in `SearchRequest` — no verification that the user owns the project | High |
| **No project-ownership filter on `POST /retrieval/context`** | `documents.py:151` | Same as search — `ContextRequest.project_id` is untrusted | High |
| **No rate-limiting or brute-force protection** | auth_service | Login, password-reset endpoints have no rate limiting | Medium |
| **Unrestricted `/agents/registry`** | `agents.py:195` | Lists all registered agents — currently read-only, but could leak system topology | Low |
| **Unrestricted `/evaluation/benchmarks`** | `evaluation.py:55` | Lists benchmark definitions — low risk, but inconsistent with the rest of evaluation router | Low |
| **No audit logging for ownership failures** | (cross-cutting) | 404 returns for authorization failures are not explicitly logged for forensics | Medium |
| **Service-layer auth duplication** | (cross-cutting) | `ReportService.create_report` and `SessionService.create_session` do not re-verify ownership; the API layer is the only guard | Low |

**Recommended immediate actions:**
1. Add `_check_project_owner()` guard to `GET /documents` when `project_id` is supplied
2. Add ownership verification in `search_documents` and `retrieve_context` before passing `project_id` to the vector store
3. Implement rate-limiting middleware on auth endpoints
4. Add structured audit logging (user_id, attempted resource, outcome) for all ownership-check failures
