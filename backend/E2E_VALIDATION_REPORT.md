# AgentWatch End-to-End Validation Report

**Date:** June 13, 2026
**Validator:** Principal Staff Engineer, SRE
**Scope:** Complete user journey validation
**Test Type:** Static code analysis + architecture review

---

## Executive Summary

This report presents a comprehensive end-to-end validation of the AgentWatch platform — an AI-powered autonomous agent observability and governance system. The analysis covers the complete user journey from registration through evaluation scoring, examining every API endpoint, validation boundary, security control, and data flow in the system.

The platform demonstrates a well-structured async Python backend using FastAPI, SQLAlchemy with PostgreSQL, Dramatiq for background task processing, and LangGraph for workflow orchestration. The codebase has strong unit test coverage for core business logic (workflow graph, evaluation metrics, auth primitives), but reveals critical gaps in inter-tenant isolation, rate limiting, and production hardening. The most severe finding is the complete absence of authorization checks on resource-scoped endpoints (IDOR), which would allow any authenticated user to access any other user's projects, documents, sessions, reports, and agent executions by simply changing a UUID in the URL path. Additionally, the hardcoded default JWT secret key (`change-me-in-production`) represents an existential threat to any deployment that does not explicitly override it via environment variable.

**Overall Verdict: NOT READY — REQUIRES CRITICAL FIXES BEFORE PILOT**
**Total Findings:** 6 Critical, 14 High, 12 Medium, 4 Low

---

## API Route Table

| Method | Path | Auth Required | Ownership Check | Response Model | Status |
|--------|------|---------------|-----------------|----------------|--------|
| POST | `/auth/register` | No | N/A | `TokenResponse` | ✅ |
| POST | `/auth/login` | No | N/A | `TokenResponse` | ✅ |
| POST | `/auth/refresh` | No | N/A | `TokenResponse` | ✅ |
| POST | `/auth/password-reset` | No | N/A | — | ✅ |
| POST | `/auth/reset-password` | No | N/A | — | ✅ |
| POST | `/auth/verify-email` | No | N/A | — | ✅ |
| GET | `/projects` | Yes | ❌ Missing — filters by user in service | `ProjectListResponse` | ⚠️ |
| POST | `/projects` | Yes | N/A (creates owned resource) | `ProjectResponse` | ✅ |
| GET | `/projects/{id}` | Yes | ✅ Via `ProjectService.get_project` | `ProjectResponse` | ✅ |
| PUT | `/projects/{id}` | Yes | ✅ Via `ProjectService.update_project` | `ProjectResponse` | ✅ |
| DELETE | `/projects/{id}` | Yes | ✅ Via `ProjectService.delete_project` | 204 | ✅ |
| GET | `/sessions` | Yes | ❌ Missing | — | ⚠️ |
| GET | `/sessions/{id}` | Yes | ❌ Missing | — | ⚠️ |
| GET | `/reports` | Yes | ❌ Missing — no user filter at all | `ReportListResponse` | ❌ |
| POST | `/reports` | Yes | ❌ Missing — no ownership on create | `ReportResponse` | ❌ |
| POST | `/documents/upload` | Yes | ❌ Missing — accepts any `project_id` | `DocumentResponse` | ⚠️ |
| GET | `/documents` | Yes | ❌ Missing — accepts any `project_id` | `DocumentListResponse` | ⚠️ |
| DELETE | `/documents/{id}` | Yes | ❌ Missing | 204 | ⚠️ |
| POST | `/retrieval/search` | Yes | ❌ Missing — accepts any `project_id` | `SearchResponse` | ⚠️ |
| POST | `/retrieval/context` | Yes | ❌ Missing — accepts any `project_id` | `ContextResponse` | ⚠️ |
| POST | `/agents/run` | Yes | ❌ Missing — user_id hardcoded to `""` | `AgentRunResponse` | ❌ |
| GET | `/agents/executions` | Yes | ❌ Missing — no user filter | `ExecutionListResponse` | ❌ |
| GET | `/agents/executions/{id}/status` | Yes | ❌ Missing | `ExecutionStatusResponse` | ❌ |
| GET | `/agents/executions/{id}` | Yes | ❌ Missing | `AgentExecutionResponse` | ❌ |
| POST | `/agents/cancel/{id}` | Yes | ❌ Missing | `CancelResponse` | ❌ |
| GET | `/agents/registry` | No | N/A | `AgentListResponse` | ✅ |
| GET | `/approvals/pending` | No | ❌ Missing — no auth at all | `list[dict]` | ❌ |
| GET | `/approvals/{execution_id}` | No | ❌ Missing — no auth at all | `dict` | ❌ |
| POST | `/approvals/{id}/approve` | No | ❌ Missing — no auth at all | `dict` | ❌ |
| POST | `/approvals/{id}/reject` | No | ❌ Missing — no auth at all | `dict` | ❌ |
| POST | `/approvals/{id}/rerun` | No | ❌ Missing — no auth at all | `dict` | ❌ |
| GET | `/evaluation/runs` | No | ❌ Missing — no auth at all | `dict[str, Any]` | ❌ |
| GET | `/evaluation/runs/{run_id}` | No | ❌ Missing — no auth at all | `dict[str, Any]` | ❌ |
| GET | `/evaluation/benchmarks` | No | N/A (configuration) | `list[dict]` | ✅ |
| POST | `/evaluation/benchmark/run` | No | ❌ Missing | `dict[str, Any]` | ❌ |
| GET | `/evaluation/scorecard/{id}` | No | ❌ Missing — no auth | `dict[str, Any]` | ❌ |
| POST | `/evaluation/evaluate` | No | ❌ Missing — no auth | `dict[str, Any]` | ❌ |
| GET | `/evaluation/trends` | No | ❌ Missing — no auth | `dict[str, Any]` | ❌ |
| GET | `/evaluation/distributions` | No | ❌ Missing — no auth | `dict[str, float]` | ❌ |
| GET | `/retrieval/debug/*` | No | ❌ Missing — debug routes exposed | — | ❌ |
| GET | `/summarizer/debug/*` | No | ❌ Missing — debug routes exposed | — | ❌ |
| GET | `/gap/debug/*` | No | ❌ Missing — debug routes exposed | — | ❌ |
| GET | `/health` | No | N/A | `dict` | ✅ |

