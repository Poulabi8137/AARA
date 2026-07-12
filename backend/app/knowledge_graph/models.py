from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    MEMORY = "memory"
    EVIDENCE = "evidence"
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    METHODOLOGY = "methodology"
    EXPERIMENT = "experiment"
    EXPERIMENT_PLAN = "experiment_plan"
    PAPER = "paper"
    DATASET = "dataset"
    BENCHMARK = "benchmark"
    METHOD = "method"
    AUTHOR = "author"
    PROJECT = "project"
    USER = "user"
    VARIABLE = "variable"
    RISK = "risk"
    RECOMMENDATION = "recommendation"
    HYPOTHESIS = "hypothesis"
    DOMAIN = "domain"
    FINDING = "finding"
    GAP = "gap"
    CONSENSUS = "consensus"
    CONTRADICTION = "contradiction"
    TREND = "trend"
    LIMITATION = "limitation"
    BEST_PRACTICE = "best_practice"
    QUERY = "query"
    GOAL = "goal"
    TASK = "task"
    OBJECTIVE = "objective"
    OUTCOME = "outcome"
    PHASE = "phase"
    STEP = "step"
    BASELINE = "baseline"


class RelationshipType(str, Enum):
    CITES = "cites"
    USES = "uses"
    EVALUATES = "evaluates"
    PROPOSES = "proposes"
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    VALIDATES = "validates"
    BELONGS_TO = "belongs_to"
    WROTE = "wrote"
    CONTAINS = "contains"
    REFERENCES = "references"
    GENERATES = "generates"
    DERIVED_FROM = "derived_from"
    TRAINS_ON = "trains_on"
    COMPARES_TO = "compares_to"
    OUTPERFORMS = "outperforms"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    MITIGATES = "mitigates"
    IDENTIFIES = "identifies"
    RECOMMENDS = "recommends"
    LEADS_TO = "leads_to"
    ADDRESSES = "addresses"
    CORRELATED_WITH = "correlated_with"


class TraversalStrategy(str, Enum):
    BFS = "bfs"
    DFS = "dfs"
    DIJKSTRA = "dijkstra"
    RANDOM_WALK = "random_walk"


class GraphOperation(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    MERGE = "merge"
    REBUILD = "rebuild"
    DELETE = "delete"


@dataclass
class NodeMetadata:
    source_type: str = ""
    source_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: float = 1.0
    provenance: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EdgeMetadata:
    confidence: float = 1.0
    weight: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: list[str] = field(default_factory=list)
    source: str = ""
    reason: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNode:
    node_id: str
    node_type: NodeType
    label: str = ""
    description: str = ""
    metadata: NodeMetadata = field(default_factory=NodeMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "description": self.description,
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class GraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    label: str = ""
    metadata: EdgeMetadata = field(default_factory=EdgeMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "label": self.label,
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class GraphRelationship:
    source_node: GraphNode
    target_node: GraphNode
    edge: GraphEdge

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source_node.to_dict(),
            "target": self.target_node.to_dict(),
            "edge": self.edge.to_dict(),
        }


@dataclass
class GraphStatistics:
    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_type: dict[str, int] = field(default_factory=dict)
    edges_by_type: dict[str, int] = field(default_factory=dict)
    avg_degree: float = 0.0
    avg_confidence: float = 0.0
    connected_components: int = 0
    graph_density: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphQuery:
    query_type: str = "find_node"
    node_type: NodeType | None = None
    node_id: str | None = None
    relationship_type: RelationshipType | None = None
    max_depth: int = 3
    max_neighbors: int = 50
    min_confidence: float = 0.0
    traversal_strategy: TraversalStrategy = TraversalStrategy.BFS
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphQueryResult:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    total_found: int = 0
    query_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "total_found": self.total_found,
            "query_time_ms": self.query_time_ms,
        }


@dataclass
class PathResult:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    total_confidence: float = 0.0
    total_weight: float = 0.0
    path_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "total_confidence": self.total_confidence,
            "total_weight": self.total_weight,
            "path_length": self.path_length,
        }


@dataclass
class TraversalResult:
    visited_nodes: list[GraphNode] = field(default_factory=list)
    visited_edges: list[GraphEdge] = field(default_factory=list)
    traversal_path: list[str] = field(default_factory=list)
    depth_reached: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "visited_nodes": [n.to_dict() for n in self.visited_nodes],
            "visited_edges": [e.to_dict() for e in self.visited_edges],
            "traversal_path": self.traversal_path,
            "depth_reached": self.depth_reached,
        }


@dataclass
class Subgraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    root_node_id: str = ""
    statistics: GraphStatistics = field(default_factory=GraphStatistics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "root_node_id": self.root_node_id,
            "statistics": self.statistics.to_dict(),
        }


@dataclass
class GraphValidationReport:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    orphan_nodes: list[str] = field(default_factory=list)
    duplicate_nodes: list[str] = field(default_factory=list)
    broken_edges: list[str] = field(default_factory=list)
    missing_provenance: list[str] = field(default_factory=list)
    cyclic_references: list[str] = field(default_factory=list)
    confidence_inconsistencies: list[str] = field(default_factory=list)
    invalid_node_types: list[str] = field(default_factory=list)
    invalid_relationships: list[str] = field(default_factory=list)
    connectivity_issues: list[str] = field(default_factory=list)


@dataclass
class GraphMetadata:
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"
    node_count: int = 0
    edge_count: int = 0
    last_operation: GraphOperation = GraphOperation.CREATE
    duration_ms: float = 0.0
    validation_passed: bool = True
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["last_operation"] = self.last_operation.value
        return result


@dataclass
class KnowledgeGraph:
    graph_id: str = ""
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, GraphEdge] = field(default_factory=dict)
    adjacency: dict[str, list[GraphEdge]] = field(default_factory=dict)
    statistics: GraphStatistics = field(default_factory=GraphStatistics)
    metadata: GraphMetadata = field(default_factory=GraphMetadata)
    validation: GraphValidationReport | None = None

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.adjacency:
            self.adjacency[node.node_id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges[edge.edge_id] = edge
        if edge.source_id in self.adjacency:
            self.adjacency[edge.source_id].append(edge)
        if edge.target_id in self.adjacency:
            pass

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self.edges.get(edge_id)

    def get_neighbors(self, node_id: str) -> list[GraphRelationship]:
        results: list[GraphRelationship] = []
        source_node = self.nodes.get(node_id)
        if not source_node:
            return results
        for edge in self.adjacency.get(node_id, []):
            target_node = self.nodes.get(edge.target_id)
            if target_node:
                results.append(GraphRelationship(
                    source_node=source_node,
                    target_node=target_node,
                    edge=edge,
                ))
        return results

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_edges_by_type(self, rel_type: RelationshipType) -> list[GraphEdge]:
        return [e for e in self.edges.values() if e.relationship_type == rel_type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
            "statistics": self.statistics.to_dict(),
            "metadata": self.metadata.to_dict(),
        }
