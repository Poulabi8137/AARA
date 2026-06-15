from __future__ import annotations

from typing import Any


def build_evaluation_report(
    evaluation_result: dict[str, Any],
    format: str = "json",
) -> str:
    """Build a human-readable evaluation report from an evaluation result.

    Args:
        evaluation_result: Output from WorkflowEvaluator.evaluate().
        format: "json" (default) or "markdown".

    Returns:
        Formatted report string.
    """
    if format == "markdown":
        return _build_markdown(evaluation_result)
    import json
    return json.dumps(evaluation_result, indent=2, default=str)


def _build_markdown(result: dict[str, Any]) -> str:
    scorecard = result.get("scorecard", {})
    scores = scorecard.get("scores", {})
    composite = scorecard.get("composite", 0)
    summary = scorecard.get("summary", {})
    query = result.get("query", "N/A")
    eval_time = result.get("evaluated_at", "")

    lines = [
        "# Evaluation Report",
        "",
        f"**Query:** {query}",
        f"**Evaluated At:** {eval_time}",
        f"**Composite Score:** {composite:.1f}/100",
        f"**Tier:** {summary.get('tier', 'unknown').upper()}",
        f"**Passed:** {'✓' if summary.get('passed') else '✗'}",
        "",
        "## Score Breakdown",
        "",
        "| Metric | Score |",
        "|--------|-----:|",
    ]
    for name, score in sorted(scores.items()):
        if name == "research_quality":
            continue
        bar = _score_bar(score)
        lines.append(f"| {name.replace('_', ' ').title()} | {score:.1f} {bar} |")

    lines.extend([
        "",
        f"**Overall Quality:** {composite:.1f}/100",
        "",
    ])

    return "\n".join(lines)


def build_trend_report(
    trend_data: dict[str, Any],
) -> str:
    """Build a trend report from WorkflowEvaluator.compute_trend() output."""
    import json
    return json.dumps(trend_data, indent=2, default=str)


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 100.0) * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"
