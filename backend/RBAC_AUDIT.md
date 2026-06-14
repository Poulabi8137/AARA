# AgentWatch RBAC Audit & Authorization Review

**Audit Date:** 2026-06-13
**Scope:** Full backend API (`app/`) — endpoints, middleware, service layer
**Classification:** Internal — Confidential

---

## 1. Authorization Matrix

| Role         | Projects CRUD | Sessions CRUD | Reports CRUD | Documents CRUD | Agents / Workflow | Evaluation | Debug Routes | Admin / Users | System Config |
|--------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Admin**    | All | All | All | All | All | All | ✓    | ✓    | ✓    |
| **Researcher** | Own | Own | Own | Own | Run  | View | ✗    | ✗    | ✗    |
| **Viewer**   | R   | R   | R   | R   | ✗   | View | ✗    | ✗    | ✗    |

**Legend:** R=Read, Own=Own resources only, All=All resources, ✓=Enabled, ✗=Disabled

---

## 2. API Endpoint Protection Status

### 2.1 Authentication Endpoints

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| POST | `/auth/register` | ✗ | ✗ | Public — no auth required | None (intentionally public) |
| POST | `/auth/login` | ✗ | ✗ | Public — no auth required | None (intentionally public) |
| POST | `/auth/refresh` | ✗ | ✗ | Public — refresh token in body | Rate limiting already applied |

### 2.2 Health & Metrics

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| GET | `/health` | ✗ | ✗ | Public | None |
| GET | `/metrics` | ✗ | ✗ | Public (Prometheus scrape) | Should restrict to internal network |

### 2.3 Projects

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| GET | `/projects` | ✓ | ✗ | Auth only — lists all projects | **CRITICAL** — should scope to user's projects; needs `researcher+` |
| POST | `/projects` | ✓ | ✗ | Auth only | **HIGH** — needs `researcher+` role check |
| GET | `/projects/{id}` | ✓ | ✗ | Auth only | **CRITICAL** — no ownership check (IDOR); needs `viewer+` |
| PUT | `/projects/{id}` | ✓ | ✗ | Auth only | **CRITICAL** — no ownership check; needs `researcher+` on owned |
| DELETE | `/projects/{id}` | ✓ | ✗ | Auth only | **CRITICAL** — no ownership check; needs `admin` only |

### 2.4 Research Sessions

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| GET | `/sessions` | ✓ | ✗ | Auth only — lists all sessions | **HIGH** — should scope to user's projects; needs `viewer+` |
| POST | `/sessions` | ✓ | ✗ | Auth only | **HIGH** — needs `researcher+` role check |
| GET | `/sessions/{id}` | ✓ | ✗ | Auth only | **CRITICAL** — no ownership check (IDOR) |

### 2.5 Reports

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| GET | `/reports` | ✓ | ✗ | Auth only — lists all reports | **HIGH** — should scope to user; needs `viewer+` |
| POST | `/reports` | ✓ | ✗ | Auth only | **HIGH** — needs `researcher+` role check |

### 2.6 Documents & Retrieval

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| POST | `/documents/upload` | ✓ | ✗ | Auth only — no project ownership verify | **HIGH** — needs `researcher+` + project ownership |
| GET | `/documents` | ✓ | ✗ | Auth only — lists across all projects | **CRITICAL** — no project scoping; needs `viewer+` |
| DELETE | `/documents/{id}` | ✓ | ✗ | Auth only | **CRITICAL** — no ownership check; needs `researcher+` |
| POST | `/retrieval/search` | ✓ | ✗ | Auth only | **HIGH** — needs `viewer+` |
| POST | `/retrieval/context` | ✓ | ✗ | Auth only | **HIGH** — needs `viewer+` |