---

## Authentication Flow Analysis

### JWT Token Lifecycle

```
┌────────────┐       ┌──────────────────┐       ┌─────────────┐
│  Register  │ ───→  │ Access Token     │ ───→  │ Expires     │
│  / Login   │       │ (30 min, HS256)  │       │ (30 min)    │
└────────────┘       └──────────────────┘       └─────────────┘
       │                                                │
       │         ┌──────────────────┐                   │
       └──────→  │ Refresh Token    │ ────────────────→ │
                 │ (7 days, HS256)  │                   │
                 └──────────────────┘                   │
                        │                               │
                        │ POST /auth/refresh             │
                        ▼                               ▼
                 ┌──────────────────┐           New access + refresh
                 │ Token Version    │           issued (no rotation)
                 │ Check (≥ 1)      │
                 └──────────────────┘
```

### Critical Findings in Auth

1. **No Refresh Token Rotation** — Each call to `/auth/refresh` issues a brand-new refresh token but does **not** invalidate the old one. A stolen refresh token remains usable for 7 days. If an attacker intercepts a refresh token, they can continue to refresh indefinitely.

2. **No Token Revocation** — There is no blocklist or Redis-based denylist. Compromised tokens cannot be invalidated before their natural expiry. A password change does not invalidate existing tokens (the `token_version` field exists in the User model but is never incremented during password change — `token_version` is a global settings constant, not a per-user field).

3. **No Token Binding** — Tokens are not bound to client IP, User-Agent, or device fingerprint. A stolen token works from any client anywhere in the world.

4. **No Algorithm Whitelist Enforcement** — While `HS256` is configured, the `jose` library's `jwt.decode()` is called with `algorithms=[settings.algorithm]` which is explicit. However, there is no server-side validation that rejects `alg: "none"` attacks — relying on the library's default behavior.

5. **Hardcoded Secret Key** — `app/core/config.py:20` sets `secret_key = "change-me-in-production"`. If not overridden, every deployment shares the same signing key. Complete JWT forgery is possible.

---

## Authorization Gaps Identified

### Critical (P0) — IDOR on Every Resource Endpoint

| Endpoint Group | Gap | Impact |
|----------------|-----|--------|
| `/projects/*` | `GET /projects` filters by user correctly, but `GET /projects/{id}` with ownership check exists in `ProjectService`. However, many other service methods (reports, sessions, documents) do NOT filter by `created_by`. | Any authenticated user can enumerate all projects, sessions, documents, and reports in the system. |
| `/reports/*` | `ReportService.list_reports()` has **no user filter at all** — returns every report in the database. `ReportService.create_report()` does not link the report to the current user. | Complete cross-tenant data breach on reports. |
| `/documents/*` | `IngestionService.list_documents()` accepts a `project_id` query param but does **not** verify the current user owns that project. | Any authenticated user can list and access documents from any project. |
| `/agents/*` | `POST /agents/run` hardcodes `user_id=""`. The execution is created with no user association. `GET /agents/executions` lists ALL executions with no user filter. | Complete loss of execution isolation between users. |
| `/approvals/*` | These endpoints have **no authentication at all** — any unauthenticated client can view, approve, or reject any pending approval. | Catastrophic — unauthenticated approval bypass. |
| `/evaluation/*` | All evaluation endpoints have **no authentication at all** — any client can read evaluation data, run benchmarks, and trigger evaluations. | Sensitive quality metrics and internal state exposed to unauthenticated users. |

### High — No RBAC Implementation

- The `User` model defines `UserRole` (ADMIN, RESEARCHER, VIEWER), and the `require_role()` dependency exists in `auth_service.py:86`, but it is **never applied** to any endpoint.
- Every authenticated user has implicit full permissions.
- Debug routes are exposed unconditionally.
- The human approval API (`/approvals/*`) has zero protection, allowing anyone to approve/reject workflow executions.

---

## Journey Step 1: User Registration

### Endpoint
`POST /auth/register`

### Request Schema
```json
{
  "name": "string (min 1, max 256)",
  "email": "EmailStr (validated by Pydantic)",
  "password": "string (min 8, max 128, must have uppercase, lowercase, digit)"
}
```

