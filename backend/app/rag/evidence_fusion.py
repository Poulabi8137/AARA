from __future__ import annotations

from app.core.logging import get_logger
from app.rag.models import RetrievedEvidence, SourceType

logger = get_logger("rag.evidence_fusion")


class EvidenceFusion:
    def fuse(
        self,
        evidence: list[RetrievedEvidence],
    ) -> list[RetrievedEvidence]:
        groups: dict[str, list[RetrievedEvidence]] = {}

        for ev in evidence:
            key = self._fusion_key(ev)
            groups.setdefault(key, []).append(ev)

        fused: list[RetrievedEvidence] = []
        for key, group in groups.items():
            if len(group) == 1:
                ev = group[0]
                if not ev.original_collections:
                    ev.original_collections = [ev.source_type]
                fused.append(ev)
            else:
                fused.append(self._merge_group(group))

        logger.info(
            "evidence fusion complete",
            extra={
                "input": len(evidence),
                "groups": len(groups),
                "fused": len(fused),
                "merged_groups": len([g for g in groups.values() if len(g) > 1]),
            },
        )
        return fused

    def _fusion_key(self, ev: RetrievedEvidence) -> str:
        content_prefix = ev.content.strip()[:200]
        return content_prefix

    def _merge_group(self, group: list[RetrievedEvidence]) -> RetrievedEvidence:
        best = max(group, key=lambda e: e.score)
        all_collections: list[SourceType] = []
        seen_coll: set[SourceType] = set()
        all_metadata: dict = {}

        for ev in group:
            coll = ev.source_type
            if coll not in seen_coll:
                seen_coll.add(coll)
                all_collections.append(coll)
            if ev.metadata:
                all_metadata.update(ev.metadata)

        best.original_collections = all_collections
        best.metadata = all_metadata
        best.score = max(best.score, max(e.score for e in group))

        provenance_parts: list[str] = []
        for ev in group:
            if ev.provenance and ev.provenance not in provenance_parts:
                provenance_parts.append(ev.provenance)
            coll_name = ev.source_type.value
            if coll_name not in provenance_parts:
                provenance_parts.append(coll_name)
        best.provenance = " | ".join(provenance_parts)

        return best
