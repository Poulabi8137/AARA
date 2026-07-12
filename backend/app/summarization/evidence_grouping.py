from __future__ import annotations

from collections import defaultdict

from app.core.logging import get_logger
from app.summarization.models import EvidenceGroup, GroupingStrategy
from app.rag.models import RetrievedEvidence

logger = get_logger("summarization.evidence_grouping")

_GROUP_KEY_MAP: dict[str, str] = {
    "topic": "topic",
    "methodology": "methodology",
    "year": "year",
    "dataset": "dataset",
    "benchmark": "benchmark",
    "author": "author",
    "institution": "institution",
    "domain": "domain",
}


class EvidenceGrouper:
    def group(
        self,
        evidence: list[RetrievedEvidence],
        strategy: GroupingStrategy = GroupingStrategy.TOPIC,
    ) -> list[EvidenceGroup]:
        if not evidence:
            return []

        if strategy == GroupingStrategy.TOPIC:
            return self._group_by_topic(evidence)
        if strategy == GroupingStrategy.YEAR:
            return self._group_by_year(evidence)
        if strategy == GroupingStrategy.METHODOLOGY:
            return self._group_by_metadata(evidence, "methodology", "Unknown Methodology")
        if strategy == GroupingStrategy.DATASET:
            return self._group_by_metadata(evidence, "dataset", "Unknown Dataset")
        if strategy == GroupingStrategy.BENCHMARK:
            return self._group_by_metadata(evidence, "benchmark", "Unknown Benchmark")
        if strategy == GroupingStrategy.AUTHOR:
            return self._group_by_metadata(evidence, "author", "Unknown Author")
        if strategy == GroupingStrategy.INSTITUTION:
            return self._group_by_metadata(evidence, "institution", "Unknown Institution")
        if strategy == GroupingStrategy.DOMAIN:
            return self._group_by_metadata(evidence, "domain", "General")

        return [EvidenceGroup(label="All Evidence", evidence=evidence)]

    def _group_by_topic(
        self, evidence: list[RetrievedEvidence]
    ) -> list[EvidenceGroup]:
        buckets: dict[str, list[RetrievedEvidence]] = defaultdict(list)
        for ev in evidence:
            topic = ev.metadata.get("topic", "") or ev.metadata.get("category", "") or ev.metadata.get("domain", "")
            if not topic:
                source = ev.source_type.value.replace("_", " ").title()
                if any(kw in ev.content[:100].lower() for kw in ["method", "approach", "technique"]):
                    topic = "Methodology"
                elif any(kw in ev.content[:100].lower() for kw in ["result", "finding", "performance"]):
                    topic = "Results"
                elif any(kw in ev.content[:100].lower() for kw in ["dataset", "data", "corpus"]):
                    topic = "Datasets"
                else:
                    topic = source
            buckets[topic].append(ev)

        groups: list[EvidenceGroup] = []
        for label, items in sorted(buckets.items(), key=lambda x: -len(x[1])):
            group = EvidenceGroup(
                label=label[:60],
                evidence=items,
                citation_keys=[_citation_key(e, i) for i, e in enumerate(items)],
            )
            groups.append(group)

        logger.info(
            "evidence grouped by topic",
            extra={"groups": len(groups), "total": len(evidence)},
        )
        return groups

    def _group_by_year(
        self, evidence: list[RetrievedEvidence]
    ) -> list[EvidenceGroup]:
        buckets: dict[str, list[RetrievedEvidence]] = defaultdict(list)
        for ev in evidence:
            year = ev.metadata.get("year", "")
            if not year and ev.metadata.get("created_at"):
                try:
                    year = str(int(ev.metadata["created_at"][:4]))
                except (ValueError, IndexError):
                    year = "Unknown"
            if not year:
                year = "Unknown"
            buckets[str(year)].append(ev)

        groups = [
            EvidenceGroup(label=f"Year: {year}", evidence=items)
            for year, items in sorted(buckets.items(), reverse=True)
        ]
        logger.info(
            "evidence grouped by year",
            extra={"groups": len(groups), "total": len(evidence)},
        )
        return groups

    def _group_by_metadata(
        self,
        evidence: list[RetrievedEvidence],
        field: str,
        default_label: str,
    ) -> list[EvidenceGroup]:
        buckets: dict[str, list[RetrievedEvidence]] = defaultdict(list)
        for ev in evidence:
            val = ev.metadata.get(field, default_label)
            buckets[str(val) if val else default_label].append(ev)

        groups = [
            EvidenceGroup(label=v[:60], evidence=items)
            for v, items in sorted(buckets.items(), key=lambda x: -len(x[1]))
        ]
        logger.info(
            "evidence grouped by metadata field",
            extra={"field": field, "groups": len(groups), "total": len(evidence)},
        )
        return groups


def _citation_key(ev: RetrievedEvidence, index: int) -> str:
    title = ev.metadata.get("title", "") or ev.metadata.get("paper_title", "")
    if title:
        return f"[{index + 1}] {title[:60]}"
    return f"[{index + 1}] {ev.source_type.value}"