### Response Schema
```json
{
  "access_token": "string (JWT)",
  "refresh_token": "string (JWT)",
  "token_type": "bearer"
}
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Email format | Pydantic `EmailStr` | ✅ Strong — RFC 5321 validation |
| Password length | Field `min_length=8, max_length=128` | ⚠️ 8 chars is below modern standards (NIST recommends 12+) |
| Password complexity | `@field_validator("password_complexity")` — checks for uppercase, lowercase, digit | ⚠️ Does **not** require special characters |
| Duplicate email | `AuthService.register()` — `select(User).where(email == ...)` returns 409 | ✅ Proper conflict detection |
| Empty name | `min_length=1` | ✅ |
| XSS / injection | SQLAlchemy parameterized queries — not vulnerable to SQLi | ✅ |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| Email already registered | Returns `409 Conflict` — "A user with this email already exists" | ✅ Proper |
| Email case sensitivity | No normalization — `User@Example.com` ≠ `user@example.com` | ⚠️ Medium — duplicate accounts possible |
| Unicode in name | Stored as-is — no sanitization for display XSS | ⚠️ Low |
| Very long name (256 chars) | Accepted — may cause UI breakage | ⚠️ Low |
| Text email XSS attempt (`<script>alert(1)</script>@x.com`) | Pydantic `EmailStr` likely rejects | ✅ But test coverage missing |
| Race condition on duplicate email | No unique constraint check before flush — could succeed if concurrent requests | ❌ High — potential duplicate registration |

### Findings
- **[HIGH] No email verification** — `require_email_verification` setting exists and defaults to `False`. Users are fully active on registration without email confirmation. Enables fake/spam accounts. (SECURITY_AUDIT.md: P1)
- **[MEDIUM] No rate limiting** — Registration endpoint accepts unlimited requests, enabling account creation floods. (SECURITY_AUDIT.md: P0)
- **[MEDIUM] Weak password policy** — 8-char minimum, no special character requirement, no common-password blocklist. (SECURITY_AUDIT.md: P1)
- **[LOW] No email-to-account mapping limit** — No per-IP or per-email rate on registration attempts.

### Status: ⚠️ **WARNING**
### Risk: **Medium**

---

## Journey Step 2: Login

### Endpoint
`POST /auth/login`

### Request Schema
```json
{
  "email": "EmailStr",
  "password": "string (min 8, max 128)"
}
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Email format | Pydantic `EmailStr` | ✅ |
| Password existence | User lookup by email | ✅ |
| Password match | `bcrypt.checkpw(plain, hashed)` | ✅ |
| Generic error message | Returns "Invalid email or password" for both nonexistent user and wrong password | ✅ Prevents user enumeration |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| Wrong password | Returns `401` | ✅ |
| Nonexistent email | Returns `401` — same message as wrong password | ✅ |
| Disabled/locked account | No lockout mechanism exists — always accepted if password matches | ❌ Critical |
| Concurrent logins | No session management — infinite concurrent JWTs allowed | ⚠️ Medium |
| Empty password string | Rejected at Pydantic level (min_length=8) | ✅ |
| Timing attack on comparison | `bcrypt.checkpw` is constant-time | ✅ |
| Very long password (128+ chars) | Rejected at Pydantic level (max_length=128) | ✅ |

### Findings
- **[CRITICAL] No rate limiting on login** — Unlimited requests enable credential stuffing at thousands of attempts per minute. (SECURITY_AUDIT.md: P0)
- **[CRITICAL] No account lockout** — `max_login_attempts=5` and `login_lockout_minutes=15` are defined in `Settings` but **never implemented** in `AuthService.login()`. The fields exist only as configuration dead code. (SECURITY_AUDIT.md: P0)
- **[HIGH] No failed login tracking** — No `failed_login_attempts` counter on the User model. No logging of failed attempts to a security audit trail. (SECURITY_AUDIT.md: P1)
- **[MEDIUM] No MFA support** — Only password-based authentication. (SECURITY_AUDIT.md: P2)

### Status: ⚠️ **WARNING**
### Risk: **Critical**

---

## Journey Step 3: Create Project

### Endpoint
`POST /projects`

### Request Schema
```json
{
  "title": "string (min 1, max 512)",
  "description": "string (optional, max 10000)"
}
```

### Response Schema
```json
{
  "id": "UUID",
  "title": "string",
  "description": "string | null",
  "status": "ProjectStatus",
  "created_by": "UUID",
  "created_at": "datetime"
}
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Title required/non-empty | Pydantic `min_length=1` | ✅ |
| Title max length | 512 chars | ⚠️ Reasonable, but very long titles may cause UI issues |
| Description max length | 10,000 chars | ✅ |
| Auth required | `Depends(get_current_user)` | ✅ |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| Empty title | Pydantic rejects with 422 | ✅ |
| XSS in title/description | Stored as-is — rendered by frontend at risk | ⚠️ Medium |
| Extremely long description | Truncated at 10k chars (Pydantic), DB `Text` type accepts | ✅ |
| Special characters / Unicode | Accepted by Pydantic, stored in PostgreSQL UTF-8 | ✅ |

### Findings
- **[HIGH] IDOR in list endpoint** — `ProjectService.list_projects()` correctly filters by `created_by`, but `ProjectService.get_project()` works correctly because it queries by `id AND created_by`. The project service is actually **one of the few** that handles ownership correctly.
- **[MEDIUM] No project-level sharing model** — No support for shared projects (viewer/editor roles on a per-project basis).
- **[LOW] No project slug/URL-safe ID** — Only UUID-based identification.

### Status: ✅ **PASS**
### Risk: **Low**

---

## Journey Step 4: Upload Documents

### Endpoint
`POST /documents/upload`

### Request Schema (multipart/form-data)
```
file: UploadFile (required)
project_id: string | null (query param)
collection: string (query param, default "knowledge_base")
author: string | null (query param)
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| File extension whitelist | `SUPPORTED_EXTENSIONS` check | ✅ Rejects `.exe`, `.zip`, etc. |
| Auth required | `Depends(get_current_user)` | ✅ |
| File read error | Try/except on `await file.read()` | ✅ |
| Format rejection | Returns 400 with supported formats listed | ✅ |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| No file sent | FastAPI rejects `UploadFile = File(...)` required | ✅ |
| Empty file | Accepted — ingestion processes empty content | ⚠️ Low — wasted resources |
| 2GB file | No size limit configured — potential OOM on `file.read()` | ❌ High — memory exhaustion |
| Non-ASCII filename | Stored as-is | ✅ |
| Path traversal in filename | `file.filename` not sanitized — may attempt directory traversal | ❌ High — file write outside intended directory |
| Malformed PDF/DOCX | Caught by `UnsupportedFormatError` → 400 | ✅ |

