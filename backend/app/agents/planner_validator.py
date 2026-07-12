from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.planner import PlannerOutput


def parse_llm_response(raw: str) -> dict[str, Any] | None:
    """Parse and optionally repair an LLM JSON response.

    Attempts:
    1. Direct json.loads
    2. Strip markdown code fences
    3. Extract JSON object from text
    4. Fix common quoting issues
    """
    text = raw.strip()

    # Attempt 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Attempt 3: find first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        candidate = text[brace_start : brace_end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Attempt 4: fix unquoted keys / trailing commas (common LLM errors)
    fixed = _repair_json(text)
    if fixed is not None:
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

    return None


def _repair_json(text: str) -> str | None:
    """Try to fix common JSON generation errors from LLMs."""
    try:
        # Find JSON boundaries
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        body = text[start : end + 1]

        # Remove trailing commas before ] or }
        body = re.sub(r",\s*([\]}])", r"\1", body)

        # Normalise quotes: replace all single quotes around content with double
        body = re.sub(r"'([^']*?)'(?=\s*[:,}\]])", r'"\1"', body)

        # Ensure all keys (now left unquoted after normalisation) are double-quoted
        body = re.sub(r"(?<![\\\"])(\b[a-zA-Z_][a-zA-Z0-9_]*\b)(\s*:)", r'"\1"\2', body)

        return body
    except Exception:
        return None


def compute_planning_score(plan: PlannerOutput) -> PlannerOutput:
    """Compute completeness, coverage, specificity, and overall score."""
    completeness = 0
    coverage = 0
    specificity = 0

    # Completeness: checks that every field is populated
    checks = 0
    if plan.research_goal and len(plan.research_goal) >= 10:
        completeness += 20
    checks += 1
    if len(plan.research_questions) >= 3:
        completeness += 15
    checks += 1
    if len(plan.keywords) >= 3:
        completeness += 10
    checks += 1
    if len(plan.search_queries) >= 5:
        completeness += 15
    checks += 1
    if len(plan.subtopics) >= 3:
        completeness += 15
    checks += 1
    if plan.methodology and len(plan.methodology) >= 5:
        completeness += 10
    checks += 1
    if len(plan.expected_deliverables) >= 1:
        completeness += 10
    checks += 1
    if len(plan.priority_areas) >= 1:
        completeness += 5
    checks += 1

    # Coverage: breadth and diversity of topics
    total_distinct = len(
        set(
            plan.research_questions
            + plan.keywords
            + plan.search_queries
            + plan.subtopics
        )
    )
    coverage = min(100, total_distinct * 3)

    # Specificity: average length and depth of entries
    avg_q_len = sum(len(q) for q in plan.research_questions) / max(
        len(plan.research_questions), 1
    )
    avg_sq_len = sum(len(sq) for sq in plan.search_queries) / max(
        len(plan.search_queries), 1
    )
    avg_sub_len = sum(len(st) for st in plan.subtopics) / max(len(plan.subtopics), 1)

    spec_score = 0
    if avg_q_len >= 30:
        spec_score += 40
    elif avg_q_len >= 20:
        spec_score += 25
    if avg_sq_len >= 30:
        spec_score += 30
    elif avg_sq_len >= 20:
        spec_score += 20
    if avg_sub_len >= 20:
        spec_score += 30
    elif avg_sub_len >= 12:
        spec_score += 20

    specificity = min(100, spec_score)

    overall = int(round((completeness + coverage + specificity) / 3))

    plan.completeness = completeness
    plan.coverage = coverage
    plan.specificity = specificity
    plan.planning_score = min(100, overall)

    return plan


def validate_plan(plan: PlannerOutput) -> list[str]:
    """Return a list of validation warnings (not errors)."""
    warnings: list[str] = []

    if not plan.research_goal.endswith(".") and not plan.research_goal.endswith("?"):
        warnings.append("research_goal should end with a period or question mark")

    questions_with_qmark = [
        q for q in plan.research_questions if q.strip().endswith("?")
    ]
    if len(questions_with_qmark) < len(plan.research_questions):
        warnings.append(
            f"{len(plan.research_questions) - len(questions_with_qmark)} research question(s) do not end with '?'"
        )

    if plan.estimated_steps < 3 or plan.estimated_steps > 15:
        warnings.append(
            f"estimated_steps ({plan.estimated_steps}) seems unusual for a research workflow"
        )

    return warnings
