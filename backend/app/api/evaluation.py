from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.state import make_initial_state
from app.evaluation.benchmark import BenchmarkRunner
from app.evaluation.evaluators import WorkflowEvaluator
from app.models.user import User, UserRole
from app.services.auth_service import require_role

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

_evaluator = WorkflowEvaluator()
_benchmark_runner = BenchmarkRunner()

_evaluation_store: dict[str, dict[str, Any]] = {}


@router.get("/runs")
async def list_evaluation_runs(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List evaluation runs with pagination."""
    all_runs = list(_evaluation_store.values())
    all_runs.sort(key=lambda r: r.get("evaluated_at", ""), reverse=True)
    page = all_runs[offset : offset + limit]
    return {
        "total": len(all_runs),
        "offset": offset,
        "limit": limit,
        "runs": page,
    }


@router.get("/runs/{run_id}")
async def get_evaluation_run(
    run_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Get a single evaluation run by ID."""
    run = _evaluation_store.get(run_id)
    if not run:
        raise HTTPException(
            status_code=404, detail=f"Evaluation run {run_id} not found"
        )
    return run


@router.get("/benchmarks")
async def list_benchmarks(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> list[dict[str, Any]]:
    """List all available benchmarks with their definitions."""
    return _benchmark_runner.list_benchmarks()


@router.post("/benchmark/run")
async def run_benchmark(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    benchmark_name: str = Query(..., description="Name of the benchmark to run"),
    query: str = Query(..., description="Research query to evaluate"),
) -> dict[str, Any]:
    """Run a benchmark evaluation against a simulated research state."""
    benchmark = _benchmark_runner.get_benchmark(benchmark_name)
    if not benchmark:
        raise HTTPException(
            status_code=404,
            detail=f"Benchmark '{benchmark_name}' not found. Available: {[b.name for b in _benchmark_runner.list_benchmarks()]}",
        )

    state = make_initial_state(query=query)
    result = await _benchmark_runner.run_benchmark(benchmark_name, dict(state))
    return result


@router.get("/scorecard/{execution_id}")
async def get_scorecard(
    execution_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Generate a scorecard for a given execution."""
    run = _evaluation_store.get(execution_id)
    if run:
        return run.get("scorecard", {})

    raise HTTPException(
        status_code=404,
        detail=f"No evaluation found for execution {execution_id}",
    )


@router.post("/evaluate")
async def evaluate_execution(
    state: dict[str, Any],
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    execution_id: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Run full evaluation on a research state and store the result."""
    result = await _evaluator.evaluate(
        state, execution_id=execution_id, project_id=project_id
    )
    run_id = execution_id or result.get("evaluated_at", "")
    _evaluation_store[run_id] = result
    return result


@router.get("/trends")
async def get_trends(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Compute score trends across all stored evaluations."""
    if not _evaluation_store:
        return {
            "average_quality": 0.0,
            "min_quality": 0.0,
            "max_quality": 0.0,
            "trend_direction": "insufficient_data",
            "metric_averages": {},
            "evaluation_count": 0,
        }
    return _evaluator.compute_trend(list(_evaluation_store.values()))


@router.get("/distributions")
async def get_distributions(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> dict[str, dict[str, float]]:
    """Compute metric distribution statistics across all evaluations."""
    if not _evaluation_store:
        return {}
    return _evaluator.compute_metric_distributions(list(_evaluation_store.values()))
