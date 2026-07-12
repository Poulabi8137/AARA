from __future__ import annotations

import json
import re
import time
from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry
from app.agents.state import ResearchState
from app.agents.summarizer_citations import (
    extract_key_phrases,
    extract_statistics,
    detect_contradictory_language,
    build_citation_index,
    compute_evidence_utilization,
    compute_compression_ratio,
)
from app.agents.summarizer_scoring import compute_summary_quality
from app.agents.summarizer_prompts import (
    SUMMARIZER_SYSTEM_PROMPT,
    SUMMARIZER_USER_PROMPT_TEMPLATE,
)
from app.schemas.summarizer import (
    SectionSummary,
    CitationRecord,
    Contradiction,
    SummarizerMetrics,
)
from app.core.logging import get_logger

logger = get_logger("agents.summarizer")

MAX_EVIDENCE_PER_BUNDLE = 15
MIN_FINDINGS = 2


@AgentRegistry.register
class SummarizerAgent(BaseAgent):
    agent_name = "summarizer"
    description = "Transforms retrieval bundles into evidence-grounded section summaries with citations"
    requires_human_approval = False

    async def arun(self, state: ResearchState) -> ResearchState:
        start = time.monotonic()
        bundles_raw = state.get("retrieved_documents", [])
        query = state.get("query", "")

        metrics = SummarizerMetrics()
        section_summaries: list[SectionSummary] = []
        total_original_chars = 0
        total_summary_chars = 0
        total_chunks = 0

        if not bundles_raw:
            logger.warning("no retrieval bundles to summarise, using fallback")
            metrics.used_fallback = True
            summary = self._fallback_summary(query)
            section_summaries.append(summary)
        else:
            for bundle in bundles_raw:
                subtopic = bundle.get("subtopic", "general")
                evidence = bundle.get("evidence", [])
                sources = bundle.get("sources", [])

                if not evidence:
                    logger.warning(
                        "empty evidence bundle", extra={"subtopic": subtopic}
                    )
                    summary = self._fallback_summary(query, subtopic)
                    section_summaries.append(summary)
                    continue

                total_chunks += len(evidence)

                # 1. Build citation index
                build_citation_index(evidence)

                # 2. Collect all evidence text
                texts = [e.get("content", "") for e in evidence]
                combined = "\n".join(texts)
                total_original_chars += len(combined)

                # 3. Extract key themes / key phrases
                all_phrases = extract_key_phrases(combined, top_n=8)

                # 4. Extract statistics
                stats = extract_statistics(combined)
                stats = list(set(stats))[:6]

                # 5. Key findings: derived from top phrases
                key_findings = []
                seen_findings: set[str] = set()
                for phrase in all_phrases:
                    for text in texts:
                        if phrase in text.lower():
                            sentences = self._extract_relevant_sentences(text, phrase)
                            for s in sentences:
                                if s not in seen_findings and len(s) > 20:
                                    seen_findings.add(s)
                                    key_findings.append(s)
                                    break
                            break
                key_findings = key_findings[:6]

                # 6. Supporting evidence: best chunks
                top_evidence = sorted(
                    evidence[:MAX_EVIDENCE_PER_BUNDLE],
                    key=lambda e: e.get("relevance_score", 0),
                    reverse=True,
                )
                supporting_evidence = []
                for e in top_evidence:
                    content = e.get("content", "")
                    if content and len(content) > 30:
                        supporting_evidence.append(content[:200])

                # 7. Consensus: phrases appearing across multiple chunks
                consensus = self._find_consensus(evidence, all_phrases)

                # 8. Contradiction detection
                contradictions = self._detect_contradictions(evidence)

                # 9. Build citations
                citations = self._build_citations(key_findings, evidence)

                # 10. Executive summary (extractive baseline)
                exec_summary = self._generate_executive_summary(
                    subtopic,
                    key_findings,
                    consensus,
                    stats,
                )

                # 11. LLM enhancement: abstractive summarization
                llm_enhanced = await self._enhance_with_llm(
                    subtopic=subtopic,
                    evidence_texts=texts,
                    key_findings=key_findings,
                    stats=stats,
                    consensus=consensus,
                    contradictions=contradictions,
                )
                if llm_enhanced is not None:
                    exec_summary = llm_enhanced.get("executive_summary", exec_summary)
                    llm_insights = llm_enhanced.get("key_insights", [])
                    if llm_insights:
                        key_findings = llm_insights[:6]
                    metrics.used_fallback = False
                else:
                    metrics.used_fallback = True

                # 12. Build SectionSummary
                summary = SectionSummary(
                    subtopic=subtopic,
                    executive_summary=exec_summary,
                    key_findings=key_findings,
                    supporting_evidence=supporting_evidence,
                    important_statistics=stats,
                    consensus_points=consensus,
                    contradictions=contradictions,
                    citations=citations,
                    confidence_score=bundle.get("confidence_score", 50.0),
                    citation_count=len(citations),
                    source_count=len(sources),
                )

                summary = compute_summary_quality(summary, bundle)
                summary._llm_enhanced = llm_enhanced is not None
                total_summary_chars += len(json.dumps(summary.model_dump()))
                section_summaries.append(summary)

        llm_enhancement_count = sum(
            1 for s in section_summaries if getattr(s, "_llm_enhanced", False)
        )

        compression = compute_compression_ratio(
            total_original_chars, total_summary_chars
        )
        if total_chunks > 0:
            sum(len(s.citations) for s in section_summaries)
            util = compute_evidence_utilization(0, [], total_chunks)
        else:
            util = 0.0

        avg_score = round(
            sum(s.summary_score for s in section_summaries)
            / max(len(section_summaries), 1),
            2,
        )

        metrics.bundles_processed = len(section_summaries)
        metrics.total_evidence_chunks = total_chunks
        metrics.total_citations = sum(s.citation_count for s in section_summaries)
        metrics.total_contradictions = sum(
            len(s.contradictions) for s in section_summaries
        )
        metrics.compression_ratio = compression
        metrics.evidence_utilization = util
        metrics.average_summary_score = avg_score
        metrics.llm_enhancement_count = llm_enhancement_count
        metrics.latency_seconds = round(time.monotonic() - start, 3)

        state["summaries"] = [s.model_dump() for s in section_summaries]
        state["status"] = "summarizer_complete"
        state["agent_metrics"]["summarizer"] = metrics.model_dump()

        logger.info(
            "summarizer complete",
            extra={
                "bundles": len(section_summaries),
                "citations": metrics.total_citations,
                "contradictions": metrics.total_contradictions,
                "avg_score": avg_score,
                "compression": compression,
                "latency": metrics.latency_seconds,
            },
        )

        return state

    # ── Private ────────────────────────────────────────

    def _extract_relevant_sentences(self, text: str, phrase: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        relevant = []
        for s in sentences:
            if phrase in s.lower() and len(s) > 15:
                relevant.append(s.strip())
        return relevant[:3]

    def _find_consensus(
        self,
        evidence: list[dict[str, Any]],
        top_phrases: list[str],
    ) -> list[str]:
        """Find themes that appear across multiple evidence chunks."""
        phrase_chunk_count: dict[str, int] = {}
        for phrase in top_phrases:
            count = 0
            for e in evidence:
                if phrase in e.get("content", "").lower():
                    count += 1
            if count >= 2:
                phrase_chunk_count[phrase] = count
        sorted_phrases = sorted(phrase_chunk_count.items(), key=lambda x: -x[1])
        return [
            f"Multiple sources confirm the importance of '{p}'"
            for p, _ in sorted_phrases[:4]
        ]

    def _detect_contradictions(
        self,
        evidence: list[dict[str, Any]],
    ) -> list[Contradiction]:
        """Detect intra-bundle contradictions."""
        contradictions: list[Contradiction] = []
        texts = [e.get("content", "") for e in evidence]
        combined = "\n".join(texts)

        signals = detect_contradictory_language(combined)
        if signals:
            contra_chunks = []
            for e in evidence:
                cid = e.get("chunk_id", "")
                for sig in signals:
                    if sig.lower() in e.get("content", "").lower():
                        contra_chunks.append(cid)
                        break
            contradictions.append(
                Contradiction(
                    topic="conflicting viewpoints",
                    statements=[
                        f"Language suggesting contradiction detected: '{s}'"
                        for s in signals[:3]
                    ],
                    source_chunk_ids=contra_chunks[:5],
                    severity="medium" if len(signals) <= 3 else "high",
                )
            )

        # Check for numerical contradictions
        numbers_a = set(re.findall(r"\b(\d+)[%]\b", texts[0])) if texts else set()
        if len(texts) > 1:
            numbers_b = set(re.findall(r"\b(\d+)[%]\b", texts[1]))
            if numbers_a and numbers_b and numbers_a != numbers_b:
                contradictions.append(
                    Contradiction(
                        topic="conflicting statistics",
                        statements=[
                            f"Different numerical claims: {numbers_a} vs {numbers_b}"
                        ],
                        severity="medium",
                    )
                )

        return contradictions

    def _build_citations(
        self,
        findings: list[str],
        evidence: list[dict[str, Any]],
    ) -> list[CitationRecord]:
        citations: list[CitationRecord] = []
        for finding in findings:
            chunk_ids: list[str] = []
            source = ""
            for e in evidence:
                cid = e.get("chunk_id", "") or str(hash(e.get("content", "")))
                content = e.get("content", "").lower()
                finding_words = set(finding.lower().split())
                overlap = sum(1 for w in finding_words if w in content and len(w) > 3)
                if overlap >= 2:
                    chunk_ids.append(cid)
                    if not source:
                        source = e.get("source", "")
            if chunk_ids:
                citations.append(
                    CitationRecord(
                        claim=finding[:120],
                        supporting_chunk_ids=chunk_ids[:3],
                        source=source,
                    )
                )
        return citations

    def _generate_executive_summary(
        self,
        subtopic: str,
        findings: list[str],
        consensus: list[str],
        stats: list[str],
    ) -> str:
        parts = [f"Analysis of {subtopic} reveals"]
        if findings:
            parts.append(f"key findings including {findings[0].lower()}")
        if stats:
            parts.append(f"with notable statistics: {'; '.join(stats[:3])}")
        if consensus:
            parts.append(f"there is consensus that {consensus[0].lower()}")
        return ". ".join(parts) + "."

    async def _enhance_with_llm(
        self,
        subtopic: str,
        evidence_texts: list[str],
        key_findings: list[str],
        stats: list[str],
        consensus: list[str],
        contradictions: list[Any],
    ) -> dict[str, Any] | None:
        """Call the LLM for abstractive summarization enhancement.

        Returns a dict with 'executive_summary' and 'key_insights' keys,
        or None if the LLM call fails or returns unparseable output.
        """
        if not evidence_texts:
            return None

        combined_evidence = "\n\n".join(
            f"[{i + 1}] {t[:500]}" for i, t in enumerate(evidence_texts[:5])
        )
        contradictions_text = (
            json.dumps(
                [
                    c.model_dump() if hasattr(c, "model_dump") else c
                    for c in contradictions
                ]
            )
            if contradictions
            else "None"
        )

        prompt = SUMMARIZER_USER_PROMPT_TEMPLATE.format(
            subtopic=subtopic,
            subtopic_evidence=combined_evidence,
            key_findings="\n".join(f"- {f}" for f in key_findings or []),
            statistics="\n".join(f"- {s}" for s in stats or []),
            consensus_points="\n".join(f"- {c}" for c in consensus or []),
            contradictions=contradictions_text,
        )

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            )
            raw = response.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                raw = raw.rsplit("\n```", 1)[0]
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("LLM response is not a JSON object")
            return result
        except Exception as exc:
            logger.warning(
                "llm summarization enhancement failed, using extractive fallback",
                extra={"subtopic": subtopic, "error": str(exc)},
            )
            return None

    def _fallback_summary(
        self, query: str, subtopic: str = "general"
    ) -> SectionSummary:
        return SectionSummary(
            subtopic=subtopic,
            executive_summary=f"Insufficient evidence to generate a detailed summary for {subtopic}.",
            key_findings=[f"No substantial findings available for {subtopic}"],
            supporting_evidence=[],
            important_statistics=[],
            consensus_points=[],
            contradictions=[],
            citations=[],
            confidence_score=10.0,
            citation_count=0,
            source_count=0,
        )
