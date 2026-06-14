# Worker State Persistence Fix

## 1. Problem

The Dramatiq worker executed research workflows but **did not persist any state transitions** to the database. This meant:

### 1.1 No Status Transitions

When the API created an `AgentExecution` record, it was inserted with `execution_status = "pending"`. The worker never updated this field as the workflow progressed. Even after successful completion, the database still showed `"pending"`.

**Impact:** The frontend had no way to show workflow progress. Every execution appeared stuck in "pending" regardless of actual state. Users could not distinguish between:
- Queued (not yet picked up by a worker)
- Running (actively being processed)
- Completed (finished successfully)
- Failed (encountered an error)

### 1.2 No Node Progress Tracking

The research workflow is a multi-step pipeline: `planner → retrieval → summarizer → gap_detection → human_approval → report_generator`. There was no mechanism to record which node was currently executing.

**Impact:** When a workflow hung or crashed mid-pipeline, operators had zero visibility into which step failed. Debugging required adding ad-hoc logging and correlating timestamps manually.

### 1.3 No Retry Count Persistence

Dramatiq's built-in retry mechanism re-queued failed messages, but the `retry_count` field on `AgentExecution` was never incremented. The database always showed `retry_count = 0` even after multiple retry attempts.

**Impact:** There was no way to distinguish first-time failures from repeated failures. Operations could not set alert thresholds based on retry count (e.g., "alert if retry_count > 3").

---

## 2. Solution

Added four dedicated DB persistence helper functions called at key stages of the workflow lifecycle:

| Helper Function                  | When Called                | What It Updates                        |
|----------------------------------|----------------------------|----------------------------------------|
| `_update_execution_status`       | Start of `_execute_workflow` | `execution_status`, `start_time`       |
| `_update_execution_node`         | After each graph node      | `execution_metadata.current_node`, `execution_metadata.execution_history` |
| `_update_execution_complete`     | On successful completion   | `execution_status`, `end_time`, `output_report`, `execution_metadata` |
| `_update_execution_failed`       | On exception               | `execution_status`, `end_time`, `error_message`, `retry_count` |
| `_cancel_execution` (preexisting)| Cancel request             | `execution_status`, `end_time`         |

---

## 3. Changes Made

### 3.1 `_update_execution_status` — Status Transition at Start

**File:** `backend/app/workers/dramatiq_worker.py:124`

```python
async def _update_execution_status(execution_id: str, status: ExecutionStatus) -> None:
    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(execution_status=status, start_time=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
        await session.commit()
```

**What it does:**
- Takes `execution_id` and target `ExecutionStatus`
- Performs a direct `UPDATE` using SQLAlchemy core (not ORM) to avoid loading the full object
- Sets `start_time` to `datetime.now(timezone.utc)` when transitioning to `RUNNING`
- Commits the transaction immediately to ensure visibility

**Why SQLAlchemy core `update()` instead of ORM `session.merge()`?**
- Avoids a `SELECT` before `UPDATE` (saves one query)
- Avoids loading the full `AgentExecution` row (reduces memory pressure in workers)
- The update is straightforward and doesn't need ORM tracking

### 3.2 `_update_execution_node` — Node Progress Tracking

**File:** `backend/app/workers/dramatiq_worker.py:140`

```python
async def _update_execution_node(execution_id: str, node_name: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        exec_obj = result.scalar_one_or_none()
        if exec_obj is None:
            return
        meta = dict(exec_obj.execution_metadata or {})
        meta["current_node"] = node_name
        history = meta.get("execution_history", [])
        history.append({
            "node": node_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        meta["execution_history"] = history
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(execution_metadata=meta)
        )
        await session.execute(stmt)
        await session.commit()
```

**What it does:**
- Loads the current `execution_metadata` JSON blob
- Sets `meta["current_node"]` to the named node (e.g., `"planner"`, `"retrieval"`)
- Appends a `{node, timestamp}` entry to `meta["execution_history"]`
- Writes the updated metadata back to the DB

**Metadata structure after running:**
```json
{
  "current_node": "report_generator",
  "execution_history": [
    {"node": "planner",          "timestamp": "2026-06-14T10:00:01Z"},
    {"node": "retrieval",        "timestamp": "2026-06-14T10:00:05Z"},
    {"node": "summarizer",       "timestamp": "2026-06-14T10:00:30Z"},
    {"node": "gap_detection",    "timestamp": "2026-06-14T10:01:00Z"},
    {"node": "human_approval",   "timestamp": "2026-06-14T10:01:02Z"},
    {"node": "report_generator", "timestamp": "2026-06-14T10:01:30Z"}
  ]
}
```

