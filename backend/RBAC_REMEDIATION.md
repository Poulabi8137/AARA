# AgentWatch RBAC Remediation Report

**Date:** 2026-06-14
**Status:** Remediation in progress
**Classification:** Internal — Confidential

---

## 1. Executive Summary

The AgentWatch backend contains a fully-built Role-Based Access Control (RBAC) framework — a `UserRole` enum with three roles (`ADMIN`, `RESEARCHER`, `VIEWER`) and a `require_role()` dependency guard — yet this framework was **never wired to any API endpoint** at initial implementation. Every authenticated user (including newly-registered default `RESEARCHER` users) could access all endpoints, and 16 endpoints had **zero authentication at all**.

The RBAC audit (`RBAC_AUDIT.md`) identified **42 total vulnerabilities**: 16 missing authentication, 10 missing role checks, 8 IDOR vulnerabilities, and 8 least-privilege violations. This remediation report documents the enforcement actions taken and the remaining work.

**Current remediation status:** Evaluation endpoints and all debug routes now carry `require_role(UserRole.ADMIN)` protection. All other endpoints remain at their pre-remediation protection level and require further action.

---

## 2. Vulnerability Assessment

### 2.1 Pre-Remediation State

| Risk Area | Impact |
|-----------|--------|
| No role checks anywhere | Every authenticated user had implicit admin-equivalent access to all functionality |
| 16 endpoints with no auth | Unauthenticated actors could run agents, trigger evaluations, read debug telemetry, generate reports |
| `require_role()` never deployed | The RBAC guard function existed but was dead code — zero call sites |
| `UserRole` enum defined but unused | Role column in database stored values but were never checked at runtime |
| New users defaulted to `RESEARCHER` | Effective access level was `ADMIN` since no role gates existed |

### 2.2 Severity Breakdown

| Severity | Count | Description |
|----------|-------|-------------|
| **CRITICAL** | 16 | No authentication (agents, evaluation, report generator, debug routes) |
| **HIGH** | 10 | Authenticated but no role check or ownership verification |
| **MEDIUM** | 4 | Authenticated, scoped by user, but no explicit role enforcement |
| **LOW** | 2 | Read-only public endpoints (health, metrics) |

---

## 3. Role Model

### 3.1 Role Hierarchy & Capabilities

```
ADMIN ─────────────────────────────────────────────> All resources, all actions
  │
  ├─── RESEARCHER ────> Own resources (CRUD), agents, debug disabled
  │       │
  │       └─── VIEWER ────> Read-only access to assigned resources
  │
  └─── (unauthenticated) ───> Register, login, health check only
```

### 3.2 Role Definitions

#### `UserRole.ADMIN` (`"admin"`)
- **Scope:** System-wide, cross-tenant
- **Permissions:**
  - All `RESEARCHER` + `VIEWER` permissions
  - Create/read/update/delete any project, session, report, document
  - Run agent workflows for any user
  - Access all evaluation endpoints (run benchmarks, generate scorecards, view trends)
  - Access all debug routes (retrieval, summarizer, gap analysis internals)
  - User management (create/disable/promote users)
  - System configuration
  - Delete any resource regardless of ownership
- **Intended audience:** Platform operators, internal engineering team

#### `UserRole.RESEARCHER` (`"researcher"`)
- **Scope:** Owned resources only (scoped by `creator_id`)
- **Permissions:**
  - Create projects, sessions, reports, documents
  - Read/update/delete own resources
  - Run agent workflows on own projects
  - View evaluation results (read-only)
  - Cannot access debug routes
  - Cannot access admin/user management
  - Cannot modify system configuration
- **Default role** assigned to all newly registered users
- **Intended audience:** End users conducting research

#### `UserRole.VIEWER` (`"viewer"`)
- **Scope:** Read-only on resources shared with the user
- **Permissions:**
  - Read projects, sessions, reports, documents
  - View evaluation results
  - Cannot create, update, or delete any resource
  - Cannot run agent workflows
  - Cannot access debug routes
  - Cannot access admin/user management
- **Intended audience:** Stakeholders, reviewers, auditors

---

## 4. Remediation Actions

### 4.1 Already Completed — Evaluation Endpoints

**File:** `app/api/evaluation.py`

All endpoints now protected with `require_role(UserRole.ADMIN)`:

