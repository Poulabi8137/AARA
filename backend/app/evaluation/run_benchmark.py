"""Comprehensive benchmark runner for the AARA 20-question evaluation suite.

Usage:
    python -m app.evaluation.run_benchmark
    python -m app.evaluation.run_benchmark --category "Artificial Intelligence"
    python -m app.evaluation.run_benchmark --question AI-01
    python -m app.evaluation.run_benchmark --output docs/benchmark_results.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.evaluation.benchmark_scenarios import evaluate_report
from app.evaluation.metrics import METRIC_REGISTRY, METRIC_WEIGHTS
from app.evaluation.scorecard import generate_scorecard
from app.evaluation.report import build_evaluation_report

try:
    from app.evaluation.benchmark_20_questions import (
        BENCHMARK_20_QUESTIONS,
        get_questions_by_category,
    )
except ImportError:
    BENCHMARK_20_QUESTIONS = []
    def get_questions_by_category():
        return {}

logger = get_logger("evaluation.run_benchmark")


def _collect_state_from_report(report: dict[str, Any], query: str) -> dict[str, Any]:
    """Build a ResearchState-like dict from a report dict for scorecard evaluation."""
    sections = report.get("sections", [])
    summaries = []
    for sec in sections:
        summaries.append({
            "subtopic": sec.get("title", "General"),
            "executive_summary": sec.get("summary", ""),
            "key_findings": sec.get("key_findings", []),
            "citations": sec.get("citations", []),
            "sources": [c.get("source", "") for c in sec.get("citations", [])],
            "supporting_evidence": sec.get("evidence_highlights", []),
            "coverage_score": 50.0,
            "citation_strength": 50.0,
            "consistency_score": 50.0,
            "summary_score": 50.0,
            "evidence_density": 50.0,
        })
    return {
        "query": query,
        "planner_output": json.dumps({
            "research_questions": [f"Research question about {query}"],
            "subtopics": [s.get("title", "") for s in sections],
            "methodology": "literature review",
        }),
        "summaries": summaries,
        "research_gaps": report.get("research_gaps", []),
        "generated_report": report,
    }


def evaluate_question_against_scenario(
    question: Any,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single benchmark question against a generated report."""
    start = time.monotonic()

    from app.evaluation.benchmark_scenarios import BenchmarkScenario

    scenario = BenchmarkScenario(
        name=question.id,
        query=question.query,
        objective=question.objective,
        domain=question.category,
        expected_subtopics=question.expected_subtopics,
        expected_keywords=question.expected_findings,
        min_expected_sections=3,
        expected_references=3,
        validation_rules={
            "must_mention": question.expected_findings[:3],
        },
    )

    scenario_result = evaluate_report(scenario, report)
    state = _collect_state_from_report(report, question.query)
    scorecard = generate_scorecard(state)

    elapsed = round(time.monotonic() - start, 3)

    return {
        "question_id": question.id,
        "category": question.category,
        "difficulty": question.difficulty,
        "query": question.query,
        "objective": question.objective,
        "scenario_evaluation": {
            "completeness_score": scenario_result.completeness_score,
            "confidence": scenario_result.confidence,
            "section_count": scenario_result.section_count,
            "reference_count": scenario_result.reference_count,
            "citation_count": scenario_result.citation_count,
            "has_introduction": scenario_result.has_introduction,
            "has_conclusion": scenario_result.has_conclusion,
            "has_executive_summary": scenario_result.has_executive_summary,
            "has_methodology": scenario_result.has_methodology,
            "errors": scenario_result.errors,
            "warnings": scenario_result.warnings,
        },
        "scorecard": scorecard,
        "evaluation_latency": elapsed,
    }


def score_single_question(result: dict[str, Any]) -> float:
    sc = result.get("scenario_evaluation", {})
    scorecard = result.get("scorecard", {})
    composite = scorecard.get("composite", 0)
    completeness = sc.get("completeness_score", 0)
    return round(completeness * 0.3 + composite * 0.7, 1)


BENCHMARK_GRADES = [
    (90, "A", "Excellent"),
    (80, "B", "Good"),
    (65, "C", "Acceptable"),
    (50, "D", "Weak"),
    (0, "F", "Poor"),
]


def grade_score(score: float) -> tuple[str, str]:
    for threshold, grade, label in BENCHMARK_GRADES:
        if score >= threshold:
            return grade, label
    return "F", "Poor"


