from __future__ import annotations

import time

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.models import ExperimentPlan
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    EdgeMetadata,
    GraphEdge,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
)
from app.knowledge_graph.relationship_builder import _edge_id
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider

logger = get_logger("knowledge_graph.relationship_discovery")
settings = get_knowledge_graph_settings()

_DISCOVERY_SYSTEM: str = (
    "You are a knowledge graph relationship discovery assistant. "
    "Given two research entities, determine if a meaningful semantic relationship exists between them.\n\n"
    "Available relationship types:\n"
    "- supports: entity A provides evidence supporting entity B\n"
    "- contradicts: entity A contradicts entity B\n"
    "- extends: entity A extends or builds upon entity B\n"
    "- uses: entity A uses entity B\n"
    "- evaluates: entity A evaluates entity B\n"
    "- similar_to: entity A is semantically similar to entity B\n"
    "- correlated_with: entity A is correlated with entity B\n"
    "- leads_to: entity A leads to or causes entity B\n"
    "- addresses: entity A addresses entity B\n\n"
    "Respond with:\n"
    "Relationship: <type> | <blank if none>\n"
    "Confidence: 0.X\n"
    "Reason: <explanation>"
)

_DISCOVERY_USER: str = (
    "Entity A:\n"
    "Type: {type_a}\n"
    "Label: {label_a}\n"
    "Description: {desc_a}\n\n"
    "Entity B:\n"
    "Type: {type_b}\n"
    "Label: {label_b}\n"
    "Description: {desc_b}\n\n"
    "Determine if a meaningful relationship exists."
)