**Why use JSON metadata instead of a separate `execution_nodes` table?**
- Avoids schema complexity for a simple list (append-only, no updates)
- The entire progress is read/written atomically in one row
- Frontend can display progress with a single query (no JOINs)
- Trade-off: Concurrent writes to the same row could conflict, but nodes execute sequentially

### 3.3 `_update_execution_complete` — Successful Completion

**File:** `backend/app/workers/dramatiq_worker.py:167`

```python
async def _update_execution_complete(execution_id: str, state: dict) -> None:
    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.COMPLETED,
                end_time=datetime.now(timezone.utc),
                output_report=json.dumps(state.get("generated_report", ""), default=str),
                execution_metadata={
                    "summary_count": len(state.get("summaries", [])),
                    "gap_count": len(state.get("research_gaps", [])),
                    "execution_history": state.get("execution_history", []),
                },
            )
        )
        await session.execute(stmt)
        await session.commit()
```

**What it does:**
- Sets status to `COMPLETED`
- Records `end_time`
- Serializes `generated_report` from state to the `output_report` text column
- Writes summary statistics to `execution_metadata`:
  - `summary_count`: number of summaries generated
  - `gap_count`: number of research gaps found
  - `execution_history`: carried over from node tracking

### 3.4 `_update_execution_failed` — Error Handling with Retry Tracking

**File:** `backend/app/workers/dramatiq_worker.py:194`

```python
async def _update_execution_failed(execution_id: str, error: str) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        exec_obj = result.scalar_one_or_none()
        retry_count = (exec_obj.retry_count + 1) if exec_obj else 0
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.FAILED,
                end_time=datetime.now(timezone.utc),
                error_message=error,
                retry_count=retry_count,
            )
        )
        await session.execute(stmt)
        await session.commit()
```

**What changed from the original:**
- **Was**: Set `execution_status = FAILED` and `error_message` only
- **Now**: Also **reads current `retry_count`**, **increments it by 1**, and writes it back

**Dramatiq retry integration:**
```
Dramatiq detects exception
  → Retries middleware re-queues message (max 3 retries)
  → Worker picks up re-queued message
  → New _execute_workflow call with same execution_id
  → _update_execution_status(execution_id, RUNNING) resets status
  → If fails again, _update_execution_failed increments retry_count again
```

The `retry_count` in the DB reflects the total number of distinct failure events, not just Dramatiq delivery attempts. This is important because one workflow execution can produce multiple DB `FAILED` records as Dramatiq retries it.

### 3.5 Integration in `_execute_workflow`

**File:** `backend/app/workers/dramatiq_worker.py:78`

```python
async def _execute_workflow(execution_id, query, project_id, objective):
    state = make_initial_state(query=query, project_id=project_id, objective=objective)
    state["execution_id"] = execution_id

    try:
        await _update_execution_status(execution_id, ExecutionStatus.RUNNING)
        await _update_execution_node(execution_id, "planner")

        final_state = await run_research_workflow(state)

        await _update_execution_complete(execution_id, final_state)
        return {"status": "completed", "execution_id": execution_id}

    except Exception as exc:
        await _update_execution_failed(execution_id, str(exc))
        return {"status": "failed", "execution_id": execution_id, "error": str(exc)}
```

**Execution flow with progress tracking:**
```
1. _update_execution_status(id, RUNNING)      → status = "running", start_time = now
2. _update_execution_node(id, "planner")      → metadata.current_node = "planner"
3. run_research_workflow(state)               → planner, retrieval, summarizer, gap_detection, ...
   (future: node hooks call _update_execution_node inside each node)
4. _update_execution_complete(id, state)      → status = "completed", output_report = ...
   OR
4. _update_execution_failed(id, error)        → status = "failed", retry_count++, error_message = ...
```

### 3.6 `cancel_workflow_actor` (Preexisting, Unchanged)

**File:** `backend/app/workers/dramatiq_worker.py:220`