| Endpoint | Dependency | Rationale |
|----------|------------|-----------|
| `GET /evaluation/runs` | `require_role(UserRole.ADMIN)` | List all evaluation runs — exposes quality metrics across all users |
| `GET /evaluation/runs/{run_id}` | `require_role(UserRole.ADMIN)` | View single run — internal performance data |
| `GET /evaluation/benchmarks` | Public (no auth) | Reads benchmark definitions only — no user data exposed |
| `POST /evaluation/benchmark/run` | `require_role(UserRole.ADMIN)` | Compute-costly operation — prevent DoS |
| `GET /evaluation/scorecard/{execution_id}` | `require_role(UserRole.ADMIN)` | Scorecard contains per-run quality metrics |
| `POST /evaluation/evaluate` | `require_role(UserRole.ADMIN)` | Triggers full evaluation pipeline — expensive |
| `GET /evaluation/trends` | `require_role(UserRole.ADMIN)` | Aggregated quality trends across all runs |
| `GET /evaluation/distributions` | `require_role(UserRole.ADMIN)` | Metric distributions — internal analytics |

### 4.2 Already Completed — Debug Routes

**Files:**
- `app/api/retrieval_debug.py`
- `app/api/summarizer_debug.py`
- `app/api/gap_debug.py`

All debug endpoints now protected with `require_role(UserRole.ADMIN)`:

| Endpoint | File | Rationale |
|----------|------|-----------|
| `POST /retrieval/debug` | `retrieval_debug.py` | Exposes retrieval internals, prompts, raw context |
| `POST /summaries/debug` | `summarizer_debug.py` | Exposes summarizer pipeline, raw LLM output |
| `POST /gaps/debug` | `gap_debug.py` | Exposes gap analysis internals, coverage metrics |

### 4.3 Pending — Required Role Assignments

#### Category A: Admin-Only (require_role(ADMIN))

| Endpoint | Current Protection | Required |
|----------|-------------------|----------|
| `DELETE /projects/{id}` | `get_current_user` only | `require_role(ADMIN)` — only admins may delete projects |
| `DELETE /documents/{id}` | `get_current_user` only | `require_role(ADMIN)` — only admins may delete documents |
| `POST /agents/cancel/{id}` | No auth | `require_role(ADMIN)` — cancel any execution |
| All debug endpoints | ✅ DONE | Already remediated |
| All evaluation endpoints | ✅ DONE | Already remediated |

#### Category B: Researcher+ (require_role(ADMIN, RESEARCHER))

| Endpoint | Current Protection | Required |
|----------|-------------------|----------|
| `POST /projects` | `get_current_user` only | `require_role(ADMIN, RESEARCHER)` — create projects |
| `PUT /projects/{id}` | `get_current_user` only | `require_role(ADMIN, RESEARCHER)` — update own project |
| `POST /sessions` | `get_current_user` only | `require_role(ADMIN, RESEARCHER)` — create sessions |
| `POST /documents/upload` | `get_current_user` only | `require_role(ADMIN, RESEARCHER)` — upload documents |
| `POST /agents/run` | No auth | `require_role(ADMIN, RESEARCHER)` — run agent workflows |
| `POST /agents/cancel/{id}` | No auth | `require_role(ADMIN, RESEARCHER)` — cancel own execution |
| `POST /reports/generate` | No auth | `require_role(ADMIN, RESEARCHER)` — generate reports |
| `POST /reports/preview` | No auth | `require_role(ADMIN, RESEARCHER)` — preview reports |
| `POST /evaluation/evaluate` | ✅ DONE | Already remediated (ADMIN-only) |

#### Category C: Viewer+ (require_role(ADMIN, RESEARCHER, VIEWER))

| Endpoint | Current Protection | Required |
|----------|-------------------|----------|
| `GET /projects` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — scoped to user |
| `GET /projects/{id}` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` + ownership check |
| `GET /sessions` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — scoped to user |
| `GET /sessions/{id}` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` + ownership check |
| `GET /reports` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — scoped to user |
| `GET /documents` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — scoped to user |
| `POST /retrieval/search` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — search documents |
| `POST /retrieval/context` | `get_current_user` only | `require_role(ADMIN, RESEARCHER, VIEWER)` — retrieve context |
| `GET /agents/executions` | No auth | `require_role(ADMIN, RESEARCHER, VIEWER)` — scoped to user |
| `GET /agents/executions/{id}` | No auth | `require_role(ADMIN, RESEARCHER, VIEWER)` + ownership check |
| `GET /agents/registry` | No auth | `require_role(ADMIN, RESEARCHER, VIEWER)` — view agent catalog |
| `POST /reports/export` | No auth | `require_role(ADMIN, RESEARCHER, VIEWER)` — export reports |
| `GET /evaluation/runs` | ✅ DONE | Already remediated (ADMIN-only) |
| `GET /evaluation/runs/{id}` | ✅ DONE | Already remediated (ADMIN-only) |
| `GET /evaluation/scorecard/{id}` | ✅ DONE | Already remediated (ADMIN-only) |
| `GET /evaluation/trends` | ✅ DONE | Already remediated (ADMIN-only) |
| `GET /evaluation/distributions` | ✅ DONE | Already remediated (ADMIN-only) |

