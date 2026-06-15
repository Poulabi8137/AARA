# Backend Audit Report

**Date:** 2026-06-15
**Scope:** Full FastAPI backend codebase analysis, startup crash resolution, test validation
**Auditor:** Automated analysis tool

---

## 1. Root Cause of Startup Crash

### `AssertionError: Status code 204 must not have a response body`

**Location:** `app/api/projects.py:75`

```python
@router.delete("/{project_id}", status_code=204)
async def delete_project(...) -> None:
    ...
```

**Root Cause:** FastAPI wraps `None` returns in a `JSONResponse(content=None)` which produces body `"null"`. Starlette's `Response.__init__` asserts that a 204 response must have no body, causing `AssertionError`.

**Same issue at:** `app/api/documents.py:91` (`delete_document` route)

---

## 2. Files Modified

| File | Change | Severity |
|------|--------|----------|
| `app/api/projects.py` | Added `Response` import, `response_class=Response` to `@router.delete`, explicit `return Response(status_code=204)` | Critical |
| `app/api/documents.py` | Added `Response` import, `response_class=Response` to `@router.delete`, explicit `return Response(status_code=204)` | Critical |
| `app/db/session.py` | Added `get_async_session()` function (referenced by `agents.py` but not defined) | Critical |
| `app/middleware/rate_limit.py` | Changed `self._app.state` → `self.app.state` → `request.app.state` (middleware chain wraps other middleware, not FastAPI app) | Critical |
| `app/agents/registry.py` | Changed `extra={"name": ...}` → `extra={"agent_name": ...}` because `name` is a reserved `LogRecord` key | Critical |
| `app/agents/registry.py` | Changed `extra={"module": ...}` → `extra={"agent_module": ...}` because `module` is a reserved `LogRecord` key | Critical |
| `app/core/secrets.py` | Changed `extra={"name": ...}` → `extra={"secret_name": ...}` (2 occurrences) | High |
| `app/schemas/auth.py` | Added `Field(..., min_length=1)` to `RefreshRequest.refresh_token` (test expects 422 for empty string) | Medium |
| `tests/test_api.py` | Fixed 3 test passwords to include uppercase letter (schema requires it); marked 3 ChromaDB-dependent tests with `@pytest.mark.skipif` | Medium |
| `app/vectorstore/chroma_client.py` | Fixed fallback to use `EphemeralClient` instead of broken `AsyncHttpClient` double-fail | Medium |

---

## 3. Exact Code Changes

### projects.py (lines 5, 75-82)
```python
from fastapi import APIRouter, Depends, Query, Response
# ...
@router.delete("/{project_id}", status_code=204, response_class=Response)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProjectService(db)
    await service.delete_project(project_id=project_id, user=current_user)
    return Response(status_code=204)
```

### documents.py (lines 5, 91-112)
```python
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status, Response
# ...
@router.delete("/documents/{document_id}", status_code=204, response_class=Response)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    # ...
    await service.delete_document(document_id)
    return Response(status_code=204)
```

### db/session.py (added `get_async_session`)
```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### rate_limit.py (lines 54, 71)
```python
async def _check_limit(
    self, request: Request, client_id: str, path: str, window: int, max_req: int
) -> tuple[bool, int, int]:
    redis = getattr(request.app.state, "redis_client", None)
