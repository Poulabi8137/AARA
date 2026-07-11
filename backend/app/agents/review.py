from __future__ import annotations

import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.models import AgentContext, AgentOutput
from app.ai.evaluation.aggregation import QualityAggregator
from app.ai.evaluation.engine import EvaluationEngine
from app.ai.evaluation.metrics import (
    CitationAccuracyMetric,
    CompletenessMetric,
    GroundednessMetric,
)


class ReviewAgent(BaseAgent):
    agent_id = "review"
    agent_name = "Review Agent"
    version = "1.0"
    max_retries = 2
    timeout_seconds = 60

    def __init__(self) -> None:
        super().__init__()
        self._engine = EvaluationEngine()
        self._aggregator = QualityAggregator()
        self._citation_metric = CitationAccuracyMetric()
        self._groundedness_metric = GroundednessMetric()
        self._completeness_metric = CompletenessMetric()

    async def execute(self, context: AgentContext) -> AgentOutput:
        start = time.perf_counter()
        draft: dict[str, Any] = context.input.get("draft", {})

        quality = await self.evaluate_quality(draft)
        citation_issues = await self.verify_citations(draft)
        groundedness_issues = await self.check_groundedness(draft)
        completeness_issues = await self.check_completeness(draft)

        revision_requests = self._build_revision_requests(
            citation_issues, groundedness_issues, completeness_issues
        )

        scores = quality.get("scores", {})
        metric_results = quality.get("metric_results", [])

        self._aggregator.aggregate(metric_results)

        passed = (
            scores.get("structure", 0) >= 3
            and scores.get("citations", 0) >= 3
            and scores.get("validity", 0) >= 3
            and scores.get("clarity", 0) >= 3
            and scores.get("completeness", 0) >= 3
        )

        summary = self._build_summary(scores, citation_issues, groundedness_issues)

        review_report: dict[str, Any] = {
            "scores": scores,
            "citation_issues": citation_issues,
            "groundedness_issues": groundedness_issues,
            "revision_requests": revision_requests,
            "summary": summary,
            "passed": passed,
        }

        duration = int((time.perf_counter() - start) * 1000)
        return AgentOutput(
            agent_id=self.agent_id,
            workflow_id=context.workflow_id,
            output=review_report,
            summary=summary,
            duration_ms=duration,
        )

    async def evaluate_quality(self, draft: dict[str, Any]) -> dict[str, Any]:
        sections: list[dict[str, Any]] = draft.get("sections", [])
        citations: list[dict[str, Any]] = draft.get("citations", [])
        claims = self._extract_claims(sections)

        citation_result = await self._citation_metric.evaluate(citations=citations)
        groundedness_result = await self._groundedness_metric.evaluate(claims=claims)
        completeness_result = await self._completeness_metric.evaluate(sections=sections)

        structure_score = self._score_structure(sections)
        clarity_score = self._score_clarity(sections)

        metric_results = [citation_result, groundedness_result, completeness_result]

        scores = {
            "structure": structure_score,
            "citations": int(citation_result.score * 5),
            "validity": int(groundedness_result.score * 5),
            "clarity": clarity_score,
            "completeness": int(completeness_result.score * 5),
        }

        return {
            "scores": scores,
            "metric_results": metric_results,
        }

    async def verify_citations(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = draft.get("citations", [])
        issues: list[dict[str, Any]] = []
        for cit in citations:
            if not cit.get("doi"):
                issues.append({
                    "citation_id": cit.get("id", "unknown"),
                    "issue_type": "missing_doi",
                    "description": f"Citation {cit.get('id')} has no DOI",
                })
            if not cit.get("text"):
                issues.append({
                    "citation_id": cit.get("id", "unknown"),
                    "issue_type": "missing_text",
                    "description": f"Citation {cit.get('id')} has no reference text",
                })
        return issues

    async def check_groundedness(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = draft.get("sections", [])
        claims = self._extract_claims(sections)
        issues: list[dict[str, Any]] = []
        for claim in claims:
            if not claim.get("has_citation", False):
                issues.append({
                    "claim": claim.get("text", ""),
                    "evidence": claim.get("evidence", ""),
                    "score": 0.0,
                })
        return issues

    async def check_completeness(self, draft: dict[str, Any]) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = draft.get("sections", [])
        required_headings = {
            "title/abstract", "introduction", "related work",
            "method", "experiment design", "expected results", "discussion",
        }
        present = set(
            s.get("heading", "").strip().lower() for s in sections
        )
        issues: list[dict[str, Any]] = []
        for required in required_headings:
            if required not in present:
                issues.append({
                    "section": required,
                    "issue": "missing_section",
                    "suggestion": f"Add the '{required}' section to the draft",
                    "priority": "high",
                })
        return issues

    async def validate_output(self, output: AgentOutput) -> bool:
        report = output.output
        if "scores" not in report or not isinstance(report["scores"], dict):
            return False
        required_scores = {"structure", "citations", "validity", "clarity", "completeness"}
        if not required_scores.issubset(report["scores"].keys()):
            return False
        for key in required_scores:
            if not isinstance(report["scores"][key], (int, float)):
                return False
            if not 1 <= report["scores"][key] <= 5:
                return False
        if "citation_issues" not in report or not isinstance(report["citation_issues"], list):
            return False
        for issue in report["citation_issues"]:
            if not {"citation_id", "issue_type", "description"}.issubset(issue.keys()):
                return False
        if "groundedness_issues" not in report or not isinstance(report["groundedness_issues"], list):  # noqa: E501
            return False
        for issue in report["groundedness_issues"]:
            if not {"claim", "evidence", "score"}.issubset(issue.keys()):
                return False
        if "revision_requests" not in report or not isinstance(report["revision_requests"], list):
            return False
        for req in report["revision_requests"]:
            if not {"section", "issue", "suggestion", "priority"}.issubset(req.keys()):
                return False
        if "summary" not in report or not isinstance(report["summary"], str):
            return False
        return not ("passed" not in report or not isinstance(report["passed"], bool))

    def _extract_claims(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        claims: list[dict[str, Any]] = []
        for section in sections:
            content = section.get("content", "")
            sentences = [s.strip() for s in content.replace("\n", " ").split(".") if s.strip()]
            for sentence in sentences:
                has_cit = "@" in sentence or "doi" in sentence.lower()
                claims.append({
                    "text": sentence,
                    "has_citation": has_cit,
                    "evidence": "",
                    "section": section.get("heading", ""),
                })
        return claims

    def _score_structure(self, sections: list[dict[str, Any]]) -> int:
        if not sections:
            return 1
        expected_order = [
            "title", "abstract", "introduction", "related work",
            "method", "experiment", "result", "discussion",
        ]
        headings = [s.get("heading", "").strip().lower() for s in sections]
        matches = sum(1 for i, h in enumerate(headings) if i < len(expected_order) and expected_order[i] in h)  # noqa: E501
        score = max(1, min(5, matches + 2))
        return score

    def _score_clarity(self, sections: list[dict[str, Any]]) -> int:
        if not sections:
            return 1
        total_words = sum(len(s.get("content", "").split()) for s in sections)
        total_sentences = sum(
            len([s for s in s.get("content", "").replace("\n", " ").split(".") if s.strip()])
            for s in sections
        )
        avg_sentence_length = total_words / max(total_sentences, 1)
        if avg_sentence_length < 10 or avg_sentence_length > 40:
            return 3
        return 5

    def _build_revision_requests(
        self,
        citation_issues: list[dict[str, Any]],
        groundedness_issues: list[dict[str, Any]],
        completeness_issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        for issue in citation_issues:
            requests.append({
                "section": "citations",
                "issue": issue.get("issue_type", "citation_error"),
                "suggestion": issue.get("description", "Fix citation"),
                "priority": "high" if issue.get("issue_type") == "missing_doi" else "medium",
            })
        for issue in groundedness_issues:
            requests.append({
                "section": issue.get("section", "unknown"),
                "issue": "unsupported_claim",
                "suggestion": f"Add citation for claim: {issue.get('claim', '')[:100]}",
                "priority": "high",
            })
        for issue in completeness_issues:
            requests.append({
                "section": issue.get("section", "unknown"),
                "issue": issue.get("issue", "missing_section"),
                "suggestion": issue.get("suggestion", "Add missing section"),
                "priority": issue.get("priority", "high"),
            })
        return requests

    def _build_summary(
        self,
        scores: dict[str, int],
        citation_issues: list[dict[str, Any]],
        groundedness_issues: list[dict[str, Any]],
    ) -> str:
        avg_score = sum(scores.values()) / max(len(scores), 1)
        status = "PASSED" if avg_score >= 3 else "NEEDS REVISION"
        return (
            f"Review {status} | Average score: {avg_score:.1f}/5 | "
            f"Citation issues: {len(citation_issues)} | "
            f"Unsupported claims: {len(groundedness_issues)}"
        )