### 4.4 Endpoints Remaining Public (Intentionally)

| Endpoint | Rationale |
|----------|-----------|
| `POST /auth/register` | Account creation must be publicly accessible |
| `POST /auth/login` | Authentication entry point |
| `POST /auth/refresh` | Token refresh (token in body, not header) |
| `GET /health` | Health check for load balancers / orchestration |
| `GET /metrics` | Prometheus scrape endpoint (restrict to internal network in production) |
| `GET /evaluation/benchmarks` | Read-only benchmark definitions |

---

## 5. Enforcement Strategy

### 5.1 How RBAC Is Wired

The enforcement chain has three layers:

```
Request
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ Layer 1: Security Headers Middleware                 │
│   - CSP, HSTS, X-Frame-Options (no RBAC, infra)     │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ Layer 2: Rate Limiting Middleware                    │
│   - Redis-backed sliding window                      │
│   - Applied to auth, upload, agent run endpoints     │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ Layer 3: FastAPI Dependency Injection (RBAC)         │
│                                                       │
│  get_current_user (authn)                             │
│    ├── Extracts Bearer token                          │
│    ├── Decodes JWT, validates signature & expiry      │
│    ├── Checks token_version against settings          │
│    ├── Fetches User from database                     │
│    └── Returns User object (or raises 401)            │
│                                                       │
│  require_role(*roles) (authz)                         │
│    ├── Depends on get_current_user                     │
│    ├── Checks current_user.role in allowed roles       │
│    └── Returns User or raises 403                     │
└─────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ Layer 4: Resource Ownership Verification (IDOR)      │
│   - get_owned_project, get_owned_session, etc.        │
│   - Admin role bypasses ownership check               │
│   - Raises 403 if user does not own resource          │
└─────────────────────────────────────────────────────┘
  │
  ▼
  Handler
```

### 5.2 Dependency Injection Pattern

```python
# Pattern A: Admin-only endpoints
@router.get("/evaluation/runs")
async def list_evaluation_runs(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    ...

# Pattern B: Researcher+ endpoints
@router.post("/projects")
async def create_project(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER)),
):
    ...

# Pattern C: Viewer+ endpoints (with ownership scoping)
@router.get("/projects")
async def list_projects(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESEARCHER, UserRole.VIEWER)),
):
    if current_user.role == UserRole.ADMIN:
        projects = await get_all_projects(db)
    else:
        projects = await get_user_projects(db, current_user.id)
    ...
```

### 5.3 Ownership Check Pattern (IDOR Prevention)

```python
async def get_owned_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearchProject:
    result = await db.execute(
        select(ResearchProject).where(ResearchProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied")
    return project
```

### 5.4 Verification Checklist

Each endpoint must satisfy exactly one of:
- [ ] Uses `require_role(ADMIN)` — admin-only operation
- [ ] Uses `require_role(ADMIN, RESEARCHER)` — mutation by researchers
- [ ] Uses `require_role(ADMIN, RESEARCHER, VIEWER)` — read by any authenticated user
- [ ] Explicitly listed as public in `#Public Endpoints` section
- [ ] Includes ownership verification for resource-by-ID endpoints

---

## 6. Least-Privilege Assessment

### 6.1 Endpoint-to-Role Justification