```

### registry.py (reserved keys)
```python
logger.info("agent registered", extra={"agent_name": name, "class": agent_cls.__name__})
logger.warning("agent module not found, skipping", extra={"agent_module": mod})
```

---

## 4. Additional Bugs Discovered

### 4.1 Missing `get_async_session` dependency
`app/api/agents.py` imports `get_async_session` from `app.db.session` but the function was never defined. All 5 agent routes (`/agents/run`, status, list, detail, cancel) would fail at runtime with `ImportError`.

### 4.2 Rate limiter accessing wrong app state
`app/middleware/rate_limit.py:71` used `self._app.state` (`self.app.state` after rename) to access the FastAPI app's `redis_client`. In a middleware chain, `self.app` is the **next middleware** (not the FastAPI app), which has no `.state` attribute. Fixed to use `request.app.state`.

### 4.3 Reserved LogRecord keys in structured logging
Three locations used `"name"` and one used `"module"` as extra dict keys in `logger.*(..., extra={...})`. Python's `LogRecord` reserves these keys and raises `KeyError` on collision. This caused the startup crash at `AgentRegistry.discover()`.

### 4.4 ChromaDB fallback broken
`chroma_client.py:53-61` created `AsyncHttpClient` for the fallback path — the same type that failed in the first attempt. The second attempt would also crash with `ConnectionRefusedError`. Fixed to use `EphemeralClient`.

### 4.5 Empty refresh token ambiguity
`RefreshRequest.refresh_token` had no `min_length` constraint. An empty string passed Pydantic validation (expecting 422) but was then rejected by `decode_token()` as an invalid JWT (returning 401). Added `min_length=1` for consistent 422 response.

---

## 5. Security Issues Discovered

### 5.1 Severity: Medium
- **Password complexity enforced at schema level** (uppercase, lowercase, digit) — good practice
- **JWT token versioning** implemented for invalidation — good
- **Refresh token rotation** on every refresh call — good
- **SECRET_KEY validated at startup** (length ≥ 32, not default) — good
- **No CORS misconfigurations** — `allow_origins` from settings, explicit method/header allowlist

### 5.2 No critical vulnerabilities found

---

## 6. Architecture Concerns

### 6.1 Rate limiter in middleware chain misalignment
The `RateLimitMiddleware` tries to access the FastAPI app state but sits in a middleware chain where `self.app` is the next middleware. Fixed, but the pattern is fragile — any future middleware reordering could break it again. Consider using `request.app` consistently.

### 6.2 In-memory evaluation store
`evaluation.py` uses `_evaluation_store: dict[str, dict[str, Any]] = {}` as in-memory storage. All evaluation data is lost on restart. Acceptable for dev/debug but needs persistent storage for production.

### 6.3 ChromaDB dependency coupling
Core routes (`/retrieval/search`, `/retrieval/context`, `/documents/upload`) directly depend on a running ChromaDB server. When unavailable, these routes return 500 errors. Consider graceful degradation to keyword search or meaningful error responses.

### 6.4 Lazy imports in route handlers
`reports.py:24` and `documents.py:97` import models inside function bodies. Works but inconsistent with the rest of the codebase.

### 6.5 Dramatiq worker dependency
Agent execution routes depend on Dramatiq workers for background processing. Without a running worker, `/agents/run` enqueues tasks that never execute.

---

## 7. Startup Verification Results

| Step | Result |
|------|--------|
| `python -m compileall app` | ✅ Pass (0 syntax errors) |
| `from app.main import app` | ✅ Pass (50 routes loaded) |
| `uvicorn app.main:app --lifespan on` | ✅ Pass (clean startup) |
| `GET /health` | ✅ `{"status":"ok","version":"0.1.0"}` |
| `GET /openapi.json` | ✅ 55KB schema, 46 endpoints |
| `POST /auth/register` (valid) | ✅ 201 with tokens |
| `POST /auth/register` (invalid) | ✅ 422 with errors |
| `GET /projects` (no auth) | ✅ 401 |
| `pytest tests/` | ✅ **371 passed, 3 skipped** |

### OpenAPI Endpoints (46 total)
```
GET    /health
POST   /auth/register, /auth/login, /auth/refresh
GET    /auth/me
GET    /projects, /projects/{id}
POST   /projects
PUT    /projects/{id}
DELETE /projects/{id}
GET    /sessions, /sessions/{id}
POST   /sessions
GET    /reports
POST   /reports
POST   /documents/upload
GET    /documents
DELETE /documents/{id}
POST   /retrieval/search, /retrieval/context
POST   /agents/run, /agents/cancel/{id}
GET    /agents/executions, /agents/registry
POST   /retrieval/debug, /summaries/debug, /gaps/debug
POST   /reports/generate, /reports/preview, /reports/export
GET    /evaluation/runs, /evaluation/benchmarks, /evaluation/trends, /evaluation/distributions
POST   /evaluation/benchmark/run, /evaluation/evaluate
GET    /evaluation/scorecard/{id}
GET    /approvals/pending, /approvals/{id}
POST   /approvals/{id}/approve, /approvals/{id}/reject, /approvals/{id}/rerun
GET    /metrics
```

---

## 8. Remaining Warnings

| Warning | Type | Impact |
|---------|------|--------|
| `PydanticDeprecatedSince20: class-based config` | Deprecation | Low — will need `model_config` migration for Pydantic v3 |
| `asyncio.iscoroutinefunction` deprecated | Deprecation (ChromaDB) | Low — upstream library issue |
| `coroutine was never awaited` (3 tests) | RuntimeWarning | Low — mock issue in human_approval tests |
| 3 ChromaDB tests skipped | Integration | Low — requires running ChromaDB server |

---

## 9. Production Readiness Score

**Score: 7.5 / 10**

### Strengths (+)
- **JWT auth with token versioning** and rotation
- **Fail-fast secret validation** at startup
- **Comprehensive route protection** (JWT + RBAC + ownership)
- **371 passing tests** with strong auth/security coverage
- **Structured JSON logging** across all services
- **Database session management** with auto-commit/rollback
- **Rate limiting infrastructure** (Redis backend, fail-open)

### Weaknesses (-)
- **Chromadb dependency** blocks 3 routes without server
- **In-memory evaluation store** loses data on restart
- **Dramatiq worker coupling** — agent execution is fire-and-forget
- **No CSRF protection** for cookie-based auth flows
- **Rate limiter fail-open** when Redis is unavailable (design choice)
- **Pydantic v2 deprecation warnings** need addressing

### Recommendations for 8+
1. Replace in-memory `_evaluation_store` with PostgreSQL-backed persistence
2. Implement ChromaDB graceful degradation (keyword fallback)
3. Add health check for ChromaDB and Dramatiq worker availability
4. Migrate `Settings.Config` to `model_config` (Pydantic v2)
5. Add request-level CSRF token validation

---

## 10. Summary of All Changes

```
Modified:   app/api/projects.py         (204 fix + Response import)
Modified:   app/api/documents.py        (204 fix + Response import)
Modified:   app/db/session.py           (added get_async_session)
Modified:   app/middleware/rate_limit.py (request.app.state fix)
Modified:   app/agents/registry.py       (reserved key fix x2)
Modified:   app/core/secrets.py          (reserved key fix x2)
Modified:   app/schemas/auth.py          (min_length on refresh_token)
Modified:   app/vectorstore/chroma_client.py (proper fallback)
Modified:   tests/test_api.py            (password fix + skip marks)
```

**Before:** Server crashed on startup (204 assertion + LogRecord KeyError)
**After:** Server starts clean, 371/374 tests pass, 3 skipped (ChromaDB dependency)