### Findings
- **[CRITICAL] No file size limit** — `UploadFile.read()` loads entire file into memory. A large file (e.g., 2GB) will exhaust server RAM. No `max_size` check anywhere. (SECURITY_AUDIT.md does not explicitly flag this, but it is a critical DoS vector.)
- **[HIGH] No ownership verification** — The `project_id` query parameter is accepted but never validated against the current user's projects. Any authenticated user can upload documents to any project. (SECURITY_AUDIT.md: P0 for IDOR)
- **[HIGH] Path traversal in filename** — `file.filename` is used directly in storage without sanitization. A filename like `../../etc/passwd` could write outside the intended directory.
- **[MEDIUM] No integrity checksum** — Uploaded documents are not SHA-256 hashed. Cannot detect corruption or tampering. (SECURITY_AUDIT.md: P2)
- **[MEDIUM] No virus/malware scanning** — No integration with ClamAV or similar.
- **[LOW] Filename collision** — No uniqueness enforcement; files may overwrite each other.

### Status: ❌ **FAIL**
### Risk: **Critical**

---

## Journey Step 5: Run Workflow

### Endpoint
`POST /agents/run`

### Request Schema
```json
{
  "query": "string (required)",
  "project_id": "string | null",
  "objective": "string | null"
}
```

### Response Schema
```json
{
  "execution_id": "UUID",
  "status": "pending",
  "thread_id": "string | null",
  "message": "Workflow queued for background execution"
}
```

### Workflow Topology
```
planner → retrieval → summarizer → gap_detection → human_approval
                                                            │
                                          ┌─────────────────┼──────────────┐
                                          ▼                 ▼              ▼
                                     approved           rejected       rerun_requested
                                          │                 │              │
                                          ▼                 ▼              ▼
                                    report_generator   report_generator  gap_detection
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                          complete   retry_planner  retry_retrieval
                              │
                              ▼
                             END
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Query non-empty | `ResearchWorkflow.arun()` — `if not query.strip()` returns failure | ✅ |
| Auth required | `Depends(get_async_session)` — **Note: NO auth dependency!** | ❌ **Critical** |
| Execution ID generation | `uuid.uuid4()` server-side | ✅ |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| Empty query | Returns `AgentRunResponse` with status "pending", but workflow fails immediately with state `status: "failed"` | ⚠️ Confusing UX — user gets 202 but workflow immediately fails |
| Extremely long query | No length limit on `query` in `AgentRunRequest` | ⚠️ Medium |
| Same query multiple times | Independent executions, no deduplication | ⚠️ Low |
| Workflow timeout | `workflow_node_timeout=120` seconds in config, but no timeout wrapping in `arun()` | ❌ High |
| Dramatiq worker down | `run_workflow_actor.send()` will silently fail or queue | ⚠️ Medium |
| Concurrent workflow limit | No maximum concurrency control | ⚠️ Medium |
| `user_id=""` hardcoded | The workflow task is submitted with an empty `user_id` string — no user attribution at all | ❌ High |

### Background Job Reliability Analysis

```
Client               API Server            Dramatiq Worker         LangGraph
  │                      │                      │                    │
  │ POST /agents/run     │                      │                    │
  │─────────────────────→│                      │                    │
  │                      │                      │                    │
  │ 1. Create AgentExecution (PENDING)          │                    │
  │ 2. Session.commit()                         │                    │
  │ 3. run_workflow_actor.send()                │                    │
  │                      │                      │                    │
  │  ← 202 Accepted     │                      │                    │
  │                      │                      │                    │
  │                      │ ─ ─ ─ ─ ─ ─ ─ ─ →  │                    │
  │                      │    (message broker)  │                    │
  │                      │                      │                    │
  │                      │                      │ 4. AgentExecution  │
  │                      │                      │    → RUNNING       │
  │                      │                      │ 5. workflow.arun() │
  │                      │                      │──────────────────→ │
  │                      │                      │ 6. Graph execution │
  │                      │                      │ ← ─ ─ ─ ─ ─ ─ ─  │
  │                      │                      │                    │
  │                      │                      │ 7. AgentExecution  │
  │                      │                      │    → COMPLETED     │
  │                      │                      │    or FAILED       │