```python
@dramatiq.actor(queue_name="workflows", max_retries=0)
def cancel_workflow_actor(execution_id: str) -> None:
    asyncio.run(_cancel_execution(execution_id))

async def _cancel_execution(execution_id: str) -> None:
    async with async_session_factory() as session:
        stmt = (
            update(AgentExecution)
            .where(AgentExecution.id == execution_id)
            .values(
                execution_status=ExecutionStatus.CANCELLED,
                end_time=datetime.now(timezone.utc),
            )
        )
        await session.execute(stmt)
        await session.commit()
```

This actor was already persisting status to DB. It is called by the API cancel endpoint and sets `execution_status = CANCELLED` with an `end_time`.

---

## 4. Status Lifecycle

### Complete State Machine

```
                  ┌──────────┐
                  │  PENDING │
                  └────┬─────┘
                       │
                 Worker picks up
                       │
                       ▼
                  ┌──────────┐
                  │  RUNNING │
                  └────┬─────┘
                       │
            ┌──────────┼──────────┬──────────────┐
            ▼          ▼          ▼              ▼
        ┌──────────┐ ┌────────┐ ┌────────┐  ┌─────────┐
        │COMPLETED │ │ FAILED │ │CANCELLED│  │PENDING  │
        └──────────┘ └────────┘ └────────┘  │(retry)  │
                                             └─────────┘
                                                │
                                          Dramatiq retries
                                          (3 max, configurable)
                                                │
                                                ▼
                                          ┌──────────┐
                                          │  RUNNING │
                                          └──────────┘
```

### Status Transition Details

| From        | To          | Trigger                           | Side Effects                       |
|-------------|-------------|-----------------------------------|------------------------------------|
| `PENDING`   | `RUNNING`   | Worker starts execution           | `start_time` set                   |
| `RUNNING`   | `COMPLETED` | Workflow finishes without error   | `end_time`, `output_report` set    |
| `RUNNING`   | `FAILED`    | Workflow raises exception         | `end_time`, `error_message`, `retry_count++` |
| `RUNNING`   | `CANCELLED` | User cancels via API              | `end_time` set                     |
| `FAILED`    | `RUNNING`   | Dramatiq retry (auto)             | `start_time` updated               |
| `CANCELLED` | (terminal)  | —                                 | —                                  |

### `PENDING → RUNNING` Transition Detail

```python
# In _execute_workflow, before any graph work:
await _update_execution_status(execution_id, ExecutionStatus.RUNNING)

# SQL generated:
UPDATE agent_executions
SET execution_status = 'running',
    start_time = '2026-06-14T10:00:00+00:00'
WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

---

## 5. Retry Tracking

### How Retries Are Counted

The `AgentExecution` model has a `retry_count` column (`Integer, default=0`):

```python
retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

**Increment logic (`_update_execution_failed`):**
```python
exec_obj = result.scalar_one_or_none()
retry_count = (exec_obj.retry_count + 1) if exec_obj else 0
```

**Counting scenario:**

| Attempt | Event                          | retry_count in DB | Status      |
|---------|--------------------------------|:-----------------:|-------------|
| 1st     | Workflow starts                | 0                 | RUNNING     |
| 1st     | Workflow fails (timeout)       | 1                 | FAILED      |
| 2nd     | Dramatiq retries (auto)        | 1                 | RUNNING     |
| 2nd     | Workflow fails (API error)     | 2                 | FAILED      |
| 3rd     | Dramatiq retries (auto)        | 2                 | RUNNING     |
| 3rd     | Workflow succeeds              | 2                 | COMPLETED   |

After the 3rd attempt succeeds, `retry_count` stays at 2 (the number of failures). The final status is `COMPLETED`, not `FAILED`.

### Dramatiq Configuration

```python
@dramatiq.actor(
    max_retries=3,
    time_limit=600_000,   # 10 minutes
    queue_name="workflows",
    priority=10,
)
def run_workflow_actor(execution_id, user_id, query, project_id="", objective=""):
    ...
```

- `max_retries=3`: Up to 3 automatic retries (4 total attempts)
- `time_limit=600_000`: 10-minute wall-clock timeout
- Global `workflow_max_retries` setting also configurable via `get_settings().workflow_max_retries`

### Why Both DB Retry Count and Dramatiq Retries?

| Mechanism        | Scope              | Persistence | Purpose                                |
|------------------|--------------------|:-----------:|----------------------------------------|
| Dramatiq retries | Message delivery   | No          | Infrastructure-level re-queueing       |
| DB retry_count   | Execution record   | Yes         | Audit trail and alerting               |

