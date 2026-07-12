from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.paper_authoring_prompts import (
    EVIDENCE_VALIDATION_SYSTEM_PROMPT,
    EVIDENCE_VALIDATION_USER_PROMPT,
)
from app.core.logging import get_logger

logger = get_logger("agents.evidence_validator")


@AgentRegistry.register
class EvidenceValidatorAgent(BaseAgent):
    agent_name = "evidence_validator_agent"
    description = "Classifies factual statements in paper sections as supported, weakly supported, needs citation, or speculative"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        paper = state.get("paper_draft", {})
        sections = paper.get("sections", [])

        all_statements = []
        coverage = {"supported": 0, "weakly_supported": 0, "needs_citation": 0, "speculative": 0, "total": 0}

        for i, section in enumerate(sections):
            title = section.get("section_title", "")
            content = section.get("content", "")
            if not content:
                continue
            result = await self._validate_section(title, content)
            statements = result.get("statements", [])
            sec_coverage = result.get("coverage", {})
            all_statements.append({
                "section_number": section.get("section_number", i + 1),
                "section_title": title,
                "statements": statements,
                "coverage": sec_coverage,
            })
            for k in coverage:
                coverage[k] = coverage.get(k, 0) + sec_coverage.get(k, 0)

        coverage["total"] = sum(coverage.get(k, 0) for k in ["supported", "weakly_supported", "needs_citation", "speculative"])
        supported_ratio = coverage["supported"] / max(coverage["total"], 1)

        state["evidence_validation"] = {
            "sections": all_statements,
            "coverage": coverage,
            "overall_supported_ratio": round(supported_ratio, 3),
            "status": "complete" if coverage["total"] > 0 else "insufficient_content",
        }
        state["status"] = "evidence_validation_complete"
        state["agent_metrics"]["evidence_validator_agent"] = {
            "total_statements": coverage["total"],
            "supported_ratio": round(supported_ratio, 3),
            "latency_seconds": round(time.monotonic() - start, 3),
        }

        history = state.get("execution_history", [])
        history.append({
            "node": "evidence_validator_agent",
            "timestamp": state.get("timestamp"),
            "status": "evidence_validation_complete",
            "total_statements": coverage["total"],
            "supported_ratio": round(supported_ratio, 3),
        })
        state["execution_history"] = history

        logger.info("evidence validation complete", extra={
            "total": coverage["total"],
            "supported": coverage["supported"],
        })
        return state

    async def _validate_section(self, title: str, content: str) -> dict[str, Any]:
        prompt = EVIDENCE_VALIDATION_USER_PROMPT.format(
            section_title=title, content=content
        )
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=EVIDENCE_VALIDATION_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            return json.loads(raw)
        except Exception as exc:
            logger.warning("LLM evidence validation failed, using heuristic", extra={"error": str(exc)})
            return self._heuristic_validation(content)

    def _heuristic_validation(self, content: str) -> dict[str, Any]:
        sentences = [s.strip() for s in content.replace("\n", " ").split(".") if len(s.strip()) > 20]
        statements = []
        coverage = {"supported": 0, "weakly_supported": 0, "needs_citation": 0, "speculative": 0}

        for s in sentences:
            has_citation = bool("[" in s and "]" in s)
            is_speculative = any(w in s.lower() for w in ["expected", "proposed", "projected", "would", "could", "may", "might"])
            is_weak = any(w in s.lower() for w in ["suggests", "indicates", "potentially", "possibly"])

            if has_citation and not is_speculative:
                cls = "supported"
            elif has_citation and is_speculative:
                cls = "weakly_supported"
            elif is_speculative:
                cls = "speculative"
            elif is_weak:
                cls = "weakly_supported"
            else:
                cls = "needs_citation"

            statements.append({
                "statement": s[:200],
                "classification": cls,
                "confidence": 0.7 if cls == "supported" else 0.5,
                "citation_key": self._extract_citation(s),
                "reasoning": f"Heuristic classification: {cls}",
            })
            coverage[cls] = coverage.get(cls, 0) + 1

        coverage["total"] = sum(coverage.values())
        return {"statements": statements, "coverage": coverage}

    def _extract_citation(self, text: str) -> str | None:
        import re
        match = re.search(r'\[(\d+(?:,\s*\d+)*)\]', text)
        return match.group(1) if match else None

    async def validate_output(self, state: ResearchState) -> None:
        val = state.get("evidence_validation", {})
        if not isinstance(val, dict):
            raise ValueError("evidence_validation must be a dict")
