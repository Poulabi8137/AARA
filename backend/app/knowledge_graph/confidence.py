from __future__ import annotations

import time
from collections import deque
from typing import Any

from app.core.logging import get_logger
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import KnowledgeGraph, NodeType

logger = get_logger("knowledge_graph.confidence")
settings = get_knowledge_graph_settings()


class ConfidencePropagator:
    def __init__(self, decay: float = 0.0) -> None:
        self._decay = decay or settings.graph_confidence_decay

    def propagate(self, graph: KnowledgeGraph) -> int:
        start = time.monotonic()
        updated_count = 0

        source_nodes = self._find_source_nodes(graph)
        for source_id in source_nodes:
            count = self._propagate_from(graph, source_id)
            updated_count += count

        logger.info(
            "confidence propagation complete",
            extra={
                "source_nodes": len(source_nodes),
                "propagations": updated_count,
                "decay": self._decay,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return updated_count

    def _find_source_nodes(self, graph: KnowledgeGraph) -> list[str]:
        source_types = {
            NodeType.PAPER,
            NodeType.EVIDENCE,
            NodeType.MEMORY,
            NodeType.SUMMARY,
            NodeType.ANALYSIS,
        }
        return [
            nid
            for nid, node in graph.nodes.items()
            if node.node_type in source_types and node.metadata.confidence >= 0.5
        ]

    def _propagate_from(self, graph: KnowledgeGraph, start_id: str) -> int:
        updated = 0
        visited: set[str] = set()
        queue: deque[tuple[str, float, int]] = deque()
        queue.append((start_id, graph.nodes[start_id].metadata.confidence, 0))
        visited.add(start_id)

        while queue:
            current_id, current_conf, depth = queue.popleft()
            current_node = graph.nodes.get(current_id)
            if not current_node:
                continue

            for edge in graph.adjacency.get(current_id, []):
                neighbor_id = (
                    edge.target_id if edge.source_id == current_id else edge.source_id
                )
                if neighbor_id not in graph.nodes:
                    continue

                propagated = current_conf * self._decay * edge.metadata.confidence
                propagated = max(0.0, min(1.0, propagated))

                neighbor = graph.nodes[neighbor_id]
                if propagated > neighbor.metadata.confidence:
                    neighbor.metadata.confidence = round(propagated, 4)
                    updated += 1

                if neighbor_id not in visited and depth < settings.graph_max_depth:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, propagated, depth + 1))

        return updated

    def propagate_for_node_type(
        self,
        graph: KnowledgeGraph,
        source_type: NodeType,
        target_type: NodeType,
    ) -> int:
        start = time.monotonic()
        updated = 0

        for node in list(graph.nodes.values()):
            if node.node_type != source_type:
                continue
            if node.metadata.confidence < 0.3:
                continue
            count = self._propagate_from(graph, node.node_id)
            updated += count

        logger.info(
            "targeted confidence propagation complete",
            extra={
                "source_type": source_type.value,
                "target_type": target_type.value,
                "propagations": updated,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return updated

    def propagate_single(self, graph: KnowledgeGraph, node_id: str) -> int:
        node = graph.nodes.get(node_id)
        if not node:
            return 0
        return self._propagate_from(graph, node_id)

    def get_confidence_score(
        self,
        graph: KnowledgeGraph,
        node_id: str,
        default: float = 0.0,
    ) -> float:
        node = graph.nodes.get(node_id)
        if not node:
            return default
        return node.metadata.confidence

    def explain_confidence(
        self,
        graph: KnowledgeGraph,
        node_id: str,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "node_id": node_id,
            "current_confidence": 0.0,
            "incoming_edges": [],
            "propagation_path": [],
        }

        node = graph.nodes.get(node_id)
        if not node:
            return result

        result["current_confidence"] = node.metadata.confidence
        result["node_type"] = node.node_type.value

        incoming: list[dict] = []
        for eid, edge in graph.edges.items():
            if edge.target_id == node_id:
                source_node = graph.nodes.get(edge.source_id)
                incoming.append(
                    {
                        "edge_id": eid,
                        "source_id": edge.source_id,
                        "source_type": source_node.node_type.value
                        if source_node
                        else "unknown",
                        "source_confidence": source_node.metadata.confidence
                        if source_node
                        else 0.0,
                        "edge_confidence": edge.metadata.confidence,
                        "edge_weight": edge.metadata.weight,
                        "relationship_type": edge.relationship_type.value,
                        "propagated_confidence": round(
                            (source_node.metadata.confidence if source_node else 0.0)
                            * settings.graph_confidence_decay
                            * edge.metadata.confidence,
                            4,
                        ),
                    }
                )
        result["incoming_edges"] = incoming
        return result