### 2.7 Agents & Workflow

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| POST | `/agents/run` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth, no rate limiting beyond middleware; needs `researcher+` |
| GET | `/agents/executions` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `viewer+` or `admin` |
| GET | `/agents/executions/{id}` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth |
| POST | `/agents/cancel/{id}` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `researcher+` |
| GET | `/agents/registry` | ✗ | ✗ | **NONE** | **HIGH** — exposes full agent registry publicly |

### 2.8 Report Generator

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| POST | `/reports/generate` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `researcher+` |
| POST | `/reports/preview` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `researcher+` |
| POST | `/reports/export` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `viewer+` |

### 2.9 Debug Routes

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| POST | `/retrieval/debug` | ✗ | ✗ | **NONE** | **CRITICAL** — exposes full retrieval internals; should be `admin` only + gated |
| POST | `/summaries/debug` | ✗ | ✗ | **NONE** | **CRITICAL** — exposes summarizer internals; `admin` only |
| POST | `/gaps/debug` | ✗ | ✗ | **NONE** | **CRITICAL** — exposes gap analysis internals; `admin` only |

### 2.10 Evaluation

| Method | Path | Auth | Role Check | Current Protection | Missing |
|--------|------|:----:|:----------:|--------------------|---------|
| GET | `/evaluation/runs` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `viewer+` |
| GET | `/evaluation/runs/{id}` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth |
| GET | `/evaluation/benchmarks` | ✗ | ✗ | **NONE** | **HIGH** — read-only but no auth |
| POST | `/evaluation/benchmark/run` | ✗ | ✗ | **NONE** | **CRITICAL** — compute-costly endpoint, no auth |
| GET | `/evaluation/scorecard/{id}` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth |
| POST | `/evaluation/evaluate` | ✗ | ✗ | **NONE** | **CRITICAL** — no auth; needs `researcher+` |
| GET | `/evaluation/trends` | ✗ | ✗ | **NONE** | **HIGH** — no auth |
| GET | `/evaluation/distributions` | ✗ | ✗ | **NONE** | **HIGH** — no auth |

---

## 3. Missing Role Checks — Consolidated Severity

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 16 | Endpoints with no authentication at all (agents, evaluation, report generator, debug) |
| **HIGH** | 10 | Authenticated endpoints lacking role checks or resource ownership verification |
| **MEDIUM** | 4 | Authenticated endpoints that scope by user but need explicit role enforcement |
| **LOW** | 2 | Read-only public endpoints that should ideally have lightweight auth |

---

## 4. Least Privilege Violations

| # | Violation | Endpoint(s) | Risk | Remediation |
|---|-----------|-------------|------|-------------|
| 1 | Unauthenticated agent execution | `POST /agents/run` | Anyone can run expensive workflows (cost, DoS) | Require `researcher+` role |
| 2 | Unauthenticated execution listing | `GET /agents/executions` | Any actor can enumerate all executions | Require `viewer+` |
| 3 | Unauthenticated evaluation | All `evaluation/` endpoints | Sensitive quality metrics exposed | Require `viewer+` for GET, `researcher+` for POST |
| 4 | Debug routes publicly accessible | All `debug/` endpoints | Internal state, prompts, RAG context leaked | Gate behind `admin` role + feature flag |
| 5 | IDOR on all resource-by-ID endpoints | `projects/{id}`, `sessions/{id}`, `documents/{id}` | Cross-tenant data access | Add ownership verification dependency |
| 6 | Researcher can delete any document | `DELETE /documents/{id}` | No project ownership check | Check document->project->user ownership |
| 7 | No admin-only designation | All system-level operations | No mechanism for admin guard | Implement `require_role(UserRole.ADMIN)` checks |
| 8 | Viewer can create/delete projects | `POST /projects`, `DELETE /projects/{id}` | Viewer role allows write ops | Enforce `researcher+` for mutations |

---

## 5. Current Protection Mechanisms (Already Implemented)