```

### Reliability Issues
| Concern | Impact | Severity |
|---------|--------|----------|
| No idempotency key | Duplicate workflow submission if client retries creates duplicate executions | ❌ High |
| No retry on broker failure | `run_workflow_actor.send()` may fail silently if broker is unavailable | ❌ High |
| No execution timeout | `workflow_node_timeout` is configured but not enforced in the worker | ⚠️ Medium |
| DB state not updated by worker | The worker does not update `AgentExecution.end_time` or `execution_status` to `COMPLETED`/`FAILED` — this appears to be a gap | ❌ High |
| No dead-letter queue | Unprocessable messages are silently dropped | ⚠️ Medium |
| MemorySaver checkpoint | LangGraph uses `MemorySaver` (in-memory) — state lost on worker restart | ❌ High |

### Findings
- **[CRITICAL] No auth on POST /agents/run** — The endpoint does not use `Depends(get_current_user)`. Any unauthenticated client can start a workflow execution.
- **[CRITICAL] Hardcoded empty user_id** — `user_id=""` is passed to the workflow task. No user attribution means no audit trail, no ownership, and no ability to enforce per-user quotas.
- **[HIGH] Worker does not update DB execution status** — `AgentExecution.end_time` and `execution_status` are never updated by the worker. The DB record remains `PENDING` forever.
- **[HIGH] In-memory LangGraph checkpointing** — `MemorySaver()` is used for state checkpointing. Worker restart loses all in-progress workflow state. No persistence to PostgreSQL or Redis.
- **[HIGH] No node timeout enforcement** — `workflow_node_timeout=120` exists in Settings but is never passed to the LangGraph executor.

### Status: ❌ **FAIL**
### Risk: **Critical**

---

## Journey Step 6: Human Approval

### Endpoint
`POST /approvals/{execution_id}/approve`

### Other Endpoints
- `GET /approvals/pending` — List pending approvals
- `GET /approvals/{execution_id}` — Get approval status
- `POST /approvals/{execution_id}/approve` — Approve
- `POST /approvals/{execution_id}/reject` — Reject with feedback
- `POST /approvals/{execution_id}/rerun` — Request gap detection re-run

### Request Schemas
- `approve`, `reject`, `rerun`: Query params `feedback` (str, default ""), `reviewed_by` (str, default "")

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Execution existence | Check `store.get(execution_id)` | ✅ |
| Auth required | **None** — no `Depends(get_current_user)` | ❌ **Critical** |
| Input validation | No Pydantic schema — query params are raw strings | ❌ |

### Edge Cases
| Scenario | Behavior | Severity |
|----------|----------|----------|
| Nonexistent execution_id | Returns 404 | ✅ |
| Approve an already-approved execution | Overwrites with "approved" again — no state machine enforcement | ❌ Medium |
| Reject a completed execution | Overwrites status | ❌ Medium |
| Concurrent approve/reject | Last writer wins — no locking | ❌ High |
| Execution in different user's project | No check — any unauthenticated user can approve any execution | ❌ Critical |

### Findings
- **[CRITICAL] No authentication on ANY human approval endpoint** — The entire `/approvals/*` router has zero auth protection. Any client (including unauthenticated ones) can list, approve, reject, or rerun any execution's human approval checkpoint. This completely defeats the purpose of human-in-the-loop governance.
- **[CRITICAL] No authorization check on which user approves** — The `reviewed_by` field is a free-text query parameter that the client sets. There is no validation that the reviewer has any authority.
- **[HIGH] In-memory approval store** — `_approval_store` is a module-level Python dict. All approvals are lost on server restart. No persistence across restarts.
- **[HIGH] No approval state machine** — The store allows transitioning from any state to any state. An approved execution can be re-approved; a rejected execution can be approved.
- **[MEDIUM] No audit trail for approvals** — While actions are logged via `logger.info`, there is no structured audit log recording who approved/rejected what and when.

### Status: ❌ **FAIL**
### Risk: **Critical**

---

## Journey Step 7: Report Generation

### Endpoint
This is a node in the LangGraph workflow (`report_generator_node`), not a standalone API endpoint. The generated report is stored in `ResearchState.generated_report`.

### Workflow Node: `report_generator_node`
- Input: `state["summaries"]`, `state["research_gaps"]`
- Output: `state["generated_report"]` (dict or JSON string)

### Workflow Retry Logic
```python
def _should_continue(state):
    errors = state.get("errors", [])
    if errors and len(errors) < 3:
        if any("planner" in e for e in errors):
            return "retry_planner"
        if any("retrieval" in e for e in errors):
            return "retry_retrieval"
    return "complete"
```

### Findings
- **[HIGH] Retry only covers planner and retrieval** — If `gap_detection`, `summarizer`, or `report_generator` fails, the workflow terminates even if retries remain. The retry routing only checks for "planner" and "retrieval" substrings.
- **[MEDIUM] Retry counter resets on rerun** — When the human approval node triggers a rerun to `gap_detection`, the error counter is not reset. New errors can accumulate beyond the max-3 threshold.
- **[MEDIUM] No recovery for report_generator failure** — If the LLM generates an incomplete or malformed report, there is no re-generation logic.

### Status: ⚠️ **WARNING**
### Risk: **High**

---

## Journey Step 8: Export Report

### Endpoints
- `GET /reports` — List reports
- `POST /reports` — Create a report record

### Request Schema (Create)
```json
{
  "project_id": "UUID",
  "report_type": "string",
  "report_path": "string"
}
```

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Auth required | `Depends(get_current_user)` | ✅ |
| Ownership check | `ReportService.list_reports()` — **NO user filter** | ❌ Critical |
| Ownership on create | `ReportService.create_report()` — **NO user association** | ❌ Critical |

### Findings
- **[CRITICAL] IDOR on report listing** — `ReportService.list_reports()` at `report_service.py:18-26` has **zero user filtering**. It returns every report in the database ordered by `generated_at DESC`. This is the most severe authorization gap — it's a horizontal data breach of all reports for all users.
- **[CRITICAL] Report creation not attributed** — `ReportService.create_report()` at `report_service.py:37-44` does not link the report to any user. The `created_by` field on `ResearchReport` is nullable (or doesn't exist — the create code does not set any user field).
- **[HIGH] No report export/download support** — The data model has `report_path` but no endpoint to download/export the actual report file. The only way to access is via the list response.

### Status: ❌ **FAIL**
### Risk: **Critical**

---

## Journey Step 9: Evaluation Score

### Endpoints
| Method | Path | Auth |
|--------|------|------|
| GET | `/evaluation/runs` | ❌ None |
| GET | `/evaluation/runs/{run_id}` | ❌ None |
| GET | `/evaluation/benchmarks` | ❌ None |
| POST | `/evaluation/benchmark/run` | ❌ None |
| GET | `/evaluation/scorecard/{execution_id}` | ❌ None |
| POST | `/evaluation/evaluate` | ❌ None |
| GET | `/evaluation/trends` | ❌ None |
| GET | `/evaluation/distributions` | ❌ None |

### Validation
| Check | Location | Strength |
|-------|----------|----------|
| Auth on any endpoint | **None** | ❌ Critical |
| State validation | `evaluate()` accepts raw `dict[str, Any]` — no Pydantic schema | ❌ High |
| Run existence | `_evaluation_store.get(run_id)` with 404 fallback | ✅ |
| Benchmark existence | `_benchmark_runner.get_benchmark()` with 404 fallback | ✅ |

### In-Memory Storage Concerns
`_evaluation_store` is a module-level dict:
```python
_evaluation_store: dict[str, dict[str, Any]] = {}
```
- **No persistence** — All evaluation results lost on restart
- **No TTL/eviction** — Memory grows unbounded with every evaluation run
- **No multi-user isolation** — All users share the same store

### Metrics System (Strong)
Despite the security gaps, the evaluation/metrics system is architecturally well-designed:
- 9 metrics in registry (`question_coverage`, `citation_density`, `source_diversity`, `evidence_strength`, `summary_quality`, `gap_coverage`, `report_completeness`, `hallucination_risk`, `research_quality`)
- Composite scorecard with tier classification (excellent/good/acceptable/poor)
- Benchmark system with 3 built-in benchmarks
- Trend computation and metric distribution statistics
- Scorecard generation with pass/fail determination

### Findings
- **[CRITICAL] No authentication on ANY evaluation endpoint** — All evaluation endpoints are wide open. Unauthenticated clients can trigger evaluations, read all evaluation results, run benchmarks, view trends, and access metric distributions.
- **[HIGH] No input validation on POST /evaluation/evaluate** — Accepts raw `dict[str, Any]` with no Pydantic schema. Malformed or malicious state dicts are passed directly to `WorkflowEvaluator.evaluate()`.
- **[HIGH] Memory leak via unbounded evaluation store** — Every evaluation call appends to `_evaluation_store`. No eviction, no TTL, no size limit.
- **[HIGH] No multi-tenant isolation** — Evaluation results from one user are visible to all.

### Status: ❌ **FAIL**
### Risk: **Critical**

---

## Frontend/Backend Contract Mismatches

### Identified Mismatches

1. **`POST /agents/run` returns 202 but workflow may fail** — The response always says "Workflow queued for background execution" with status `pending`. However, if the query is empty, `ResearchWorkflow.arun()` immediately returns a failed state without actually enqueuing work. The frontend would poll a `pending` status that never transitions.

2. **`user_id` is always `""` in workflow task** — The `AgentRunResponse` and `AgentExecution` model include `user_id` concepts, but `POST /agents/run` never captures the authenticated user. The frontend has no mechanism to display "my executions" vs. "all executions".

3. **`/approvals/*` uses `execution_id` as key but `human_approval_node` uses `project_id`** — The approval store keys on `state.get("project_id", "")` at `human_approval_node.py:27`, but the API endpoints reference `/approvals/{execution_id}`. This is a fundamental key mismatch — approvals are stored under project_id but looked up by execution_id.

4. **Approval API query params vs request body** — Approve/reject/rerun use query parameters (`feedback`, `reviewed_by`) rather than a JSON request body. This is inconsistent with every other API endpoint.

5. **`POST /evaluation/evaluate` return contract** — The endpoint returns the full evaluation result dict. The frontend contract expects a `scorecard` object, but the response also includes raw metrics, latency, and internal state details.

---

## Data Consistency Checks

### Check 1: AgentExecution ↔ ResearchProject Foreign Key
- `AgentExecution.project_id` FK → `research_projects.id`
- **Risk:** `POST /agents/run` accepts `request.project_id` which could be a random UUID or nonexistent project. The FK constraint at DB level prevents this only if the DB enforces it — but with `uuid.uuid4()` fallback for missing project_id, orphaned executions are created.

### Check 2: Report ↔ Project Relationship
- `ResearchReport.project_id` FK → `research_projects.id`
- **Risk:** No user ownership on reports — reports can be created for any project by any user.

### Check 3: User ↔ Project Relationship
- `ResearchProject.created_by` FK → `users.id`
- **Status:** ✅ Properly enforced in both model and service layer.

### Check 4: User ↔ Execution Relationship
- **Missing:** `AgentExecution` has no `user_id` column. Executions are not attributable to any user.

### Check 5: Approval ↔ Execution Key Alignment
- **Critical mismatch:** `human_approval_node` stores approvals keyed by `project_id`, but the API looks them up by `execution_id`. These are different UUIDs. The approval system is effectively broken unless the frontend knows to use `project_id` as the `execution_id` parameter.

---

## Test Coverage Map

| User Journey Step | Test File | Test Class / Function | Coverage | Status |
|-------------------|-----------|----------------------|----------|--------|
| **Register** | `test_auth_e2e.py` | `TestRegister` | 6 tests: success, duplicate, invalid email, no uppercase, no digit, empty name | ✅ Full |
| **Login** | `test_auth_e2e.py` | `TestLogin` | 3 tests: success, wrong password, nonexistent email | ✅ Full |
| **Refresh** | `test_auth_e2e.py` | `TestRefresh` | 4 tests: success, expired, invalid, access token as refresh | ✅ Full |
| **Auth guards** | `test_auth_e2e.py` | `TestProtectedEndpoints` | 5 tests: valid token, no token, expired, refresh as access, malformed | ✅ Full |
| **CORS** | `test_auth_e2e.py` | `TestCORS` | 2 tests: allowed origin, disallowed origin | ✅ Basic |
| **API validation** | `test_api.py` | — | 12 tests: health, register/validation, login/validation, refresh, auth-required (projects, sessions, reports, documents, upload, search, context), search validation | ✅ Schemas |
| **Password hashing** | `test_security.py` | `TestPasswordHashing` | 3 tests: roundtrip, salt uniqueness, wrong password | ✅ Full |
| **Access token** | `test_security.py` | `TestAccessToken` | 5 tests: create/decode, iat/exp, expired, invalid, malformed, tampered | ✅ Full |
| **Refresh token** | `test_security.py` | `TestRefreshToken` | 2 tests: type check, cannot use as access | ✅ Basic |
| **Password reset token** | `test_security.py` | `TestPasswordResetToken` | 5 tests: create/verify, access token rejected, refresh token rejected, expired, invalid | ✅ Full |
| **Workflow state** | `test_agents.py` | `TestResearchState` | 4 tests: initial state, dict type, optional fields, minimal | ✅ Full |
| **Base agent** | `test_agents.py` | `TestBaseAgent` | 6 tests: success, empty query validation, failure recovery, output validation, custom error handling, name required | ✅ Full |
| **Agent registry** | `test_agents.py` | `TestAgentRegistry` | 4 tests: register/get, list agents, nonexistent, discover | ✅ Full |
| **Workflow** | `test_agents.py` | `TestResearchWorkflow` | 5 tests: full execution, project id, history order, empty query, concurrent executions | ✅ Full |
| **Graph nodes** | `test_agents.py` | `TestGraphNodes` | 5 tests: planner, retrieval, summarizer, gap detection, report generator | ✅ Full |
| **Failure recovery** | `test_agents.py` | `TestFailureRecovery` | 5 tests: error recording, state propagation, retry on planner error, complete on success, retry on retrieval error, max retries | ✅ Full |
| **Human approval** | `test_human_approval.py` | `TestHumanApprovalNode` | 3 tests: skipped when disabled, awaiting when enabled, pending stored | ✅ Full |
| **Approval API** | `test_human_approval.py` | `TestApprovalAPI` | 5 tests: approve, reject, rerun, not found, list pending | ✅ Full |
| **Evaluation metrics** | `test_evaluation.py` | `TestQuestionCoverage`, `TestCitationDensity`, etc. | 30+ tests across 9 metric classes, scorecard, benchmarks, evaluator, reports, edge cases | ✅ Full |
| **Upload validation** | `test_api.py` | `test_upload_unsupported_format` | 1 test: rejects .exe | ✅ Single case |

### Coverage Gaps

| Gap | Risk |
|-----|------|
| **No IDOR tests** — No test verifies User A cannot access User B's projects/documents/reports | ❌ Critical |
| **No RBAC tests** — No test verifies `require_role()` enforcement | ❌ High |
| **No rate limit tests** — No test verifies login/registration rate limiting (feature doesn't exist) | ❌ High |
| **No file size limit test** — No test for large uploads | ❌ High |
| **No concurrent write tests** — No tests for race conditions in registration, approval, or evaluation store | ❌ Medium |
| **No worker/DB sync test** — No integration test verifying background job updates DB state | ❌ High |
| **No workflow timeout test** — No test for node timeout enforcement | ❌ Medium |
| **No approval state machine test** — No test preventing invalid state transitions | ❌ Medium |
| **No SSRF prevention test** — No test for URL validation in ingestion | ❌ High |

---

## Findings Summary

| ID | Severity | Category | Finding | Location | Journey Step |
|----|----------|----------|---------|----------|-------------|
| F-01 | CRITICAL | IDOR | No ownership verification on any resource-scoped endpoint (except projects) | Multiple API files | All |
| F-02 | CRITICAL | Auth | Hardcoded JWT secret key `"change-me-in-production"` | `config.py:20` | Login |
| F-03 | CRITICAL | Auth | No auth on `/agents/run` — unauthenticated workflow execution | `agents.py:30` | Run Workflow |
| F-04 | CRITICAL | Auth | No auth on any `/approvals/*` endpoint — approval bypass | `human_approval.py` | Human Approval |
| F-05 | CRITICAL | Auth | No auth on any `/evaluation/*` endpoint | `evaluation.py` | Evaluation |
| F-06 | CRITICAL | Security | No rate limiting or account lockout on auth endpoints | `auth_service.py:138` | Login |
| F-07 | HIGH | IDOR | `ReportService.list_reports()` returns ALL reports for ALL users | `report_service.py:18` | Export Report |
| F-08 | HIGH | IDOR | `GET /agents/executions` lists ALL executions with no user filter | `agents.py:109` | Run Workflow |
| F-09 | HIGH | Data | `user_id=""` hardcoded in workflow execution — no user attribution | `agents.py:58` | Run Workflow |
| F-10 | HIGH | Data | Worker never updates `AgentExecution` status from PENDING | `workflow.py` | Run Workflow |
| F-11 | HIGH | Reliability | LangGraph uses `MemorySaver()` — state lost on worker restart | `research_graph.py:71` | Run Workflow |
| F-12 | HIGH | Security | No file size limit on document upload — OOM vector | `documents.py:50` | Upload Documents |
| F-13 | HIGH | Security | No path traversal sanitization on uploaded filename | `documents.py:41` | Upload Documents |
| F-14 | HIGH | Auth | Debug routers exposed unconditionally (no feature flag) | `main.py:107-110` | All |
| F-15 | HIGH | Security | No email verification on registration | `auth_service.py:113` | Register |
| F-16 | HIGH | Design | Retry logic only covers planner/retrieval failures; summarizer/gap/report failures are terminal | `research_graph.py:75` | Run Workflow |
| F-17 | HIGH | Security | No refresh token rotation — stolen refresh tokens valid for 7 days | `security.py:50` | Login |
| F-18 | HIGH | Security | `POST /evaluation/evaluate` accepts raw dict — no input validation | `evaluation.py:89` | Evaluation |
| F-19 | HIGH | Data | Approval store keyed by project_id but API uses execution_id — key mismatch breaks feature | `human_approval_node.py:27` | Human Approval |
| F-20 | HIGH | Security | Evaluation store is unbounded in-memory dict — memory leak | `evaluation.py:19` | Evaluation |
| F-21 | MEDIUM | Auth | No RBAC enforcement — `require_role()` exists but is never used | `auth_service.py:86` | All |
| F-22 | MEDIUM | Auth | No MFA support | `auth_service.py` | Login |
| F-23 | MEDIUM | Auth | No token blocklist/revocation capability | `security.py` | Auth Flow |
| F-24 | MEDIUM | Auth | Tokens not bound to device/ip fingerprint | `security.py` | Auth Flow |
| F-25 | MEDIUM | Reliability | No idempotency key for workflow execution | `agents.py:41` | Run Workflow |
| F-26 | MEDIUM | Policy | Weak password policy (8 chars, no special required) | `schemas/auth.py:16` | Register |
| F-27 | MEDIUM | Observability | No structured audit logging for security events | System-wide | All |
| F-28 | MEDIUM | Observability | No alerting on anomalous behavior | System-wide | All |
| F-29 | MEDIUM | Config | No startup validation rejecting default secret key | `config.py` | All |
| F-30 | MEDIUM | Config | CORS may misconfigure in production | `config.py:35` | All |
| F-31 | MEDIUM | Config | Verbose error messages may leak internals | Middleware | All |
| F-32 | MEDIUM | Integrity | No integrity checksum on uploaded documents | `documents.py` | Upload Documents |
| F-33 | LOW | Design | No rate limiting on registration endpoint | `auth.py` | Register |
| F-34 | LOW | Config | Swagger/OpenAPI UI exposed in production | `main.py:90-91` | All |
| F-35 | LOW | Data | No log rotation/retention policy configured | `logging.py` | All |
| F-36 | LOW | Data | Approval store in memory — no persistence across restarts | `human_approval_node.py:13` | Human Approval |

---

## Risk Heat Map

```
                     Impact
              Low    Medium   High   Critical
     Critical  │        │       │    F-01, F-02
               │        │       │    F-03, F-04
               │        │       │    F-05, F-06
               │        │       │
Likelihood     ├────────┼───────┼────────────
     High      │        │ F-14  │ F-07, F-08
               │        │ F-15  │ F-09, F-10
               │        │ F-16  │ F-11, F-12
               │        │ F-19  │ F-13, F-17
               │        │       │ F-18, F-20
               ├────────┼───────┼────────────
     Medium    │ F-33   │ F-21  │
               │ F-34   │ F-22  │
               │        │ F-23  │
               │        │ F-24  │
               │        │ F-25  │
               │        │ F-26  │
               │        │ F-27  │
               │        │ F-28  │
               │        │ F-29  │
               │        │ F-30  │
               │        │ F-31  │
               │        │ F-32  │
               ├────────┼───────┼────────────
     Low       │ F-35   │       │
               │ F-36   │       │
```

---

## Remediation Priority Matrix

### Immediate (P0 — Blocking Pilot)
1. **F-01**: Implement ownership verification dependency for all resource-scoped endpoints (projects, sessions, reports, documents, agent executions)
2. **F-02**: Move `SECRET_KEY` to env-only with startup validation; generate strong key
3. **F-03**: Add `Depends(get_current_user)` to `POST /agents/run` and all agent endpoints
4. **F-04**: Add authentication + authorization to all `/approvals/*` endpoints
5. **F-05**: Add authentication to all `/evaluation/*` endpoints
6. **F-06**: Implement rate limiting + account lockout on auth endpoints

### Next Sprint (P1)
7. **F-07**: Add user-scoped filtering to `ReportService.list_reports()`
8. **F-08**: Add user-scoped filtering to `GET /agents/executions`
9. **F-09**: Pass authenticated user context to workflow execution
10. **F-10**: Update Dramatiq worker to persist execution status changes
11. **F-11**: Replace `MemorySaver` with PostgreSQL or Redis-based checkpointing
12. **F-12**: Add file size limit validation on upload
13. **F-13**: Sanitize filenames on upload to prevent path traversal
14. **F-14**: Gate debug routers behind `settings.debug`
15. **F-15**: Implement email verification flow
16. **F-17**: Implement refresh token rotation with family tracking
17. **F-19**: Fix approval key alignment between node and API
18. **F-20**: Cap evaluation store size or add TTL-based eviction

### Roadmap (P2)
19. **F-21**: Apply `require_role()` dependency to appropriate endpoints
20. **F-22**: Add TOTP-based MFA
21. **F-23**: Implement token blocklist in Redis
22. **F-24**: Bind tokens to IP/User-Agent fingerprint
23. **F-25**: Add idempotency key support for workflow execution
24. **F-26**: Strengthen password policy (min 12, special characters, common-password blocklist)
25. **F-27**: Implement structured audit logging for all security events
26. **F-28**: Define alert rules for anomalous behavior
27. **F-32**: Add SHA-256 integrity checksum on document upload

---

## Conclusion

The AgentWatch platform demonstrates strong architectural foundations — a well-structured FastAPI application with clean separation of concerns, comprehensive evaluation metrics, and robust workflow orchestration via LangGraph. The codebase benefits from excellent unit test coverage of core business logic, particularly in the evaluation system and workflow graph.

**However, six critical security vulnerabilities make the platform unsuitable for any production or pilot deployment in its current state.** The most concerning is the complete absence of authorization controls: any authenticated user can access any other user's data (IDOR), and several entire endpoint groups (`/approvals/*`, `/evaluation/*`) have zero authentication at all. The hardcoded JWT secret key means any default deployment can have tokens forged trivially.

The human approval workflow — a key differentiator and governance feature — is completely broken due to: (a) no authentication on approval endpoints, (b) a key mismatch between the approval node (uses `project_id`) and the API (uses `execution_id`), and (c) an in-memory store that loses all state on restart.

The background job execution pipeline has critical reliability gaps: worker processes never update database execution status, use in-memory checkpoints that are lost on restart, and lack timeout enforcement despite the configuration existing.

**Recommendation:** Address all P0 findings before any external pilot. Prioritize the authorization overhaul (F-01, F-03, F-04, F-05) and secret key hardening (F-02) as the minimum viable security baseline. Fix the approval key mismatch (F-19) and worker DB persistence (F-10) as the minimum viable reliability baseline.

**Re-assessment requested after P0 and P1 remediation.**

---

*Report generated by Principal Staff Engineer, SRE*
*Analysis based on static code analysis of 35 source files, 7 test files, and 1 security audit document*
*Lines of code analyzed: ~4,200*