| Endpoint Group | Assigned Role | Justification | Least-Privilege? |
|----------------|---------------|---------------|:-----------------:|
| `POST /evaluation/benchmark/run` | ADMIN | Runs compute-heavy E2E benchmark; could incur significant cost | ✅ Correct |
| `GET /evaluation/runs` | ADMIN | Lists all runs across users; cross-tenant data exposure | ✅ Correct |
| `GET /evaluation/runs/{id}` | ADMIN | Per-run quality metrics | ✅ Correct |
| `GET /evaluation/scorecard/{id}` | ADMIN | Scorecards contain benchmark comparisons | ✅ Correct |
| `POST /evaluation/evaluate` | ADMIN | Triggers full evaluation pipeline | ✅ Correct |
| `GET /evaluation/trends` | ADMIN | Aggregated analytics across all runs | ✅ Correct |
| `GET /evaluation/distributions` | ADMIN | Metric distribution statistics | ✅ Correct |
| `POST /retrieval/debug` | ADMIN | Exposes internal retrieval state, prompts, raw chunks | ✅ Correct |
| `POST /summaries/debug` | ADMIN | Exposes summarizer internals, scores, LLM output | ✅ Correct |
| `POST /gaps/debug` | ADMIN | Exposes gap analysis internals, coverage data | ✅ Correct |
| `GET /evaluation/benchmarks` | Public | Read-only benchmark definitions; no user data | ✅ Correct |

### 6.2 Potential Over-Provisioning Risks

| Endpoint | Current Assignment | Risk |
|----------|-------------------|------|
| `GET /evaluation/trends` | ADMIN only | Could be relaxed to `VIEWER+` if trends are non-sensitive aggregated data |
| `GET /evaluation/distributions` | ADMIN only | Same as above — metric distributions may be safe for broader access |

### 6.3 Principle of Minimum Functionality

The debug routes and evaluation runner endpoints are correctly gated to ADMIN only because:
1. **Debug routes** expose raw LLM prompts, intermediate state objects, and mock provider output — these should never reach non-engineering users
2. **Benchmark runs** are compute-intensive — unrestricted access would enable resource exhaustion attacks
3. **Evaluation trends/distributions** aggregate quality data across all projects — cross-tenant visibility is an ADMIN-only concern

---

## 7. Testing

### 7.1 Unit Tests for RBAC

```python
# File: tests/test_rbac.py

import pytest
from fastapi.testclient import TestClient
from app.models.user import User, UserRole
from app.main import app

client = TestClient(app)


def _make_token(user: User) -> str:
    """Helper: create a JWT for a given user."""
    from app.core.security import create_access_token
    return create_access_token(str(user.id), {"role": user.role.value})


class TestRBACEnforcement:
    """Verify that each endpoint rejects unauthorized roles."""

    # --- Admin-only endpoints ---

    @pytest.mark.parametrize("endpoint,method", [
        ("/evaluation/runs", "GET"),
        ("/evaluation/runs/test-run-id", "GET"),
        ("/evaluation/benchmark/run?benchmark_name=test&query=test", "POST"),
        ("/evaluation/scorecard/test-id", "GET"),
        ("/evaluation/evaluate", "POST"),
        ("/evaluation/trends", "GET"),
        ("/evaluation/distributions", "GET"),
        ("/retrieval/debug", "POST"),
        ("/summaries/debug", "POST"),
        ("/gaps/debug", "POST"),
    ])
    def test_admin_endpoints_reject_researcher(self, endpoint, method,
                                                researcher_user, researcher_token):
        """Researcher users receive 403 on admin-only endpoints."""
        response = client.request(method, endpoint,
                                  headers={"Authorization": f"Bearer {researcher_token}"})
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint,method", [
        ("/evaluation/runs", "GET"),
        ("/evaluation/runs/test-run-id", "GET"),
        ("/evaluation/benchmark/run?benchmark_name=test&query=test", "POST"),
        ("/evaluation/scorecard/test-id", "GET"),
        ("/evaluation/evaluate", "POST"),
        ("/evaluation/trends", "GET"),
        ("/evaluation/distributions", "GET"),
        ("/retrieval/debug", "POST"),
        ("/summaries/debug", "POST"),
        ("/gaps/debug", "POST"),
    ])
    def test_admin_endpoints_reject_viewer(self, endpoint, method,
                                            viewer_user, viewer_token):
        """Viewer users receive 403 on admin-only endpoints."""
        response = client.request(method, endpoint,
                                  headers={"Authorization": f"Bearer {viewer_token}"})
        assert response.status_code == 403

    @pytest.mark.parametrize("endpoint,method", [
        ("/evaluation/runs", "GET"),
        ("/evaluation/benchmark/run?benchmark_name=test&query=test", "POST"),
        ("/retrieval/debug", "POST"),
    ])
    def test_admin_endpoints_accept_admin(self, endpoint, method,
                                           admin_user, admin_token):
        """Admin users receive 200/4xx (non-404) on admin-only endpoints."""
        response = client.request(method, endpoint,
                                  headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code not in (401, 403)

    # --- Authentication gate ---

    @pytest.mark.parametrize("endpoint,method", [
        ("/evaluation/runs", "GET"),
        ("/retrieval/debug", "POST"),
        ("/summaries/debug", "POST"),
        ("/gaps/debug", "POST"),
    ])
    def test_endpoints_reject_unauthenticated(self, endpoint, method):
        """Endpoints without a token receive 401."""
        response = client.request(method, endpoint)
        assert response.status_code == 401
```

