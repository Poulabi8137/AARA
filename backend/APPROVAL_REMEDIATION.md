# Human Approval Persistence Fix

## 1. Problem

The human approval system had two critical design flaws:

### 1.1 In-Memory Store (No Persistence)

Previously, approval state lived entirely in an in-memory Python dict (LangGraph's `MemorySaver` checkpointer). When the server restarted — whether during deployment, a crash, or a rolling update — **all pending approvals were lost**. There was no way to recover in-flight workflows that were waiting for human review.

**Impact:** Research workflows that reached the human_approval checkpoint would stall forever after a restart. The API would return 404 for any approval lookups, and operators had no visibility into which executions were blocked.

### 1.2 Key Mismatch: `project_id` vs `execution_id`

The graph node stored the approval under `project_id`, while the API endpoints looked up approvals by `execution_id`. This mismatch meant:

| Layer       | Key Used       | Example Value                     |
|-------------|----------------|-----------------------------------|
| Graph node  | `project_id`   | `"proj-abc-123"`                  |
| API routes  | `execution_id` | `"550e8400-e29b-41d4-a716-446655440000"` |

The API could never find the approval record the graph node created, even if it were persisted. No approval could ever be retrieved, approved, rejected, or rerun.

**Impact:** The `/approvals/{execution_id}` endpoint always returned 404. Human-in-the-loop was completely non-functional.

---

## 2. Solution

Replaced the in-memory store with a **PostgreSQL-backed `HumanApproval` model** and aligned the key used across all layers to `execution_id`.

### Architecture Decision

| Before                    | After                     |
|---------------------------|---------------------------|
| `MemorySaver` checkpoint  | `human_approvals` table   |
| In-memory dict            | SQLAlchemy ORM model      |
| No auth                   | JWT + ownership checks    |
| `project_id` as key       | `execution_id` as key     |

---

## 3. Changes Made

### 3.1 `app/graphs/human_approval_node.py`

**File:** `backend/app/graphs/human_approval_node.py`

```python
# Before: in-memory checkpoint (implicit via MemorySaver)
# After: PostgreSQL persistence
async def human_approval_node(state: ResearchState) -> dict[str, Any]:
    execution_id = state.get("execution_id", state.get("project_id", ""))
    # ...
    async with async_session_factory() as db_session:
        result = await db_session.execute(
            _select(HumanApproval).where(HumanApproval.execution_id == exec_uuid)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            approval = HumanApproval(
                id=uuid.uuid4(),
                execution_id=exec_uuid,
                status=ApprovalStatus.PENDING,
                requested_at=datetime.now(timezone.utc),
            )
            db_session.add(approval)
            await db_session.flush()
```

**What changed:**
- Added `async_session_factory` import from `app.db.session`
- Added `HumanApproval`, `ApprovalStatus` import from `app.models.human_approval`
- Uses `execution_id` from state (falls back to `project_id` for backward compatibility)
- Executes a `SELECT` to check for existing record (idempotent)
- Creates a new `HumanApproval` DB row if none exists
- Catches and logs all DB exceptions without crashing the workflow
- Sets `state["approval_status"] = "awaiting_approval"` for the conditional edge router

**Key design decisions:**
- DB failure is **non-fatal**: the workflow continues in "awaiting" state even if the DB write fails
- The `SELECT` before `INSERT` pattern makes the node idempotent (safe to re-run)
- Falls back to `project_id` if `execution_id` is not in state (graceful degradation)

### 3.2 `app/api/human_approval.py`

**File:** `backend/app/api/human_approval.py`

```python
# Before: stub endpoints with no auth, no DB access
# After: Full CRUD with DB, auth, and ownership verification

@router.get("/pending")
async def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    user_project_ids = select(ResearchProject.id).where(
        ResearchProject.created_by == current_user.id
    ).scalar_subquery()
    user_exec_ids = select(AgentExecution.id).where(
        AgentExecution.project_id.in_(user_project_ids)
    ).scalar_subquery()
    result = await db.execute(
        select(HumanApproval)
        .where(
            HumanApproval.execution_id.in_(user_exec_ids),
            HumanApproval.status == ApprovalStatus.PENDING,
        )
        .order_by(HumanApproval.requested_at.desc())
    )
    approvals = result.scalars().all()
    return [{...} for a in approvals]
```

**What changed:**
- **Auth required**: All endpoints use `Depends(get_current_user)`
- **DB access**: All endpoints use `Depends(get_db)` for `AsyncSession`
- **Ownership checks**: `_get_approval_or_404()` verifies the execution's project belongs to the current user
- **Pagination-ready**: Results ordered by `requested_at DESC`
- **Five endpoints**:

| Endpoint                             | Method | Description                          |
|--------------------------------------|--------|--------------------------------------|
| `/approvals/pending`                 | GET    | List pending approvals (user scope)  |
| `/approvals/{execution_id}`          | GET    | Get approval status                  |
| `/approvals/{execution_id}/approve`  | POST   | Approve -> proceed to report gen     |
| `/approvals/{execution_id}/reject`   | POST   | Reject with feedback                 |
| `/approvals/{execution_id}/rerun`    | POST   | Request re-run -> back to gap detect |

**Ownership verification flow:**
```
approval.execution_id
  -> AgentExecution table (get exec row)
    -> project_id
      -> ResearchProject table (check created_by == current_user.id)
```

If any step fails (execution not found, project not owned), the API returns `404 Not Found` (not `403`) to avoid leaking execution IDs.

### 3.3 `app/models/human_approval.py`

**File:** `backend/app/models/human_approval.py` (new file)

```python
class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RERUN_REQUESTED = "rerun_requested"

class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id: Mapped[uuid.UUID]          # PK
    execution_id: Mapped[uuid.UUID]  # FK -> agent_executions.id
    status: Mapped[ApprovalStatus]   # pending/approved/rejected/rerun_requested
    requested_at: Mapped[datetime]   # when the checkpoint was hit
    reviewed_at: Mapped[datetime | None]  # when the human reviewed
    reviewed_by: Mapped[str | None]       # who reviewed (name or ID)
    feedback: Mapped[str | None]          # human feedback text
```

**Status state machine:**
```
                  ┌──────────┐
                  │  PENDING │
                  └────┬─────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
        ┌──────┐  ┌────────┐  ┌────────┐
        │APPROVED│  │REJECTED│  │RERUN...│
        └──────┘  └────────┘  └────────┘
```

### 3.4 `app/graphs/workflows.py`

**File:** `backend/app/graphs/workflows.py`

```python
async def run_research_workflow(state: dict[str, Any]) -> dict[str, Any]:
    execution_id = state.get("execution_id", "")
    return await workflow.arun(
        query=query,
        project_id=project_id,
        objective=objective,
        execution_id=execution_id,  # <-- NEW: passes execution_id through
    )
```

**What changed:**
- Extracts `execution_id` from state dict
- Passes it to `workflow.arun()` so the graph nodes have access to it
- Previously `execution_id` was silently dropped

### 3.5 `app/graphs/research_graph.py`

**File:** `backend/app/graphs/research_graph.py`

```python
async def arun(self, query, project_id="", objective="", thread_id=None, execution_id=""):
    state = make_initial_state(query=query, project_id=project_id, objective=objective)
    if execution_id:
        state["execution_id"] = execution_id  # <-- NEW: injects into state
    # ...
    result = await self._graph.ainvoke(state, config)
```

**What changed:**
- Added `execution_id` parameter to `arun()` signature
- Injects `execution_id` into the initial state before graph invocation
- The `human_approval_node` reads `state["execution_id"]` to persist the record

### 3.6 `app/workers/dramatiq_worker.py`

**File:** `backend/app/workers/dramatiq_worker.py`

```python
async def _execute_workflow(execution_id, query, project_id, objective):
    state = make_initial_state(query=query, project_id=project_id, objective=objective)
    state["execution_id"] = execution_id  # <-- NEW: sets execution_id
    # ...
    final_state = await run_research_workflow(state)
```

**What changed:**
- Sets `state["execution_id"] = execution_id` before calling `run_research_workflow`
- This is the entry point for the execution_id data flow

### 3.7 `tests/test_human_approval.py`

**File:** `backend/tests/test_human_approval.py`

**Test coverage:**
| Test                                   | What it validates                               |
|----------------------------------------|-------------------------------------------------|
| `test_skipped_when_disabled`           | Approval skipped when `require_human_approval=False` |
| `test_awaiting_approval_when_enabled`  | State has `approval_status=awaiting_approval` and `approval_data` |
| `test_approval_record_created`         | DB `add()` is called with a HumanApproval record |
| `test_db_failure_does_not_crash`       | DB exception is caught, workflow continues       |
| `test_empty_gaps`                      | Gaps summary works with empty gaps list          |

---

## 4. Data Flow: How `execution_id` Flows Through the System

```
API Request (FastAPI)
  │
  ▼
dramatiq_worker.py: run_workflow_actor(execution_id, ...)
  │  execution_id received from API caller
  │
  ▼
_execute_workflow()
  │  state["execution_id"] = execution_id
  │
  ▼
workflows.py: run_research_workflow(state)
  │  extracts execution_id from state
  │
  ▼
research_graph.py: ResearchWorkflow.arun(execution_id=...)
  │  state["execution_id"] = execution_id
  │
  ▼
Graph ainvoke(state)
  │  state flows through nodes: planner → retrieval → summarizer → gap_detection
  │
  ▼
human_approval_node.py: human_approval_node(state)
  │  execution_id = state.get("execution_id", state.get("project_id", ""))
  │
  ▼
PostgreSQL: human_approvals table
  │  INSERT INTO human_approvals (id, execution_id, status, requested_at)
  │  VALUES (?, ?, 'pending', ?)
  │
  ▼
API Endpoint: GET /approvals/{execution_id}
  │  Looks up HumanApproval WHERE execution_id = ?
  │  Verifies user owns the project via AgentExecution → ResearchProject join
  │
  ▼
API Endpoint: POST /approvals/{execution_id}/approve
  │  UPDATE human_approvals SET status = 'approved', reviewed_at = ?, ...
  │  WHERE execution_id = ?
  │
  ▼
Workflow resumes (polling mechanism in future iteration)
```

### Key Contract

Every part of the pipeline uses and passes through `execution_id` as a UUID string. The database stores it as `UUID(as_uuid=True)` with a foreign key to `agent_executions.id`. The conversion happens in `human_approval_node.py`:

```python
exec_uuid = uuid.UUID(execution_id) if isinstance(execution_id, str) else execution_id
```

---

## 5. Migration

The `human_approvals` table is created by Alembic migration `0005` (or equivalent).

```sql
-- Schema (automatically generated by SQLAlchemy)
CREATE TABLE human_approvals (
    id UUID PRIMARY KEY,
    execution_id UUID NOT NULL REFERENCES agent_executions(id),
    status approval_status NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(256),
    feedback TEXT
);
```

**Check migration status:**
```bash
cd backend
alembic current        # shows current migration head
alembic upgrade head   # applies pending migrations
```

If the table does not exist, run:
```bash
alembic revision --autogenerate -m "create human_approvals table"
alembic upgrade head
```

---

## 6. Auth & Ownership

### Authentication

All approval endpoints require a valid JWT token via `Depends(get_current_user)`. The `get_current_user` dependency extracts and validates the token from the `Authorization` header.

### Ownership Verification

The `_get_approval_or_404()` helper enforces project ownership:

```
1. Look up HumanApproval by execution_id
2. If found, look up AgentExecution by approval.execution_id
3. Look up ResearchProject by exec.project_id
4. Verify ResearchProject.created_by == current_user.id
5. If any check fails → 404 (not 403) to avoid ID enumeration
```

### Why 404 instead of 403?

Returning 403 would confirm that an execution_id exists (even if unowned). Returning 404 for both "not found" and "not owned" prevents attackers from probing valid execution IDs.

### Permission Matrix

| Action          | Requires Auth | Requires Ownership | Endpoint            |
|-----------------|:------------:|:------------------:|---------------------|
| List pending    | ✅           | ✅ (implicit)      | `GET /approvals/pending` |
| View status     | ✅           | ✅                  | `GET /approvals/{id}`    |
| Approve         | ✅           | ✅                  | `POST /approvals/{id}/approve` |
| Reject          | ✅           | ✅                  | `POST /approvals/{id}/reject`  |
| Request re-run  | ✅           | ✅                  | `POST /approvals/{id}/rerun`   |

---

## 7. Rollback Plan

If the DB-backed approval needs to be reverted:

1. **Disable human approval globally:** Set `require_human_approval = false` in settings — the graph node will skip to `report_generator` directly.
2. **Revert API changes:** Restore the old stub endpoints.
3. **Keep the table:** The `human_approvals` table can remain (it's harmless).
4. **Drop the table** (if needed):
   ```bash
   alembic revision --autogenerate -m "drop human_approvals table"
   alembic downgrade -1
   ```
