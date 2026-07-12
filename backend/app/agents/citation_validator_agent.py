from __future__ import annotations

import json
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.paper_authoring_prompts import (
    CITATION_VALIDATION_SYSTEM_PROMPT,
    CITATION_VALIDATION_USER_PROMPT,
)
from app.core.logging import get_logger

logger = get_logger("agents.citation_validator")


@AgentRegistry.register
class CitationValidatorAgent(BaseAgent):
    agent_name = "citation_validator_agent"
    description = "Validates citations for IEEE formatting, DOIs, broken URLs, and duplicate detection"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        paper = state.get("paper_draft", {})
        refs = paper.get("references", [])

        citations = await self._validate_citations(refs)
        citation_keys = set()
        duplicates = []
        validated = []
        for c in citations:
            key = c.get("citation_key", "")
            if key in citation_keys:
                duplicates.append(key)
                c["is_duplicate"] = True
            citation_keys.add(key)
            validated.append(c)

        state["citation_validation"] = {
            "citations": validated,
            "total": len(validated),
            "duplicates": list(set(duplicates)),
            "verified_count": sum(
                1 for c in validated if not c.get("is_fabricated", False)
            ),
            "has_issues": any(
                c.get("is_fabricated")
                or c.get("is_duplicate")
                or (not c.get("has_doi") and not c.get("has_url"))
                for c in validated
            ),
        }
        state["status"] = "citation_validation_complete"
        state["agent_metrics"]["citation_validator_agent"] = {
            "total_citations": len(validated),
            "verified_count": sum(
                1 for c in validated if not c.get("is_fabricated", False)
            ),
            "latency_seconds": round(time.monotonic() - start, 3),
        }

        history = state.get("execution_history", [])
        history.append(
            {
                "node": "citation_validator_agent",
                "timestamp": state.get("timestamp"),
                "status": "citation_validation_complete",
                "citation_count": len(validated),
            }
        )
        state["execution_history"] = history

        logger.info(
            "citation validation complete",
            extra={
                "total": len(validated),
                "verified": sum(
                    1 for c in validated if not c.get("is_fabricated", False)
                ),
            },
        )
        return state

    async def _validate_citations(
        self, refs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not refs:
            return []
        refs_text = "\n".join(
            f"{r.get('citation_key', '')}: {r.get('authors', '')} ({r.get('year', '')}). "
            f"{r.get('title', '')}. {r.get('journal', '')}. DOI: {r.get('doi', 'N/A')}"
            for r in refs
        )
        try:
            response = await self.llm.generate(
                prompt=CITATION_VALIDATION_USER_PROMPT.format(
                    references_text=refs_text
                ),
                system_prompt=CITATION_VALIDATION_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            result = json.loads(raw)
            return result.get("citations", [])
        except Exception as exc:
            logger.warning(
                "LLM citation validation failed, using rule-based",
                extra={"error": str(exc)},
            )
            return self._rule_based_validation(refs)

    def _rule_based_validation(
        self, refs: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        results = []
        seen_titles = set()
        for r in refs:
            key = r.get("citation_key", "")
            doi = r.get("doi", "") or ""
            url = r.get("url", "") or ""
            title = r.get("title", "").lower().strip()
            is_dup = title in seen_titles
            seen_titles.add(title)
            ieee_format = self._format_ieee(r)
            results.append(
                {
                    "citation_key": key,
                    "ieee_format": ieee_format,
                    "has_doi": bool(doi and doi.strip()),
                    "has_url": bool(url and url.strip()),
                    "is_duplicate": is_dup,
                    "is_fabricated": self._looks_fabricated(r),
                    "verification_notes": self._get_notes(r, is_dup),
                }
            )
        return results

    def _format_ieee(self, ref: dict[str, Any]) -> str:
        authors = ref.get("authors", "")
        title = ref.get("title", "")
        journal = ref.get("journal", "")
        year = ref.get("year", "")
        doi = ref.get("doi", "")
        parts = [authors] if authors else []
        if title:
            parts.append(f'"{title}"')
        if journal:
            parts.append(journal)
        if year:
            parts.append(str(year))
        result = ", ".join(parts)
        if doi:
            result += f", DOI: {doi}"
        return result

    def _looks_fabricated(self, ref: dict[str, Any]) -> bool:
        authors = (ref.get("authors") or "").lower()
        title = (ref.get("title") or "").lower()
        year = ref.get("year")
        if not authors or not title:
            return True
        if "placeholder" in authors or "placeholder" in title:
            return True
        if year and (year < 1900 or year > 2030):
            return True
        return False

    def _get_notes(self, ref: dict[str, Any], is_dup: bool) -> list[str]:
        notes = []
        if is_dup:
            notes.append("Duplicate citation detected")
        if not ref.get("doi") and not ref.get("url"):
            notes.append("No DOI or URL — verify manually")
        if self._looks_fabricated(ref):
            notes.append("May be fabricated — verify against real sources")
        if not ref.get("year"):
            notes.append("Missing publication year")
        return notes

    async def validate_output(self, state: ResearchState) -> None:
        val = state.get("citation_validation", {})
        if not isinstance(val, dict):
            raise ValueError("citation_validation must be a dict")