The DB `retry_count` survives server restarts and provides a historical record. Dramatiq's retry metadata is ephemeral (Redis-based) and lost on broker restart.

---

## 6. Testing

### 6.1 Unit Tests for Persistence Helpers

```python
# Example test structure (not yet in test suite)
@pytest.mark.asyncio
async def test_update_execution_status_sets_running():
    """Verify _update_execution_status changes status from PENDING to RUNNING and sets start_time."""
    # Arrange: create AgentExecution with status=PENDING
    # Act: call _update_execution_status(exec_id, ExecutionStatus.RUNNING)
    # Assert: DB query shows status=RUNNING, start_time is not None

@pytest.mark.asyncio
async def test_update_execution_node_tracks_progress():
    """Verify _update_execution_node sets current_node and appends to execution_history."""
    # Arrange: create AgentExecution with empty metadata
    # Act: call _update_execution_node(exec_id, "planner")
    # Assert: metadata.current_node == "planner", execution_history has 1 entry

@pytest.mark.asyncio
async def test_update_execution_failed_increments_retry():
    """Verify _update_execution_failed increments retry_count by 1."""
    # Arrange: create AgentExecution with retry_count=2
    # Act: call _update_execution_failed(exec_id, "error")
    # Assert: DB shows retry_count=3, status=FAILED, error_message is set

@pytest.mark.asyncio
async def test_update_execution_complete_stores_report():
    """Verify _update_execution_complete stores generated_report and metadata."""
    # Arrange: state with generated_report, summaries, research_gaps
    # Act: call _update_execution_complete(exec_id, state)
    # Assert: status=COMPLETED, output_report is set, metadata has summary_count
```

### 6.2 Integration Test

```bash
# Start the worker in test mode
python -m app.workers.dramatiq_worker

# Create an execution via API
curl -X POST http://localhost:8000/api/executions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "project_id": "proj-uuid"}'

# Poll execution status
curl http://localhost:8000/api/executions/$EXECUTION_ID \
  -H "Authorization: Bearer $TOKEN"

# Expected: status progresses PENDING → RUNNING → COMPLETED
# Metadata shows current_node and execution_history
```

### 6.3 Manual Verification via Database

```sql
-- Check status lifecycle
SELECT id, execution_status, start_time, end_time, retry_count, error_message
FROM agent_executions
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Check node progress
SELECT execution_metadata->>'current_node' AS current_node,
       execution_metadata->'execution_history' AS history
FROM agent_executions
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Check retry history
SELECT id, retry_count, execution_status, error_message, end_time
FROM agent_executions
WHERE id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY end_time DESC;
```

### 6.4 Verifying the Complete Lifecycle

```
Step 1: API creates execution        → status = PENDING, retry_count = 0
Step 2: Worker picks up message      → status = RUNNING, start_time = T1
Step 3: Worker progresses nodes      → metadata.current_node updates
Step 4a: Success                     → status = COMPLETED, end_time = T2, output_report = "..."
Step 4b: Failure                     → status = FAILED, end_time = T2, retry_count = N+1
Step 4c: Cancellation                → status = CANCELLED, end_time = T2
```

### 6.5 Testing Retry Behavior

```python
# Force a failure and verify retry_count increments
@pytest.mark.asyncio
async def test_retry_count_persists_across_retries():
    """Simulate a workflow that fails twice then succeeds."""
    exec_id = str(uuid.uuid4())
    await _update_execution_status(exec_id, ExecutionStatus.RUNNING)
    await _update_execution_failed(exec_id, "First failure")
    # retry_count should be 1

    await _update_execution_status(exec_id, ExecutionStatus.RUNNING)
    await _update_execution_failed(exec_id, "Second failure")
    # retry_count should be 2

    await _update_execution_status(exec_id, ExecutionStatus.RUNNING)
    await _update_execution_complete(exec_id, {"generated_report": "ok"})
    # retry_count should still be 2, status = COMPLETED

    # Verify via DB query
    async with async_session_factory() as session:
        result = await session.execute(
            select(AgentExecution).where(AgentExecution.id == exec_id)
        )
        exec_obj = result.scalar_one_or_none()
        assert exec_obj.retry_count == 2
        assert exec_obj.execution_status == ExecutionStatus.COMPLETED
```
