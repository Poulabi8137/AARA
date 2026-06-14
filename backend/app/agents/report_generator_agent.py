from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.report_builder import build_report_from_state
from app.agents.report_validation import validate_report_data
from app.schemas.report_generator import ResearchReport
from app.core.logging import get_logger

logger = get_logger("agents.report_generator")


@AgentRegistry.register
class ReportGeneratorAgent(BaseAgent):
    agent_name = "report_generator"
    description = "Generates publication-quality research reports from planner output, summaries, and gaps"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        query = state.get("query", "")
        planner_output = state.get("planner_output")
        summaries = state.get("summaries", [])
        gaps = state.get("research_gaps", [])
        objective = state.get("objective", "")

        if not summaries:
            logger.warning("no summaries available, using fallback report")
            report = self._fallback_report(query, planner_output, gaps)
        else:
            report = build_report_from_state(query, planner_output, summaries, gaps, objective)

        report.metrics.generation_latency = round(time.monotonic() - start, 3)

        state["generated_report"] = report.markdown
        state["status"] = "report_generation_complete"
        state["agent_metrics"]["report_generator"] = {
            "report_title": report.title,
            "metrics": report.metrics.model_dump(),
            "section_count": len(report.sections),
            "reference_count": len(report.references),
            "research_quality_score": report.metrics.research_quality_score,
            "latency_seconds": report.metrics.generation_latency,
        }

        # Store full structured report in execution_history for API access
        history = state.get("execution_history", [])
        history.append({
            "node": "report_generator",
            "timestamp": report.generated_at,
            "status": "report_generation_complete",
            "report_metrics": report.metrics.model_dump(),
        })
        state["execution_history"] = history

        logger.info("report generation complete", extra={
            "title": report.title,
            "sections": len(report.sections),
            "references": len(report.references),
            "quality_score": report.metrics.research_quality_score,
            "latency": report.metrics.generation_latency,
        })

        return state

    async def validate_output(self, state: ResearchState) -> None:
        """Validate the generated report."""
        report_text = state.get("generated_report", "")
        if not report_text or len(report_text) < 50:
            raise ValueError("Generated report is too short or empty")

    def _fallback_report(
        self,
        query: str,
        planner_output: str | None,
        gaps: list[dict[str, Any]],
    ) -> ResearchReport:
        """Generate a minimal report when no summaries are available."""
        from app.schemas.report_generator import (
            ResearchReport, ReportSection, ReportReference, ReportMetrics,
        )

        planner = {}
        if planner_output:
            import json
            try:
                planner = json.loads(planner_output) if isinstance(planner_output, str) else planner_output
            except (json.JSONDecodeError, TypeError):
                planner = {}

        sections: list[ReportSection] = []
        references: list[ReportReference] = []
        key_findings: list[str] = []
        limitations: list[str] = []
        recommendations: list[str] = []

        if gaps:
            for g in gaps:
                gap_type = g.get("gap_type", "")
                desc = g.get("description", "")
                if gap_type == "LOW_EVIDENCE":
                    limitations.append(f"Insufficient evidence: {desc[:150]}")
                elif gap_type == "MISSING_RESEARCH_QUESTION":
                    key_findings.append(f"Unanswered: {desc[:150]}")

        recommendations.append("Complete retrieval and summarisation pipeline before generating final report.")
        recommendations.append("Verify all pipeline agents executed without errors.")

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        report = ResearchReport(
            title=f"Incomplete Report: {query}",
            query=query,
            executive_summary=f"Report generation for '{query}' could not complete due to missing summary data. "
                              f"The pipeline did not produce any section summaries.",
            introduction=f"This report was automatically generated in fallback mode for: {query}. "
                         f"Section summaries were unavailable, indicating a pipeline failure.",
            research_objectives=planner.get("research_questions", []),
            methodology=planner.get("methodology", "literature review"),
            sections=sections,
            key_findings=key_findings,
            contradictions=[],
            research_gaps=gaps,
            limitations=limitations,
            recommendations=recommendations,
            future_research=planner.get("research_questions", [])[:3],
            conclusion=f"Cannot draw conclusions for '{query}' without completed analysis. "
                       f"Address the {len(gaps)} identified gaps and re-run the research pipeline.",
            references=references,
            metrics=ReportMetrics(
                report_completeness=10.0,
                coverage_score=0.0,
                research_quality_score=5.0,
                evidence_strength=0.0,
                citation_strength=0.0,
                section_count=0,
                reference_count=0,
            ),
            generated_at=now,
        )

        report.markdown = f"# Incomplete Report: {query}\n\nFallback mode — no summaries available.\n"
        report.report_json = "{}"
        return report
