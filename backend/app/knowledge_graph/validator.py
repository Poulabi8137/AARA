from __future__ import annotations

import time
from collections import deque

from app.core.logging import get_logger
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import GraphValidationReport, KnowledgeGraph, NodeType, RelationshipType

logger = get_logger("knowledge_graph.validator")
settings = get_knowledge_graph_settings()


class GraphValidator:
    def validate(self, graph: KnowledgeGraph) -> GraphValidationReport:
        start = time.monotonic()
        report = GraphValidationReport()

        self._check_orphan_nodes(graph, report)
        self._check_duplicate_nodes(graph, report)
        self._check_broken_edges(graph, report)
        self._check_missing_provenance(graph, report)
        self._check_cyclic_references(graph, report)
        self._check_confidence_inconsistencies(graph, report)
        self._check_invalid_node_types(graph, report)
        self._check_invalid_relationships(graph, report)
        self._check_connectivity(graph, report)

        max_orphan_ratio = settings.graph_max_orphan_ratio
        orphan_ratio = len(report.orphan_nodes) / max(1, len(graph.nodes))
        if orphan_ratio > max_orphan_ratio:
            report.errors.append(
                f"Orphan node ratio {orphan_ratio:.2f} exceeds max {max_orphan_ratio}"
            )

        min_connectivity = settings.graph_min_component_connectivity
        if graph.statistics.graph_density < min_connectivity and len(graph.nodes) > 5:
            report.warnings.append(
                f"Graph density {graph.statistics.graph_density:.4f} below minimum {min_connectivity}"
            )

        strict = settings.graph_validation_strictness
        if strict == "strict":
            report.is_valid = len(report.errors) == 0
        elif strict == "moderate":
            report.is_valid = len(report.errors) == 0 and len(report.warnings) <= 5
        else:
            report.is_valid = len(report.errors) <= 2

        logger.info(
            "graph validation complete",
            extra={
                "is_valid": report.is_valid,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "orphan_nodes": len(report.orphan_nodes),
                "broken_edges": len(report.broken_edges),
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            },
        )
        return report

    def _check_orphan_nodes(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        connected: set[str] = set()
        for edge in graph.edges.values():
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        for nid in graph.nodes:
            if nid not in connected:
                report.orphan_nodes.append(nid)
                report.warnings.append(f"Orphan node: {nid}")

    def _check_duplicate_nodes(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        labels_seen: dict[str, str] = {}
        for nid, node in graph.nodes.items():
            key = f"{node.node_type.value}:{node.label[:80].lower()}"
            if key in labels_seen:
                report.duplicate_nodes.append(nid)
                report.warnings.append(
                    f"Potential duplicate node: {nid} matches {labels_seen[key]}"
                )
            else:
                labels_seen[key] = nid

    def _check_broken_edges(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        for eid, edge in graph.edges.items():
            if edge.source_id not in graph.nodes:
                report.broken_edges.append(eid)
                report.errors.append(f"Broken edge {eid}: source {edge.source_id} not found")
            if edge.target_id not in graph.nodes:
                report.broken_edges.append(eid)
                report.errors.append(f"Broken edge {eid}: target {edge.target_id} not found")

    def _check_missing_provenance(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        if not settings.graph_enable_provenance:
            return
        for nid, node in graph.nodes.items():
            if not node.metadata.provenance:
                report.missing_provenance.append(nid)
        for eid, edge in graph.edges.items():
            if not edge.metadata.provenance:
                report.missing_provenance.append(eid)

    def _check_cyclic_references(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(nid: str) -> bool:
            visited.add(nid)
            rec_stack.add(nid)
            for edge in graph.adjacency.get(nid, []):
                neighbor = edge.target_id if edge.source_id == nid else edge.source_id
                if neighbor not in graph.nodes:
                    continue
                if neighbor not in visited:
                    if _dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    if edge.relationship_type in (
                        RelationshipType.CONTAINS,
                        RelationshipType.PART_OF,
                        RelationshipType.DERIVED_FROM,
                    ):
                        report.cyclic_references.append(
                            f"Cycle detected: {nid} -> {neighbor} via {edge.relationship_type.value}"
                        )
                        return True
            rec_stack.discard(nid)
            return False

        for nid in graph.nodes:
            if nid not in visited:
                _dfs(nid)

    def _check_confidence_inconsistencies(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        for eid, edge in graph.edges.items():
            source_node = graph.nodes.get(edge.source_id)
            target_node = graph.nodes.get(edge.target_id)
            if source_node and target_node:
                if edge.metadata.confidence > 1.0 or edge.metadata.confidence < 0.0:
                    report.confidence_inconsistencies.append(
                        f"Edge {eid} has out-of-range confidence: {edge.metadata.confidence}"
                    )
                if source_node.metadata.confidence > 0.9 and target_node.metadata.confidence < 0.1:
                    if edge.metadata.confidence > 0.5:
                        report.confidence_inconsistencies.append(
                            f"Confidence mismatch: source {source_node.node_id} ({source_node.metadata.confidence:.2f}) "
                            f"-> target {target_node.node_id} ({target_node.metadata.confidence:.2f}) "
                            f"via edge {eid} ({edge.metadata.confidence:.2f})"
                        )

    def _check_invalid_node_types(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        valid_types = set(NodeType)
        for nid, node in graph.nodes.items():
            if node.node_type not in valid_types:
                report.invalid_node_types.append(nid)
                report.errors.append(f"Invalid node type for {nid}: {node.node_type}")

    def _check_invalid_relationships(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        valid_rels = set(RelationshipType)
        for eid, edge in graph.edges.items():
            if edge.relationship_type not in valid_rels:
                report.invalid_relationships.append(eid)
                report.errors.append(f"Invalid relationship type for {eid}: {edge.relationship_type}")

    def _check_connectivity(
        self,
        graph: KnowledgeGraph,
        report: GraphValidationReport,
    ) -> None:
        if not graph.nodes:
            return
        visited: set[str] = set()
        start = next(iter(graph.nodes))
        stack = [start]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for edge in graph.adjacency.get(current, []):
                neighbor = edge.target_id if edge.source_id == current else edge.source_id
                if neighbor not in visited and neighbor in graph.nodes:
                    stack.append(neighbor)

        if len(visited) < len(graph.nodes):
            disconnected = len(graph.nodes) - len(visited)
            report.connectivity_issues.append(
                f"{disconnected} nodes not reachable from {start}"
            )
            if disconnected > len(graph.nodes) * 0.3:
                report.errors.append(f"Graph has poor connectivity: {disconnected} isolated nodes")
