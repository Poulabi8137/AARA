from __future__ import annotations

import time
from collections import defaultdict

from app.core.logging import get_logger
from app.analysis.config import get_analysis_settings
from app.analysis.models import EvidenceRelationship
from app.summarization.models import EvidenceGroup

logger = get_logger("analysis.relationships")
settings = get_analysis_settings()


class RelationshipBuilder:
    def build(
        self,
        groups: list[EvidenceGroup],
    ) -> list[EvidenceRelationship]:
        start = time.monotonic()
        relationships: list[EvidenceRelationship] = []

        group_rels = self._group_relationships(groups)
        relationships.extend(group_rels)

        method_rels = self._method_relationships(groups)
        relationships.extend(method_rels)

        year_rels = self._year_relationships(groups)
        relationships.extend(year_rels)

        author_rels = self._author_relationships(groups)
        relationships.extend(author_rels)

        deduplicated = self._deduplicate(relationships)

        logger.info(
            "relationship building complete",
            extra={
                "total": len(relationships),
                "deduplicated": len(deduplicated),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return deduplicated[: settings.max_relationships]

    def _group_relationships(
        self, groups: list[EvidenceGroup]
    ) -> list[EvidenceRelationship]:
        rels: list[EvidenceRelationship] = []
        for group in groups:
            items = group.evidence
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    rels.append(
                        EvidenceRelationship(
                            source_id=items[i].source_id,
                            target_id=items[j].source_id,
                            relationship_type="same_topic",
                            strength=0.6,
                            evidence=f"Both in group: {group.label}",
                        )
                    )
        return rels

    def _method_relationships(
        self, groups: list[EvidenceGroup]
    ) -> list[EvidenceRelationship]:
        rels: list[EvidenceRelationship] = []
        for group in groups:
            for i in range(len(group.evidence)):
                for j in range(i + 1, len(group.evidence)):
                    m1 = group.evidence[i].metadata.get("methodology", "")
                    m2 = group.evidence[j].metadata.get("methodology", "")
                    if m1 and m2 and m1 == m2:
                        rels.append(
                            EvidenceRelationship(
                                source_id=group.evidence[i].source_id,
                                target_id=group.evidence[j].source_id,
                                relationship_type="same_method",
                                strength=0.8,
                                evidence=f"Both use {m1}",
                            )
                        )
        return rels

    def _year_relationships(
        self, groups: list[EvidenceGroup]
    ) -> list[EvidenceRelationship]:
        rels: list[EvidenceRelationship] = []
        year_groups: dict[str, list[str]] = defaultdict(list)
        for group in groups:
            for ev in group.evidence:
                year = ev.metadata.get("year", "")
                if year:
                    year_groups[str(year)].append(ev.source_id)

        for year, ids in year_groups.items():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    rels.append(
                        EvidenceRelationship(
                            source_id=ids[i],
                            target_id=ids[j],
                            relationship_type="same_year",
                            strength=0.4,
                            evidence=f"Both published in {year}",
                        )
                    )
        return rels

    def _author_relationships(
        self, groups: list[EvidenceGroup]
    ) -> list[EvidenceRelationship]:
        rels: list[EvidenceRelationship] = []
        author_map: dict[str, list[str]] = defaultdict(list)
        for group in groups:
            for ev in group.evidence:
                author = ev.metadata.get("author", "")
                if author:
                    author_map[str(author)].append(ev.source_id)

        for author, ids in author_map.items():
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    rels.append(
                        EvidenceRelationship(
                            source_id=ids[i],
                            target_id=ids[j],
                            relationship_type="same_author",
                            strength=0.7,
                            evidence=f"Same author: {author}",
                        )
                    )
        return rels

    def _deduplicate(
        self, relationships: list[EvidenceRelationship]
    ) -> list[EvidenceRelationship]:
        seen: set[str] = set()
        result: list[EvidenceRelationship] = []
        for rel in relationships:
            key = f"{rel.source_id}->{rel.target_id}:{rel.relationship_type}"
            reverse = f"{rel.target_id}->{rel.source_id}:{rel.relationship_type}"
            if key not in seen and reverse not in seen:
                seen.add(key)
                result.append(rel)
        return result
