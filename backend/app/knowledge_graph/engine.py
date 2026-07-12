from __future__ import annotations

import time
from typing import Any

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.models import ExperimentPlan
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.confidence import ConfidencePropagator
from app.knowledge_graph.graph_builder import GraphBuilder
from app.knowledge_graph.models import (
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphOperation,
    GraphQuery,
    GraphQueryResult,
    GraphStatistics,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
    Subgraph,
    TraversalResult,
)
from app.knowledge_graph.node_builder import NodeBuilder
from app.knowledge_graph.provenance import ProvenanceTracker
from app.knowledge_graph.query_engine import GraphQueryEngine
from app.knowledge_graph.relationship_builder import RelationshipBuilder
from app.knowledge_graph.relationship_discovery import RelationshipDiscovery
from app.knowledge_graph.validator import GraphValidator
from app.methodology.models import MethodologyResult
from app.rag.llm import RAGLLMProvider
from app.rag.models import RetrievedEvidence
from app.summarization.models import SummaryResult

logger = get_logger("knowledge_graph.engine")
settings = get_knowledge_graph_settings()


class KnowledgeGraphEngine:
    def __init__(
        self,
        llm: RAGLLMProvider | None = None,
        node_builder: NodeBuilder | None = None,
        relationship_builder: RelationshipBuilder | None = None,
        graph_builder: GraphBuilder | None = None,
        query_engine: GraphQueryEngine | None = None,
        relationship_discovery: RelationshipDiscovery | None = None,
        confidence_propagator: ConfidencePropagator | None = None,
        provenance_tracker: ProvenanceTracker | None = None,
        validator: GraphValidator | None = None,
    ):
        self._llm = llm
        self._node_builder = node_builder or NodeBuilder()
        self._relationship_builder = relationship_builder or RelationshipBuilder()
        self._graph_builder = graph_builder or GraphBuilder()
        self._query_engine = query_engine
        self._relationship_discovery = relationship_discovery or RelationshipDiscovery(
            llm
        )
        self._confidence = confidence_propagator or ConfidencePropagator()
        self._provenance = provenance_tracker or ProvenanceTracker()
        self._validator = validator or GraphValidator()
        self._graph: KnowledgeGraph | None = None

    @property
    def graph(self) -> KnowledgeGraph | None:
        return self._graph

    async def build(
        self,
        memories: list[Any] | None = None,
        evidence: list[RetrievedEvidence] | None = None,
        summary: SummaryResult | None = None,
        analysis: AnalysisResult | None = None,
        methodology: MethodologyResult | None = None,
        experiment: ExperimentPlan | None = None,
        domain: str | None = None,
        query: str | None = None,
        project_id: str | None = None,
        graph_id: str | None = None,
    ) -> KnowledgeGraph:
        start = time.monotonic()

        graph = self._graph_builder.create_graph(graph_id)
        self._graph = graph

        all_nodes: list[GraphNode] = []

        if memories:
            memory_nodes = self._node_builder.build_memory_nodes(memories)
            all_nodes.extend(memory_nodes)

        if evidence:
            evidence_nodes = self._node_builder.build_evidence_nodes(evidence)
            all_nodes.extend(evidence_nodes)

        if summary:
            summary_nodes = self._node_builder.build_summary_nodes(summary)
            all_nodes.extend(summary_nodes)

        if analysis:
            analysis_nodes = self._node_builder.build_analysis_nodes(analysis)
            all_nodes.extend(analysis_nodes)

        if methodology:
            methodology_nodes = self._node_builder.build_methodology_nodes(methodology)
            all_nodes.extend(methodology_nodes)

        if experiment:
            experiment_nodes = self._node_builder.build_experiment_nodes(experiment)
            all_nodes.extend(experiment_nodes)

        if domain:
            domain_node = self._node_builder.build_domain_node(domain)
            all_nodes.append(domain_node)

        if query:
            query_node = self._node_builder.build_query_node(query)
            all_nodes.append(query_node)

        if project_id:
            project_node = self._node_builder.build_project_node(project_id)
            all_nodes.append(project_node)

        self._graph_builder.add_nodes_batch(graph, all_nodes, merge=True)

        edges: list[GraphEdge] = []

        if summary:
            summary_nodes_list = self._node_builder.build_summary_nodes(summary)
            summary_node = summary_nodes_list[0] if summary_nodes_list else None
            finding_nodes = [
                n for n in summary_nodes_list if n.node_type == NodeType.FINDING
            ]
            gap_nodes = [n for n in summary_nodes_list if n.node_type == NodeType.GAP]
            evidence_nodes_list = graph.get_nodes_by_type(NodeType.EVIDENCE)
            if summary_node:
                edges.extend(
                    self._relationship_builder.build_summary_relationships(
                        summary_node,
                        finding_nodes,
                        gap_nodes,
                        evidence_nodes_list,
                    )
                )

        if analysis:
            analysis_nodes_list = self._node_builder.build_analysis_nodes(analysis)
            analysis_node = analysis_nodes_list[0] if analysis_nodes_list else None
            consensus_nodes = [
                n for n in analysis_nodes_list if n.node_type == NodeType.CONSENSUS
            ]
            contra_nodes = [
                n for n in analysis_nodes_list if n.node_type == NodeType.CONTRADICTION
            ]
            trend_nodes = [
                n for n in analysis_nodes_list if n.node_type == NodeType.TREND
            ]
            limitation_nodes = [
                n for n in analysis_nodes_list if n.node_type == NodeType.LIMITATION
            ]
            recommendation_nodes = [
                n for n in analysis_nodes_list if n.node_type == NodeType.RECOMMENDATION
            ]
            all_finding_nodes = graph.get_nodes_by_type(NodeType.FINDING)
            if analysis_node:
                edges.extend(
                    self._relationship_builder.build_analysis_relationships(
                        analysis_node,
                        consensus_nodes,
                        contra_nodes,
                        trend_nodes,
                        limitation_nodes,
                        recommendation_nodes,
                        all_finding_nodes,
                    )
                )

        if methodology:
            methodology_nodes_list = self._node_builder.build_methodology_nodes(
                methodology
            )
            methodology_node = (
                methodology_nodes_list[0] if methodology_nodes_list else None
            )
            method_nodes = [
                n for n in methodology_nodes_list if n.node_type == NodeType.METHOD
            ]
            dataset_nodes = [
                n for n in methodology_nodes_list if n.node_type == NodeType.DATASET
            ]
            benchmark_nodes = [
                n for n in methodology_nodes_list if n.node_type == NodeType.BENCHMARK
            ]
            risk_nodes = [
                n for n in methodology_nodes_list if n.node_type == NodeType.RISK
            ]
            practice_nodes = [
                n
                for n in methodology_nodes_list
                if n.node_type == NodeType.BEST_PRACTICE
            ]
            if methodology_node:
                edges.extend(
                    self._relationship_builder.build_methodology_relationships(
                        methodology_node,
                        method_nodes,
                        dataset_nodes,
                        benchmark_nodes,
                        risk_nodes,
                        practice_nodes,
                    )
                )

        if experiment:
            experiment_nodes_list = self._node_builder.build_experiment_nodes(
                experiment
            )
            experiment_node = (
                experiment_nodes_list[0] if experiment_nodes_list else None
            )
            hypothesis_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.HYPOTHESIS
            ]
            variable_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.VARIABLE
            ]
            baseline_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.BASELINE
            ]
            risk_nodes_e = [
                n for n in experiment_nodes_list if n.node_type == NodeType.RISK
            ]
            phase_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.PHASE
            ]
            step_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.STEP
            ]
            objective_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.OBJECTIVE
            ]
            outcome_nodes = [
                n for n in experiment_nodes_list if n.node_type == NodeType.OUTCOME
            ]
            all_method_nodes = graph.get_nodes_by_type(NodeType.METHOD)
            all_dataset_nodes = graph.get_nodes_by_type(NodeType.DATASET)
            if experiment_node:
                edges.extend(
                    self._relationship_builder.build_experiment_relationships(
                        experiment_node,
                        hypothesis_nodes,
                        variable_nodes,
                        baseline_nodes,
                        risk_nodes_e,
                        phase_nodes,
                        step_nodes,
                        objective_nodes,
                        outcome_nodes,
                        all_method_nodes,
                        all_dataset_nodes,
                    )
                )

        if domain and graph.get_nodes_by_type(NodeType.DATASET):
            domain_nodes = graph.get_nodes_by_type(NodeType.DOMAIN)
            dataset_nodes_all = graph.get_nodes_by_type(NodeType.DATASET)
            method_nodes_all = graph.get_nodes_by_type(NodeType.METHOD)
            if domain_nodes:
                edges.extend(
                    self._relationship_builder.build_domain_relationships(
                        domain_nodes[0],
                        dataset_nodes_all,
                        method_nodes_all,
                        [],
                    )
                )

        self._graph_builder.add_edges_batch(graph, edges, merge=True)

        if settings.graph_enable_inference:
            discovered = await self._relationship_discovery.discover(
                graph,
                analysis,
                methodology,
                experiment,
            )
            self._graph_builder.add_edges_batch(graph, discovered, merge=True)

        self._confidence.propagate(graph)

        if settings.graph_enable_provenance:
            self._provenance.annotate_graph(graph, "knowledge_graph_engine")

        stats = self._graph_builder.compute_statistics(graph)
        graph.statistics = stats

        validation = self._validator.validate(graph)
        graph.validation = validation

        duration = time.monotonic() - start
        graph.metadata = GraphMetadata(
            updated_at=graph.metadata.created_at,
            version="1.0",
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            last_operation=GraphOperation.CREATE,
            duration_ms=round(duration * 1000, 1),
            validation_passed=validation.is_valid,
            validation_errors=validation.errors,
        )

        logger.info(
            "knowledge graph build complete",
            extra={
                "graph_id": graph.graph_id,
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "valid": validation.is_valid,
                "duration_ms": graph.metadata.duration_ms,
            },
        )

        return graph

    def update(
        self,
        new_nodes: list[GraphNode] | None = None,
        new_edges: list[GraphEdge] | None = None,
        propagate_confidence: bool = True,
    ) -> KnowledgeGraph | None:
        if not self._graph:
            logger.warning("no graph to update")
            return None

        if new_nodes:
            self._graph_builder.add_nodes_batch(self._graph, new_nodes, merge=True)
        if new_edges:
            self._graph_builder.add_edges_batch(self._graph, new_edges, merge=True)

        if propagate_confidence:
            self._confidence.propagate(self._graph)

        self._graph.statistics = self._graph_builder.compute_statistics(self._graph)
        self._graph.metadata.last_operation = GraphOperation.UPDATE
        self._graph.metadata.node_count = len(self._graph.nodes)
        self._graph.metadata.edge_count = len(self._graph.edges)

        logger.info(
            "graph updated",
            extra={
                "nodes_added": len(new_nodes) if new_nodes else 0,
                "edges_added": len(new_edges) if new_edges else 0,
                "total_nodes": len(self._graph.nodes),
                "total_edges": len(self._graph.edges),
            },
        )
        return self._graph

    def query(self, graph_query: GraphQuery) -> GraphQueryResult:
        if not self._graph:
            return GraphQueryResult()
        engine = self._get_query_engine()
        return engine.query(graph_query)

    def find_node(self, node_id: str) -> GraphNode | None:
        if not self._graph:
            return None
        return self._graph.nodes.get(node_id)

    def find_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        if not self._graph:
            return []
        return self._graph.get_nodes_by_type(node_type)

    def find_neighbors(
        self,
        node_id: str,
        max_depth: int = 1,
        rel_types: list[RelationshipType] | None = None,
    ) -> list[GraphNode]:
        if not self._graph:
            return []
        engine = self._get_query_engine()
        return engine.find_neighbors(node_id, max_depth, rel_types)

    def find_shortest_path(self, source: str, target: str) -> Any:
        if not self._graph:
            return None
        engine = self._get_query_engine()
        return engine.find_shortest_path(source, target)

    def extract_subgraph(
        self,
        root_id: str,
        max_depth: int = 3,
    ) -> Subgraph:
        if not self._graph:
            return Subgraph()
        engine = self._get_query_engine()
        return engine.extract_subgraph(
            root_id, max_depth, settings.graph_max_subgraph_size
        )

    def traverse(
        self,
        start_id: str,
        max_depth: int = 5,
    ) -> TraversalResult:
        if not self._graph:
            return TraversalResult()
        engine = self._get_query_engine()
        return engine.traverse(start_id, max_depth=max_depth)

    def find_communities(
        self,
        node_type: NodeType | None = None,
        min_size: int = 2,
    ) -> list[list[GraphNode]]:
        if not self._graph:
            return []
        engine = self._get_query_engine()
        return engine.find_communities(node_type, min_size)

    def get_statistics(self) -> GraphStatistics:
        if self._graph:
            return self._graph_builder.compute_statistics(self._graph)
        return GraphStatistics()

    def get_graph(self) -> KnowledgeGraph | None:
        return self._graph

    def _get_query_engine(self) -> GraphQueryEngine:
        if not self._graph:
            self._graph = KnowledgeGraph()
        self._query_engine = GraphQueryEngine(self._graph)
        return self._query_engine