- **Authentication:** JWT-based with access/refresh token pattern (`app/core/security.py`)
- **Auth middleware:** `get_current_user` dependency injected in most resource routers (but missing from agents, evaluation, report generator, debug routes)
- **Role-based dependencies:** `require_role()` function exists in `app/services/auth_service.py:86` but is **never used** in any router
- **Rate limiting:** Redis-backed sliding window on auth endpoints, document upload, agent run (`app/middleware/rate_limit.py`)
- **Security headers:** `app/middleware/security_headers.py` sets CSP, HSTS, X-Frame-Options, etc.
- **Prometheus metrics middleware:** `app/core/observability.py` with `/metrics` endpoint
- **Request logging:** `app/middleware/setup.py` — request ID, method, path, status, elapsed time

---

## 6. Recommendations

### P0 — Immediate (Fix Before Production)

1. **Add authentication to all unprotected endpoints:**
   - `app/api/agents.py` — inject `get_current_user` into all routes
   - `app/api/evaluation.py` — inject `get_current_user` into all routes
   - `app/api/report_generator.py` — inject `get_current_user` into all routes
   - `app/api/retrieval_debug.py`, `summarizer_debug.py`, `gap_debug.py` — inject auth

2. **Apply role enforcement using the existing `require_role()` helper:**
   ```python
   from app.services.auth_service import require_role, UserRole
   
   # Admin-only debug routes
   @router.post("/retrieval/debug")
   async def debug_retrieval(..., admin: User = Depends(require_role(UserRole.ADMIN))):
   
   # Researcher+ for mutations
   @router.post("/projects")
   async def create_project(..., user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER))):
   
   # Viewer+ for read operations
   @router.get("/projects")
   async def list_projects(..., user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER, UserRole.VIEWER))):
   ```

3. **Implement resource ownership verification (prevent IDOR):**
   ```python
   async def get_owned_project(project_id: UUID, current_user: User = Depends(get_current_user), db = Depends(get_db)) -> ResearchProject:
       project = await db.get(ResearchProject, project_id)
       if project is None or (project.creator_id != current_user.id and current_user.role != UserRole.ADMIN):
           raise HTTPException(403, "Project not found or access denied")
       return project
   ```
   Apply similar `get_owned_*` patterns for sessions, documents, and reports.

### P1 — Short-Term (Next Sprint)

4. **Gate debug routers behind `settings.debug` feature flag** in `app/main.py`:
   ```python
   if settings.debug:
       app.include_router(retrieval_debug_router)
       app.include_router(summarizer_debug_router)
       app.include_router(gap_debug_router)
   ```

5. **Scope list endpoints by user:** Modify `list_projects`, `list_sessions`, `list_reports`, `list_documents` to filter by `current_user.id` (admins see all, others see own).

6. **Restrict `/metrics` to internal network** or add authentication for production.

7. **Add audit logging for authorization failures:** Log each 403/401 with user ID, endpoint, timestamp, and source IP.

### P2 — Medium-Term (Roadmap)

8. **Implement API key authentication for programmatic access** with scoped permissions.

9. **Add token revocation via Redis blocklist** (already partially designed in security audit).

10. **Implement session-bound tokens** (embed IP/User-Agent hash in JWT).

11. **Add admin panel endpoints** for user management, role assignment, and system configuration.

---

## 7. Summary

| Category | Count | P0 | P1 | P2 |
|----------|-------|----|----|----|
| Missing Authentication | 16 | 16 | 0 | 0 |
| Missing Role Checks | 10 | 8 | 2 | 0 |
| IDOR Vulnerabilities | 8 | 8 | 0 | 0 |
| Least Privilege Violations | 8 | 6 | 2 | 0 |
| **Total** | **42** | **38** | **4** | **0** |

The `require_role()` helper exists in the codebase but is not used anywhere. All endpoints that already have `get_current_user` injected are one dependency addition away from role enforcement. The 16 unprotected endpoints require adding the auth dependency as a first step, then layering role checks.
