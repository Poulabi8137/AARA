from __future__ import annotations

import time
import uuid

from app.core.logging import get_logger
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    EdgeMetadata,
    GraphEdge,
    GraphNode,
    GraphOperation,
    GraphStatistics,
    KnowledgeGraph,
    NodeMetadata,
)

logger = get_logger("knowledge_graph.graph_builder")
settings = get_knowledge_graph_settings()


class GraphBuilder:
    def __init__(self) -> None:
        self._version_counter: int = 0

    def create_graph(self, graph_id: str | None = None) -> KnowledgeGraph:
        gid = graph_id or f"kg_{uuid.uuid4().hex[:12]}"
        graph = KnowledgeGraph(graph_id=gid)
        graph.metadata.last_operation = GraphOperation.CREATE
        logger.info("graph created", extra={"graph_id": gid})
        return graph

    def add_node(
        self,
        graph: KnowledgeGraph,
        node: GraphNode,
        merge: bool = True,
    ) -> bool:
        existing = graph.nodes.get(node.node_id)
        if existing:
            if merge:
                merged = self._merge_nodes(existing, node)
                graph.nodes[node.node_id] = merged
                logger.debug(
                    "node merged",
                    extra={"node_id": node.node_id, "type": node.node_type.value},
                )
                return True
            return False
        graph.nodes[node.node_id] = node
        if node.node_id not in graph.adjacency:
            graph.adjacency[node.node_id] = []
        logger.debug(
            "node added", extra={"node_id": node.node_id, "type": node.node_type.value}
        )
        return True

    def add_edge(
        self,
        graph: KnowledgeGraph,
        edge: GraphEdge,
        merge: bool = True,
    ) -> bool:
        if edge.source_id not in graph.nodes:
            logger.warning("edge source not found", extra={"source_id": edge.source_id})
            return False
        if edge.target_id not in graph.nodes:
            logger.warning("edge target not found", extra={"target_id": edge.target_id})
            return False

        existing = graph.edges.get(edge.edge_id)
        if existing:
            if merge:
                graph.edges[edge.edge_id] = self._merge_edges(existing, edge)
                return True
            return False

        graph.edges[edge.edge_id] = edge
        if edge.source_id in graph.adjacency:
            graph.adjacency[edge.source_id].append(edge)
        logger.debug(
            "edge added",
            extra={
                "edge_id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.relationship_type.value,
            },
        )
        return True

    def add_nodes_batch(
        self,
        graph: KnowledgeGraph,
        nodes: list[GraphNode],
        merge: bool = True,
    ) -> int:
        count = 0
        for node in nodes:
            if self.add_node(graph, node, merge=merge):
                count += 1
        return count

    def add_edges_batch(
        self,
        graph: KnowledgeGraph,
        edges: list[GraphEdge],
        merge: bool = True,
    ) -> int:
        count = 0
        for edge in edges:
            if self.add_edge(graph, edge, merge=merge):
                count += 1
        return count

    def merge_graphs(
        self,
        target: KnowledgeGraph,
        source: KnowledgeGraph,
    ) -> KnowledgeGraph:
        start = time.monotonic()

        node_count = self.add_nodes_batch(
            target, list(source.nodes.values()), merge=True
        )
        edge_count = self.add_edges_batch(
            target, list(source.edges.values()), merge=True
        )

        target.metadata.last_operation = GraphOperation.MERGE
        target.metadata.node_count = len(target.nodes)
        target.metadata.edge_count = len(target.edges)

        logger.info(
            "graphs merged",
            extra={
                "nodes_added": node_count,
                "edges_added": edge_count,
                "total_nodes": len(target.nodes),
                "total_edges": len(target.edges),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return target

    def rebuild_graph(
        self,
        graph: KnowledgeGraph,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> KnowledgeGraph:
        start = time.monotonic()
        graph.nodes = {}
        graph.edges = {}
        graph.adjacency = {}

        self.add_nodes_batch(graph, nodes, merge=False)
        self.add_edges_batch(graph, edges, merge=False)

        graph.metadata.last_operation = GraphOperation.REBUILD
        graph.metadata.node_count = len(graph.nodes)
        graph.metadata.edge_count = len(graph.edges)
        self._version_counter += 1

        logger.info(
            "graph rebuilt",
            extra={
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "version": self._version_counter,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return graph

    def remove_node(
        self,
        graph: KnowledgeGraph,
        node_id: str,
        cascade: bool = False,
    ) -> bool:
        if node_id not in graph.nodes:
            return False

        if cascade:
            edges_to_remove: list[str] = []
            for eid, edge in graph.edges.items():
                if edge.source_id == node_id or edge.target_id == node_id:
                    edges_to_remove.append(eid)
            for eid in edges_to_remove:
                del graph.edges[eid]

        del graph.nodes[node_id]
        if node_id in graph.adjacency:
            graph.adjacency[node_id] = []

        if cascade:
            for adj_list in graph.adjacency.values():
                adj_list[:] = [
                    e
                    for e in adj_list
                    if e.source_id != node_id and e.target_id != node_id
                ]

        logger.debug("node removed", extra={"node_id": node_id, "cascade": cascade})
        return True

    def remove_edge(self, graph: KnowledgeGraph, edge_id: str) -> bool:
        if edge_id not in graph.edges:
            return False
        edge = graph.edges[edge_id]
        del graph.edges[edge_id]
        if edge.source_id in graph.adjacency:
            graph.adjacency[edge.source_id] = [
                e for e in graph.adjacency[edge.source_id] if e.edge_id != edge_id
            ]
        return True

    def compute_statistics(self, graph: KnowledgeGraph) -> GraphStatistics:
        total_nodes = len(graph.nodes)
        total_edges = len(graph.edges)

        nodes_by_type: dict[str, int] = {}
        for n in graph.nodes.values():
            nt = n.node_type.value
            nodes_by_type[nt] = nodes_by_type.get(nt, 0) + 1

        edges_by_type: dict[str, int] = {}
        for e in graph.edges.values():
            rt = e.relationship_type.value
            edges_by_type[rt] = edges_by_type.get(rt, 0) + 1

        avg_degree = (2.0 * total_edges / total_nodes) if total_nodes > 0 else 0.0
        avg_confidence = (
            (sum(e.metadata.confidence for e in graph.edges.values()) / total_edges)
            if total_edges > 0
            else 0.0
        )

        max_possible = total_nodes * (total_nodes - 1) / 2.0
        graph_density = (total_edges / max_possible) if max_possible > 0 else 0.0

        connected_components = self._count_components(graph)

        return GraphStatistics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            avg_degree=round(avg_degree, 4),
            avg_confidence=round(avg_confidence, 4),
            connected_components=connected_components,
            graph_density=round(graph_density, 6),
        )

    def _count_components(self, graph: KnowledgeGraph) -> int:
        visited: set[str] = set()
        components = 0
        for nid in graph.nodes:
            if nid not in visited:
                components += 1
                stack = [nid]
                while stack:
                    current = stack.pop()
                    if current in visited:
                        continue
                    visited.add(current)
                    for edge in graph.adjacency.get(current, []):
                        neighbor = (
                            edge.target_id
                            if edge.source_id == current
                            else edge.source_id
                        )
                        if neighbor not in visited and neighbor in graph.nodes:
                            stack.append(neighbor)
        return components

    def _merge_nodes(self, a: GraphNode, b: GraphNode) -> GraphNode:
        merged_meta = NodeMetadata(
            source_type=a.metadata.source_type or b.metadata.source_type,
            source_id=a.metadata.source_id or b.metadata.source_id,
            confidence=max(a.metadata.confidence, b.metadata.confidence),
            provenance=list(set(a.metadata.provenance + b.metadata.provenance)),
            tags=list(set(a.metadata.tags + b.metadata.tags)),
            properties={**a.metadata.properties, **b.metadata.properties},
            version=max(a.metadata.version, b.metadata.version),
        )
        return GraphNode(
            node_id=a.node_id,
            node_type=a.node_type,
            label=b.label if len(b.label) > len(a.label) else a.label,
            description=b.description
            if len(b.description) > len(a.description)
            else a.description,
            metadata=merged_meta,
        )

    def _merge_edges(self, a: GraphEdge, b: GraphEdge) -> GraphEdge:
        merged_meta = EdgeMetadata(
            confidence=max(a.metadata.confidence, b.metadata.confidence),
            weight=max(a.metadata.weight, b.metadata.weight),
            provenance=list(set(a.metadata.provenance + b.metadata.provenance)),
            source=a.metadata.source or b.metadata.source,
            reason=a.metadata.reason or b.metadata.reason,
            properties={**a.metadata.properties, **b.metadata.properties},
        )
        return GraphEdge(
            edge_id=a.edge_id,
            source_id=a.source_id,
            target_id=a.target_id,
            relationship_type=a.relationship_type,
            label=a.label or b.label,
            metadata=merged_meta,
        )