def build_benchmark_report(
    results: list[dict[str, Any]],
    category_results: dict[str, list[dict[str, Any]]],
    duration: float,
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# AARA Benchmark Evaluation Report",
        "",
        f"**Generated:** {now}",
        f"**Duration:** {duration:.2f}s",
        f"**Total Questions:** {len(results)}",
        f"**Categories:** {len(category_results)}",
        "",
        "---",
        "",
        "## Overall Results",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]

    all_scores = [score_single_question(r) for r in results]
    avg = round(sum(all_scores) / max(len(all_scores), 1), 1)
    grade, label = grade_score(avg)
    passed = sum(1 for s in all_scores if s >= 60)
    failed = len(all_scores) - passed

    lines.append(f"| **Average Score** | {avg:.1f}/100 ({grade} — {label}) |")
    lines.append(f"| **Questions Passed** | {passed}/{len(all_scores)} |")
    lines.append(f"| **Questions Failed** | {failed} |")
    lines.append(f"| **Pass Rate** | {(passed/max(len(all_scores), 1))*100:.0f}% |")
    lines.append("")

    for cat_name, cat_results in sorted(category_results.items()):
        cat_scores = [score_single_question(r) for r in cat_results]
        cat_avg = round(sum(cat_scores) / max(len(cat_scores), 1), 1)
        cat_grade, cat_label = grade_score(cat_avg)
        lines.append(f"| **{cat_name}** | {cat_avg:.1f}/100 ({cat_grade} — {cat_label}) |")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## Per-Question Results",
        "",
        "| ID | Category | Difficulty | Score | Grade | Errors | Warnings |",
        "|---|---|---|---|---|---|---|",
    ])

    for i, r in enumerate(results):
        qid = r["question_id"]
        cat = r["category"]
        diff = r["difficulty"]
        score = all_scores[i]
        grade, _ = grade_score(score)
        se = r["scenario_evaluation"]
        n_err = len(se.get("errors", []))
        n_warn = len(se.get("warnings", []))
        lines.append(f"| {qid} | {cat} | {diff} | {score:.1f} | {grade} | {n_err} | {n_warn} |")

    lines.append("")

    for i, r in enumerate(results):
        lines.extend([
            "---",
            "",
            f"## {r['question_id']}: {r['query']}",
            "",
            f"**Category:** {r['category']} | **Difficulty:** {r['difficulty']}",
            "",
            f"**Objective:** {r['objective']}",
            "",
            f"**Score:** {all_scores[i]:.1f}/100 ({grade_score(all_scores[i])[0]} — {grade_score(all_scores[i])[1]})",
            "",
            "### Scenario Evaluation",
            "",
        ])
        se = r["scenario_evaluation"]
        for key in ["completeness_score", "confidence", "section_count",
                     "reference_count", "citation_count", "has_introduction",
                     "has_conclusion", "has_executive_summary", "has_methodology"]:
            val = se.get(key)
            if isinstance(val, bool):
                val = "✓" if val else "✗"
            lines.append(f"- **{key.replace('_', ' ').title()}:** {val}")
        if se.get("errors"):
            lines.extend(["", "**Errors:**"] + [f"- {e}" for e in se["errors"]])
        if se.get("warnings"):
            lines.extend(["", "**Warnings:**"] + [f"- {w}" for w in se["warnings"]])

        sc = r.get("scorecard", {})
        if sc.get("scores"):
            lines.extend(["", "### Metric Scores", ""])
            for name, score_val in sorted(sc["scores"].items()):
                if name == "research_quality":
                    continue
                bar_len = int(score_val / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                lines.append(f"- **{name.replace('_', ' ').title()}:** {score_val:.1f}/100 {bar}")

        lines.append("")

    return "\n".join(lines)


async def run_single_question(question: Any) -> dict[str, Any]:
    """Run a single benchmark question through the evaluation pipeline.

    NOTE: When the full agent pipeline is available, this function should
    create a project, run agents, and capture the resulting report. For now,
    it delegates to the scenario evaluation framework which can work with
    any report data.
    """
    report = {
        "sections": [],
        "references": [],
        "citations": [],
        "research_gaps": [],
        "executive_summary": "",
        "introduction": "",
        "methodology": "",
        "conclusion": "",
    }
    return evaluate_question_against_scenario(question, report)


async def run_benchmark_suite(
    category_filter: str | None = None,
    question_filter: str | None = None,
    output_file: str | None = None,
) -> list[dict[str, Any]]:
    questions = BENCHMARK_20_QUESTIONS
    if not questions:
        logger.warning("No 20-question benchmark suite found; using scenarios")
        return []

    if category_filter:
        questions = [q for q in questions if q.category.lower() == category_filter.lower()]
    if question_filter:
        questions = [q for q in questions if q.id.upper() == question_filter.upper()]

    if not questions:
        logger.error(f"No questions match filter: category={category_filter}, question={question_filter}")
        return []

    logger.info(f"Running benchmark suite: {len(questions)} questions")
    start = time.monotonic()

    results = []
    for q in questions:
        logger.info(f"  [{q.id}] {q.query[:60]}...")
        try:
            result = await run_single_question(q)
            results.append(result)
        except Exception as e:
            logger.error(f"  [{q.id}] Failed: {e}")
            results.append({
                "question_id": q.id,
                "category": q.category,
                "difficulty": q.difficulty,
                "query": q.query,
                "objective": q.objective,
                "scenario_evaluation": {
                    "completeness_score": 0.0,
                    "confidence": 0.0,
                    "section_count": 0,
                    "reference_count": 0,
                    "citation_count": 0,
                    "has_introduction": False,
                    "has_conclusion": False,
                    "has_executive_summary": False,
                    "has_methodology": False,
                    "errors": [str(e)],
                    "warnings": [],
                },
                "scorecard": {"scores": {}, "composite": 0, "summary": {"tier": "error", "passed": False}},
                "evaluation_latency": 0.0,
            })

    duration = time.monotonic() - start

    categories = {}
    for r in results:
        categories.setdefault(r["category"], []).append(r)

    report = build_benchmark_report(results, categories, duration)

    if output_file:
        with open(output_file, "w") as f:
            f.write(report)
        logger.info(f"Benchmark report written to {output_file}")
    else:
        print(report)

    return results


def main():
    parser = argparse.ArgumentParser(description="Run AARA research benchmark suite")
    parser.add_argument("--category", help="Filter by category name")
    parser.add_argument("--question", help="Run single question by ID (e.g., AI-01)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    results = asyncio.run(run_benchmark_suite(
        category_filter=args.category,
        question_filter=args.question,
        output_file=args.output if not args.json else None,
    ))

    if args.json:
        print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
