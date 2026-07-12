from __future__ import annotations

import time
from collections import deque
from typing import Any

from app.core.logging import get_logger
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    GraphEdge,
    GraphNode,
    GraphQuery,
    GraphQueryResult,
    KnowledgeGraph,
    NodeType,
    PathResult,
    RelationshipType,
    Subgraph,
    TraversalResult,
    TraversalStrategy,
)

logger = get_logger("knowledge_graph.query_engine")
settings = get_knowledge_graph_settings()


class GraphQueryEngine:
    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph

    def find_node(self, node_id: str) -> GraphNode | None:
        return self._graph.nodes.get(node_id)

    def find_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return self._graph.get_nodes_by_type(node_type)

    def find_nodes_by_label(self, query: str) -> list[GraphNode]:
        q = query.lower()
        return [
            n
            for n in self._graph.nodes.values()
            if q in n.label.lower() or q in n.description.lower()
        ]

    def find_neighbors(
        self,
        node_id: str,
        max_depth: int = 1,
        rel_types: list[RelationshipType] | None = None,
        min_confidence: float = 0.0,
    ) -> list[GraphNode]:
        visited: set[str] = set()
        results: list[GraphNode] = []
        queue: deque[tuple[str, int]] = deque()
        queue.append((node_id, 0))
        visited.add(node_id)

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._graph.adjacency.get(current, []):
                if edge.metadata.confidence < min_confidence:
                    continue
                if rel_types and edge.relationship_type not in rel_types:
                    continue
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited:
                    visited.add(neighbor)
                    neighbor_node = self._graph.nodes.get(neighbor)
                    if neighbor_node:
                        results.append(neighbor_node)
                    queue.append((neighbor, depth + 1))
        return results

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 10,
    ) -> PathResult | None:
        if source_id not in self._graph.nodes or target_id not in self._graph.nodes:
            return None

        visited: dict[str, tuple[str | None, str | None]] = {source_id: (None, None)}
        queue: deque[str] = deque([source_id])

        while queue:
            current = queue.popleft()
            if current == target_id:
                return self._reconstruct_path(source_id, target_id, visited)

            for edge in self._graph.adjacency.get(current, []):
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited:
                    visited[neighbor] = (current, edge.edge_id)
                    if len(visited) <= max_length:
                        queue.append(neighbor)

        return None

    def _reconstruct_path(
        self,
        source_id: str,
        target_id: str,
        visited: dict[str, tuple[str | None, str | None]],
    ) -> PathResult:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        total_confidence = 1.0
        total_weight = 0.0

        current = target_id
        while current is not None:
            node = self._graph.nodes.get(current)
            if node:
                nodes.append(node)
            prev, eid = visited.get(current, (None, None))
            if eid:
                edge = self._graph.edges.get(eid)
                if edge:
                    edges.append(edge)
                    total_confidence *= edge.metadata.confidence
                    total_weight += edge.metadata.weight
            current = prev

        nodes.reverse()
        edges.reverse()

        return PathResult(
            nodes=nodes,
            edges=edges,
            total_confidence=round(total_confidence, 4),
            total_weight=round(total_weight, 4),
            path_length=len(edges),
        )

    def find_related(
        self,
        node_id: str,
        rel_types: list[RelationshipType] | None = None,
        max_results: int = 20,
    ) -> list[GraphNode]:
        node = self._graph.nodes.get(node_id)
        if not node:
            return []

        neighbors = self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=rel_types,
        )
        scored: list[tuple[GraphNode, float]] = []
        for neighbor in neighbors:
            score = self._compute_relevance(node, neighbor)
            scored.append((neighbor, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [n for n, _ in scored[:max_results]]

    def _compute_relevance(self, source: GraphNode, target: GraphNode) -> float:
        score = 0.0
        for edge in self._graph.adjacency.get(source.node_id, []):
            if edge.target_id == target.node_id or edge.source_id == target.node_id:
                score += edge.metadata.confidence * edge.metadata.weight
        return score

    def traverse(
        self,
        start_node_id: str,
        strategy: TraversalStrategy = TraversalStrategy.BFS,
        max_depth: int = 5,
        node_filter: Any = None,
    ) -> TraversalResult:
        if strategy == TraversalStrategy.BFS:
            return self._bfs_traverse(start_node_id, max_depth, node_filter)
        elif strategy == TraversalStrategy.DFS:
            return self._dfs_traverse(start_node_id, max_depth, node_filter)
        elif strategy == TraversalStrategy.RANDOM_WALK:
            return self._random_walk(start_node_id, max_depth, node_filter)
        return TraversalResult()

    def _bfs_traverse(
        self,
        start: str,
        max_depth: int,
        node_filter: Any,
    ) -> TraversalResult:
        visited_nodes: list[GraphNode] = []
        visited_edges: list[GraphEdge] = []
        traversal_path: list[str] = []
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        visited.add(start)
        depth_reached = 0

        while queue:
            current, depth = queue.popleft()
            depth_reached = max(depth_reached, depth)
            node = self._graph.nodes.get(current)
            if node:
                visited_nodes.append(node)
                traversal_path.append(current)

            if depth >= max_depth:
                continue

            for edge in self._graph.adjacency.get(current, []):
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited and neighbor in self._graph.nodes:
                    visited.add(neighbor)
                    visited_edges.append(edge)
                    queue.append((neighbor, depth + 1))

        return TraversalResult(
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            traversal_path=traversal_path,
            depth_reached=depth_reached,
        )

    def _dfs_traverse(
        self,
        start: str,
        max_depth: int,
        node_filter: Any,
    ) -> TraversalResult:
        visited_nodes: list[GraphNode] = []
        visited_edges: list[GraphEdge] = []
        traversal_path: list[str] = []
        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(start, 0)]
        depth_reached = 0

        while stack:
            current, depth = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            depth_reached = max(depth_reached, depth)
            node = self._graph.nodes.get(current)
            if node:
                visited_nodes.append(node)
                traversal_path.append(current)

            if depth >= max_depth:
                continue

            for edge in reversed(self._graph.adjacency.get(current, [])):
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited and neighbor in self._graph.nodes:
                    visited_edges.append(edge)
                    stack.append((neighbor, depth + 1))

        return TraversalResult(
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            traversal_path=traversal_path,
            depth_reached=depth_reached,
        )

    def _random_walk(
        self,
        start: str,
        max_depth: int,
        node_filter: Any,
    ) -> TraversalResult:
        import random

        visited_nodes: list[GraphNode] = []
        visited_edges: list[GraphEdge] = []
        traversal_path: list[str] = []
        visited: set[str] = set()
        current = start
        depth_reached = 0

        for _ in range(max_depth):
            if current in visited:
                break
            visited.add(current)
            node = self._graph.nodes.get(current)
            if node:
                visited_nodes.append(node)
                traversal_path.append(current)

            neighbors = self._graph.adjacency.get(current, [])
            if not neighbors:
                break
            chosen = random.choice(neighbors)
            visited_edges.append(chosen)
            current = (
                chosen.target_id if chosen.source_id == current else chosen.source_id
            )
            depth_reached += 1

        return TraversalResult(
            visited_nodes=visited_nodes,
            visited_edges=visited_edges,
            traversal_path=traversal_path,
            depth_reached=depth_reached,
        )

    def extract_subgraph(
        self,
        root_node_id: str,
        max_depth: int = 3,
        max_nodes: int = 200,
    ) -> Subgraph:
        subgraph_nodes: dict[str, GraphNode] = {}
        subgraph_edges: dict[str, GraphEdge] = {}
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(root_node_id, 0)])
        visited.add(root_node_id)

        while queue and len(subgraph_nodes) < max_nodes:
            current, depth = queue.popleft()
            node = self._graph.nodes.get(current)
            if node:
                subgraph_nodes[current] = node

            if depth >= max_depth:
                continue

            for edge in self._graph.adjacency.get(current, []):
                neighbor = (
                    edge.target_id if edge.source_id == current else edge.source_id
                )
                if neighbor not in visited:
                    visited.add(neighbor)
                    subgraph_edges[edge.edge_id] = edge
                    queue.append((neighbor, depth + 1))

        sg = Subgraph(
            nodes=list(subgraph_nodes.values()),
            edges=list(subgraph_edges.values()),
            root_node_id=root_node_id,
        )
        sg.statistics.total_nodes = len(subgraph_nodes)
        sg.statistics.total_edges = len(subgraph_edges)
        return sg

    def find_communities(
        self,
        node_type: NodeType | None = None,
        min_size: int = 2,
    ) -> list[list[GraphNode]]:
        visited: set[str] = set()
        communities: list[list[GraphNode]] = []

        for nid in self._graph.nodes:
            if nid in visited:
                continue
            if node_type:
                node = self._graph.nodes[nid]
                if node.node_type != node_type:
                    continue

            component: list[GraphNode] = []
            stack = [nid]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                node = self._graph.nodes.get(current)
                if node:
                    if not node_type or node.node_type == node_type:
                        component.append(node)
                for edge in self._graph.adjacency.get(current, []):
                    neighbor = (
                        edge.target_id if edge.source_id == current else edge.source_id
                    )
                    if neighbor not in visited:
                        stack.append(neighbor)

            if len(component) >= min_size:
                communities.append(component)

        return communities

    def query(self, graph_query: GraphQuery) -> GraphQueryResult:
        start = time.monotonic()
        result = GraphQueryResult()

        qt = graph_query.query_type

        if qt == "find_node" and graph_query.node_id:
            node = self.find_node(graph_query.node_id)
            if node:
                result.nodes = [node]
        elif qt == "find_node" and graph_query.node_type:
            result.nodes = self.find_nodes_by_type(graph_query.node_type)
        elif qt == "find_neighbors" and graph_query.node_id:
            neighbors = self.find_neighbors(
                graph_query.node_id,
                max_depth=graph_query.max_depth,
                min_confidence=graph_query.min_confidence,
            )
            result.nodes = neighbors[: graph_query.limit]
        elif qt == "find_related" and graph_query.node_id:
            related = self.find_related(
                graph_query.node_id,
                max_results=graph_query.limit,
            )
            result.nodes = related
        elif qt == "find_shortest_path":
            sid = graph_query.node_id or ""
            target_type = graph_query.filters.get("target_type")
            if target_type:
                candidates = self.find_nodes_by_type(NodeType(target_type))
                if candidates:
                    target_id = candidates[0].node_id
                    path = self.find_shortest_path(
                        sid, target_id, graph_query.max_depth
                    )
                    if path:
                        result.nodes = path.nodes
                        result.edges = path.edges
        elif qt == "traverse" and graph_query.node_id:
            traversal = self.traverse(
                graph_query.node_id,
                strategy=graph_query.traversal_strategy,
                max_depth=graph_query.max_depth,
            )
            result.nodes = traversal.visited_nodes
            result.edges = traversal.visited_edges
        elif qt == "extract_subgraph" and graph_query.node_id:
            sg = self.extract_subgraph(
                graph_query.node_id,
                max_depth=graph_query.max_depth,
                max_nodes=graph_query.limit,
            )
            result.nodes = sg.nodes
            result.edges = sg.edges

        result.total_found = len(result.nodes)
        result.query_time_ms = round((time.monotonic() - start) * 1000, 1)
        return result

    def find_supporting_evidence(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=[RelationshipType.SUPPORTS, RelationshipType.REFERENCES],
        )

    def find_contradictions(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=[RelationshipType.CONTRADICTS],
        )

    def find_experiments(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=3,
            rel_types=[
                RelationshipType.VALIDATES,
                RelationshipType.USES,
                RelationshipType.EVALUATES,
            ],
        )

    def find_methods(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=[RelationshipType.PROPOSES, RelationshipType.EVALUATES],
        )

    def find_datasets(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=[RelationshipType.USES, RelationshipType.TRAINS_ON],
        )

    def find_benchmarks(self, node_id: str) -> list[GraphNode]:
        return self.find_neighbors(
            node_id,
            max_depth=2,
            rel_types=[RelationshipType.EVALUATES],
        )