class RelationshipDiscovery:
    def __init__(self, llm: RAGLLMProvider | None = None):
        self._llm = llm

    async def discover(
        self,
        graph: KnowledgeGraph,
        analysis_result: AnalysisResult | None = None,
        methodology_result: MethodologyResult | None = None,
        experiment_plan: ExperimentPlan | None = None,
    ) -> list[GraphEdge]:
        start = time.monotonic()
        discovered: list[GraphEdge] = []

        rule_based = self._rule_based_discovery(
            graph, analysis_result, methodology_result
        )
        discovered.extend(rule_based)

        if self._llm and settings.enable_llm:
            llm_edges = await self._llm_discovery(graph)
            discovered.extend(llm_edges)

        deduped = self._deduplicate(discovered)
        added = 0
        for edge in deduped:
            if edge.source_id in graph.nodes and edge.target_id in graph.nodes:
                if edge.edge_id not in graph.edges:
                    graph.add_edge(edge)
                    added += 1

        logger.info(
            "relationship discovery complete",
            extra={
                "rule_based": len(rule_based),
                "llm_discovered": len(discovered) - len(rule_based),
                "added": added,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return deduped

    def _rule_based_discovery(
        self,
        graph: KnowledgeGraph,
        analysis_result: AnalysisResult | None,
        methodology_result: MethodologyResult | None,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []

        consensus_nodes = graph.get_nodes_by_type(NodeType.CONSENSUS)
        contradiction_nodes = graph.get_nodes_by_type(NodeType.CONTRADICTION)
        finding_nodes = graph.get_nodes_by_type(NodeType.FINDING)
        method_nodes = graph.get_nodes_by_type(NodeType.METHOD)
        dataset_nodes = graph.get_nodes_by_type(NodeType.DATASET)
        paper_nodes = graph.get_nodes_by_type(NodeType.PAPER)
        hypothesis_nodes = graph.get_nodes_by_type(NodeType.HYPOTHESIS)
        recommendation_nodes = graph.get_nodes_by_type(NodeType.RECOMMENDATION)
        trend_nodes = graph.get_nodes_by_type(NodeType.TREND)

        for cn in consensus_nodes:
            for fn in finding_nodes:
                if self._text_overlap(cn.description, fn.description) > 0.3:
                    edges.append(
                        self._make_edge(
                            cn.node_id,
                            fn.node_id,
                            RelationshipType.SUPPORTS,
                            confidence=0.6,
                            source="rule_overlap",
                            reason="Consensus and finding share content overlap",
                        )
                    )

        for cn in contradiction_nodes:
            for cn_node in consensus_nodes:
                edges.append(
                    self._make_edge(
                        cn.node_id,
                        cn_node.node_id,
                        RelationshipType.CONTRADICTS,
                        confidence=0.5,
                        source="rule_contradiction",
                        reason="Contradiction opposes consensus",
                    )
                )

        for rn in recommendation_nodes:
            for mn in method_nodes:
                edges.append(
                    self._make_edge(
                        rn.node_id,
                        mn.node_id,
                        RelationshipType.RECOMMENDS,
                        confidence=0.5,
                        source="rule_recommendation",
                        reason="Recommendation suggests method",
                    )
                )

        for hn in hypothesis_nodes:
            for tn in trend_nodes:
                edges.append(
                    self._make_edge(
                        hn.node_id,
                        tn.node_id,
                        RelationshipType.CORRELATED_WITH,
                        confidence=0.4,
                        source="rule_hypothesis_trend",
                        reason="Hypothesis relates to identified trend",
                    )
                )

        for dn in dataset_nodes:
            for mn in method_nodes:
                edges.append(
                    self._make_edge(
                        dn.node_id,
                        mn.node_id,
                        RelationshipType.USES,
                        confidence=0.5,
                        source="rule_dataset_method",
                        reason="Dataset commonly used with method",
                    )
                )

        for pn in paper_nodes:
            for mn in method_nodes:
                if self._text_overlap(pn.description, mn.description) > 0.2:
                    edges.append(
                        self._make_edge(
                            pn.node_id,
                            mn.node_id,
                            RelationshipType.PROPOSES,
                            confidence=0.4,
                            source="rule_paper_method",
                            reason="Paper likely proposes method",
                        )
                    )

        return edges

    async def _llm_discovery(
        self,
        graph: KnowledgeGraph,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        candidates = self._find_candidate_pairs(graph)
        if not candidates:
            return edges

        import asyncio

        batch_size = min(5, len(candidates))
        sem = asyncio.Semaphore(batch_size)

        async def _probe(a: str, b: str) -> GraphEdge | None:
            async with sem:
                return await self._llm_probe(graph, a, b)

        tasks = [_probe(a, b) for a, b in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, GraphEdge):
                edges.append(r)

        return edges

    def _find_candidate_pairs(
        self,
        graph: KnowledgeGraph,
    ) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        node_list = list(graph.nodes.values())
        threshold = settings.graph_node_merge_threshold
        max_pairs = 50

        count = 0
        for i, a in enumerate(node_list):
            for j, b in enumerate(node_list):
                if j <= i:
                    continue
                if count >= max_pairs:
                    break
                if a.node_type == b.node_type:
                    continue
                if a.node_id == b.node_id:
                    continue
                if (
                    self._text_overlap(
                        f"{a.label} {a.description}", f"{b.label} {b.description}"
                    )
                    > threshold
                ):
                    candidates.append((a.node_id, b.node_id))
                    count += 1
            if count >= max_pairs:
                break
        return candidates

    async def _llm_probe(
        self,
        graph: KnowledgeGraph,
        source_id: str,
        target_id: str,
    ) -> GraphEdge | None:
        source = graph.nodes.get(source_id)
        target = graph.nodes.get(target_id)
        if not source or not target:
            return None

        if not self._llm:
            return None

        try:
            content = await self._llm.generate(
                prompt=_DISCOVERY_USER.format(
                    type_a=source.node_type.value,
                    label_a=source.label[:100],
                    desc_a=source.description[:200],
                    type_b=target.node_type.value,
                    label_b=target.label[:100],
                    desc_b=target.description[:200],
                ),
                system_prompt=_DISCOVERY_SYSTEM,
                temperature=0.1,
                max_tokens=256,
            )
            return self._parse_discovery(content, source_id, target_id)
        except Exception as exc:
            logger.debug("LLM discovery probe failed", extra={"error": str(exc)})
            return None

    def _parse_discovery(
        self,
        content: str,
        source_id: str,
        target_id: str,
    ) -> GraphEdge | None:
        import re

        rel_match = re.search(r"Relationship:\s*(\w+)", content)
        conf_match = re.search(r"Confidence:\s*([0-9.]+)", content)
        reason_match = re.search(r"Reason:\s*(.+)", content, re.DOTALL)

        if not rel_match:
            return None
        rel_name = rel_match.group(1).strip().lower()
        if rel_name == "blank" or rel_name == "none":
            return None

        try:
            rel_type = RelationshipType(rel_name)
        except ValueError:
            return None

        confidence = float(conf_match.group(1)) if conf_match else 0.5
        reason = (
            reason_match.group(1).strip()
            if reason_match
            else "LLM discovered relationship"
        )

        return GraphEdge(
            edge_id=_edge_id(source_id, target_id, rel_type),
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            label=f"Discovered: {rel_type.value}",
            metadata=EdgeMetadata(
                confidence=confidence,
                weight=confidence,
                source="llm_discovery",
                reason=reason,
            ),
        )

    def _text_overlap(self, text_a: str, text_b: str) -> float:
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        return len(intersection) / max(len(set_a), len(set_b))

    def _make_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        confidence: float,
        source: str,
        reason: str,
    ) -> GraphEdge:
        return GraphEdge(
            edge_id=_edge_id(source_id, target_id, rel_type),
            source_id=source_id,
            target_id=target_id,
            relationship_type=rel_type,
            label=f"Discovered: {rel_type.value}",
            metadata=EdgeMetadata(
                confidence=confidence,
                weight=confidence,
                source=source,
                reason=reason,
            ),
        )

    def _deduplicate(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        seen: set[str] = set()
        deduped: list[GraphEdge] = []
        for e in edges:
            if e.edge_id not in seen:
                seen.add(e.edge_id)
                deduped.append(e)
        return deduped