### 7.2 Integration Test Scenarios

| Scenario | Steps | Expected Result |
|----------|-------|----------------|
| Admin runs benchmark | `POST /evaluation/benchmark/run` with admin token | 200 + benchmark result |
| Researcher runs benchmark | Same with researcher token | **403 Forbidden** |
| Viewer lists evaluation runs | `GET /evaluation/runs` with viewer token | **403 Forbidden** |
| Unauthenticated debug | `POST /retrieval/debug` without token | **401 Unauthorized** |
| Researcher debug attempt | `POST /retrieval/debug` with researcher token | **403 Forbidden** |
| Token expiry | Expired JWT on any protected endpoint | **401 Unauthorized** |
| Wrong token type | Refresh token used as Bearer on protected endpoint | **401 Unauthorized** |
| Invalid signature | Tampered JWT on any protected endpoint | **401 Unauthorized** |

### 7.3 Automated Verification (CI)

Add a CI step that scans all router files for the absence of `require_role`:

```bash
# Check that every router (except auth, health) has role checks
grep -L "require_role" app/api/*.py \
  | grep -v "__init__" \
  | grep -v "auth\." \
  > /tmp/unprotected_routers.txt

if [ -s /tmp/unprotected_routers.txt ]; then
  echo "ERROR: These routers lack RBAC enforcement:"
  cat /tmp/unprotected_routers.txt
  exit 1
fi
```

### 7.4 Manual Verification Checklist

- [ ] Register a new user → confirm `role=researcher` in database
- [ ] Login as researcher → confirm JWT contains `"role":"researcher"`
- [ ] Access `GET /evaluation/runs` with researcher token → confirm `403`
- [ ] Access `POST /retrieval/debug` with researcher token → confirm `403`
- [ ] Access `POST /summaries/debug` with researcher token → confirm `403`
- [ ] Access `POST /gaps/debug` with researcher token → confirm `403`
- [ ] Promote user to admin → confirm new JWT contains `"role":"admin"`
- [ ] Access above endpoints with admin token → confirm `200`
- [ ] Revoke tokens (increment `token_version`) → confirm old tokens return `401`
- [ ] Access public endpoints (`/health`, `/auth/login`) without token → confirm `200`

---

## 8. Remediation Progress Tracker

| Area | Total Endpoints | Remediated | Remaining | Status |
|------|:---------------:|:----------:|:---------:|--------|
| Evaluation | 8 | 8 | 0 | ✅ Complete |
| Debug Routes | 3 | 3 | 0 | ✅ Complete |
| Projects CRUD | 5 | 0 | 5 | ❌ Not started |
| Sessions CRUD | 4 | 0 | 4 | ❌ Not started |
| Reports | 3 | 0 | 3 | ❌ Not started |
| Documents & Retrieval | 5 | 0 | 5 | ❌ Not started |
| Agents & Workflow | 5 | 0 | 5 | ❌ Not started |
| Report Generator | 3 | 0 | 3 | ❌ Not started |
| Auth (intentionally public) | 3 | N/A | N/A | ✅ Public by design |
| Health & Metrics (intentionally public) | 2 | N/A | N/A | ✅ Public by design |
| **Total Protected** | **38** | **11** | **25** | **29% complete** |

---

## 9. References

- RBAC Framework Implementation: `app/services/auth_service.py:86-94` (`require_role` function)
- User Role Model: `app/models/user.py:14-17` (`UserRole` enum)
- RBAC Audit Report: `RBAC_AUDIT.md`
- Security Middleware: `app/middleware/security_headers.py`
- Rate Limiting: `app/middleware/rate_limit.py`
- Token Security: `app/core/security.py`
