from __future__ import annotations

import time
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    EdgeMetadata,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeMetadata,
    NodeType,
)

logger = get_logger("knowledge_graph.provenance")
settings = get_knowledge_graph_settings()


class ProvenanceTracker:
    def track_node(
        self,
        node: GraphNode,
        component: str,
        source_ids: list[str] | None = None,
        llm_involved: bool = False,
        processing_version: str = "1.0",
    ) -> GraphNode:
        node.metadata.provenance = list(set(
            node.metadata.provenance + [f"component:{component}"]
        ))
        if source_ids:
            node.metadata.provenance = list(set(
                node.metadata.provenance + [f"source:{s}" for s in source_ids]
            ))
        node.metadata.properties["provenance_component"] = component
        node.metadata.properties["provenance_timestamp"] = datetime.now(timezone.utc).isoformat()
        node.metadata.properties["llm_involved"] = llm_involved
        node.metadata.properties["processing_version"] = processing_version
        return node

    def track_edge(
        self,
        edge: GraphEdge,
        component: str,
        source_ids: list[str] | None = None,
        llm_involved: bool = False,
        processing_version: str = "1.0",
    ) -> GraphEdge:
        edge.metadata.provenance = list(set(
            edge.metadata.provenance + [f"component:{component}"]
        ))
        if source_ids:
            edge.metadata.provenance = list(set(
                edge.metadata.provenance + [f"source:{s}" for s in source_ids]
            ))
        edge.metadata.properties["provenance_component"] = component
        edge.metadata.properties["provenance_timestamp"] = datetime.now(timezone.utc).isoformat()
        edge.metadata.properties["llm_involved"] = llm_involved
        edge.metadata.properties["processing_version"] = processing_version
        return edge

    def annotate_graph(self, graph: KnowledgeGraph, component: str) -> None:
        for node in graph.nodes.values():
            self.track_node(node, component)
        for edge in graph.edges.values():
            self.track_edge(edge, component)

    def get_node_provenance(self, graph: KnowledgeGraph, node_id: str) -> dict:
        node = graph.nodes.get(node_id)
        if not node:
            return {"error": "node not found"}
        return {
            "node_id": node.node_id,
            "node_type": node.node_type.value,
            "provenance": node.metadata.provenance,
            "source_type": node.metadata.source_type,
            "source_id": node.metadata.source_id,
            "confidence": node.metadata.confidence,
            "origin_component": node.metadata.properties.get("provenance_component", "unknown"),
            "llm_involved": node.metadata.properties.get("llm_involved", False),
            "processing_version": node.metadata.properties.get("processing_version", "unknown"),
            "created_at": node.metadata.created_at,
            "updated_at": node.metadata.updated_at,
            "version": node.metadata.version,
        }

    def get_edge_provenance(self, graph: KnowledgeGraph, edge_id: str) -> dict:
        edge = graph.edges.get(edge_id)
        if not edge:
            return {"error": "edge not found"}
        return {
            "edge_id": edge.edge_id,
            "relationship_type": edge.relationship_type.value,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "provenance": edge.metadata.provenance,
            "source": edge.metadata.source,
            "reason": edge.metadata.reason,
            "confidence": edge.metadata.confidence,
            "weight": edge.metadata.weight,
            "origin_component": edge.metadata.properties.get("provenance_component", "unknown"),
            "llm_involved": edge.metadata.properties.get("llm_involved", False),
            "timestamp": edge.metadata.timestamp,
        }

    def get_graph_provenance_summary(self, graph: KnowledgeGraph) -> dict:
        components: dict[str, int] = {}
        llm_count = 0
        total_nodes = len(graph.nodes)
        total_edges = len(graph.edges)

        for node in graph.nodes.values():
            comp = node.metadata.properties.get("provenance_component", "unknown")
            components[comp] = components.get(comp, 0) + 1
            if node.metadata.properties.get("llm_involved"):
                llm_count += 1

        for edge in graph.edges.values():
            comp = edge.metadata.properties.get("provenance_component", "unknown")
            components[comp] = components.get(comp, 0) + 1
            if edge.metadata.properties.get("llm_involved"):
                llm_count += 1

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "components_involved": list(components.keys()),
            "entities_by_component": components,
            "llm_involved_entities": llm_count,
            "graph_created": graph.metadata.created_at,
            "graph_updated": graph.metadata.updated_at,
            "graph_version": graph.metadata.version,
        }
