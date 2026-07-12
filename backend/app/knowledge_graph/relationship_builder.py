from __future__ import annotations

import uuid
from typing import Any

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.models import ExperimentPlan
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    EdgeMetadata,
    GraphEdge,
    GraphNode,
    GraphRelationship,
    KnowledgeGraph,
    NodeType,
    RelationshipType,
)
from app.methodology.models import MethodologyResult
from app.summarization.models import SummaryResult

logger = get_logger("knowledge_graph.relationship_builder")
settings = get_knowledge_graph_settings()


def _edge_id(source_id: str, target_id: str, rel_type: RelationshipType) -> str:
    raw = f"{source_id}:{rel_type.value}:{target_id}"
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class RelationshipBuilder:
    def build_memory_relationships(
        self,
        memory_nodes: list[GraphNode],
        graph: KnowledgeGraph,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for mem_node in memory_nodes:
            props = mem_node.metadata.properties
            refs = props.get("references", [])
            if isinstance(refs, list):
                for ref in refs:
                    target_id = _stable_ref_id(ref)
                    if target_id in graph.nodes:
                        edge = GraphEdge(
                            edge_id=_edge_id(mem_node.node_id, target_id, RelationshipType.REFERENCES),
                            source_id=mem_node.node_id,
                            target_id=target_id,
                            relationship_type=RelationshipType.REFERENCES,
                            label=f"Memory references {ref}",
                            metadata=EdgeMetadata(
                                confidence=mem_node.metadata.confidence,
                                weight=0.7,
                                source="memory_relationship",
                                reason="Memory contains reference to entity",
                            ),
                        )
                        edges.append(edge)
        logger.debug("built memory relationships", extra={"count": len(edges)})
        return edges

    def build_evidence_relationships(
        self,
        evidence_node: GraphNode,
        paper_nodes: dict[str, GraphNode],
        method_nodes: dict[str, GraphNode],
        dataset_nodes: dict[str, GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        props = evidence_node.metadata.properties
        source_type = props.get("source_type", "")

        if source_type == "paper" or source_type == "arxiv":
            for pid, pnode in paper_nodes.items():
                edge = GraphEdge(
                    edge_id=_edge_id(evidence_node.node_id, pid, RelationshipType.REFERENCES),
                    source_id=evidence_node.node_id,
                    target_id=pid,
                    relationship_type=RelationshipType.REFERENCES,
                    label=f"Evidence references paper",
                    metadata=EdgeMetadata(
                        confidence=evidence_node.metadata.confidence,
                        weight=0.8,
                        source="evidence_source",
                        reason="Evidence extracted from paper",
                    ),
                )
                edges.append(edge)

        for mid, mnode in method_nodes.items():
            if mid in evidence_node.description or mid in str(props):
                edge = GraphEdge(
                    edge_id=_edge_id(evidence_node.node_id, mid, RelationshipType.USES),
                    source_id=evidence_node.node_id,
                    target_id=mid,
                    relationship_type=RelationshipType.USES,
                    label=f"Evidence mentions method",
                    metadata=EdgeMetadata(
                        confidence=0.5, weight=0.5,
                        source="evidence_content",
                        reason="Method mentioned in evidence",
                    ),
                )
                edges.append(edge)
        logger.debug("built evidence relationships", extra={"count": len(edges)})
        return edges

    def build_summary_relationships(
        self,
        summary_node: GraphNode,
        finding_nodes: list[GraphNode],
        gap_nodes: list[GraphNode],
        evidence_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for fn in finding_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(summary_node.node_id, fn.node_id, RelationshipType.CONTAINS),
                source_id=summary_node.node_id,
                target_id=fn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Summary contains finding",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="summary_structure",
                                      reason="Finding extracted during summarization"),
            ))
        for gn in gap_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(summary_node.node_id, gn.node_id, RelationshipType.IDENTIFIES),
                source_id=summary_node.node_id,
                target_id=gn.node_id,
                relationship_type=RelationshipType.IDENTIFIES,
                label="Summary identifies gap",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="summary_structure",
                                      reason="Gap identified during summarization"),
            ))
        for fn in finding_nodes:
            for en in evidence_nodes:
                edges.append(GraphEdge(
                    edge_id=_edge_id(fn.node_id, en.node_id, RelationshipType.REFERENCES),
                    source_id=fn.node_id,
                    target_id=en.node_id,
                    relationship_type=RelationshipType.REFERENCES,
                    label="Finding references evidence",
                    metadata=EdgeMetadata(confidence=0.7, weight=0.6, source="finding_evidence",
                                          reason="Finding derived from evidence"),
                ))
        logger.debug("built summary relationships", extra={"count": len(edges)})
        return edges

    def build_analysis_relationships(
        self,
        analysis_node: GraphNode,
        consensus_nodes: list[GraphNode],
        contradiction_nodes: list[GraphNode],
        trend_nodes: list[GraphNode],
        limitation_nodes: list[GraphNode],
        recommendation_nodes: list[GraphNode],
        finding_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for cn in consensus_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(analysis_node.node_id, cn.node_id, RelationshipType.CONTAINS),
                source_id=analysis_node.node_id, target_id=cn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Analysis contains consensus",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="analysis_structure",
                                      reason="Consensus derived during analysis"),
            ))
        for cn in contradiction_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(analysis_node.node_id, cn.node_id, RelationshipType.CONTAINS),
                source_id=analysis_node.node_id, target_id=cn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Analysis contains contradiction",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="analysis_structure",
                                      reason="Contradiction detected during analysis"),
            ))
        for tn in trend_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(analysis_node.node_id, tn.node_id, RelationshipType.IDENTIFIES),
                source_id=analysis_node.node_id, target_id=tn.node_id,
                relationship_type=RelationshipType.IDENTIFIES,
                label="Analysis identifies trend",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="analysis_structure",
                                      reason="Trend identified during analysis"),
            ))
        for ln in limitation_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(analysis_node.node_id, ln.node_id, RelationshipType.IDENTIFIES),
                source_id=analysis_node.node_id, target_id=ln.node_id,
                relationship_type=RelationshipType.IDENTIFIES,
                label="Analysis identifies limitation",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="analysis_structure",
                                      reason="Limitation identified during analysis"),
            ))
        for rn in recommendation_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(analysis_node.node_id, rn.node_id, RelationshipType.GENERATES),
                source_id=analysis_node.node_id, target_id=rn.node_id,
                relationship_type=RelationshipType.GENERATES,
                label="Analysis generates recommendation",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="analysis_structure",
                                      reason="Recommendation generated during analysis"),
            ))
        for rn in recommendation_nodes:
            for fn in finding_nodes:
                edges.append(GraphEdge(
                    edge_id=_edge_id(rn.node_id, fn.node_id, RelationshipType.DERIVED_FROM),
                    source_id=rn.node_id, target_id=fn.node_id,
                    relationship_type=RelationshipType.DERIVED_FROM,
                    label="Recommendation derived from finding",
                    metadata=EdgeMetadata(confidence=0.6, weight=0.5, source="analysis_inference",
                                          reason="Recommendation based on findings"),
                ))
        logger.debug("built analysis relationships", extra={"count": len(edges)})
        return edges

    def build_methodology_relationships(
        self,
        methodology_node: GraphNode,
        method_nodes: list[GraphNode],
        dataset_nodes: list[GraphNode],
        benchmark_nodes: list[GraphNode],
        risk_nodes: list[GraphNode],
        practice_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for mn in method_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(methodology_node.node_id, mn.node_id, RelationshipType.CONTAINS),
                source_id=methodology_node.node_id, target_id=mn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Methodology contains method",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="methodology_structure",
                                      reason="Method selected during methodology analysis"),
            ))
            for dn in dataset_nodes:
                edges.append(GraphEdge(
                    edge_id=_edge_id(mn.node_id, dn.node_id, RelationshipType.USES),
                    source_id=mn.node_id, target_id=dn.node_id,
                    relationship_type=RelationshipType.USES,
                    label=f"Method uses dataset",
                    metadata=EdgeMetadata(confidence=0.7, weight=0.6, source="methodology_inference",
                                          reason="Method recommended with dataset"),
                ))
        for bn in benchmark_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(methodology_node.node_id, bn.node_id, RelationshipType.CONTAINS),
                source_id=methodology_node.node_id, target_id=bn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Methodology contains benchmark",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="methodology_structure",
                                      reason="Benchmark recommended during methodology analysis"),
            ))
            for mn in method_nodes:
                edges.append(GraphEdge(
                    edge_id=_edge_id(bn.node_id, mn.node_id, RelationshipType.EVALUATES),
                    source_id=bn.node_id, target_id=mn.node_id,
                    relationship_type=RelationshipType.EVALUATES,
                    label=f"Benchmark evaluates method",
                    metadata=EdgeMetadata(confidence=0.6, weight=0.5, source="methodology_inference",
                                          reason="Benchmark associated with method"),
                ))
        for rn in risk_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(methodology_node.node_id, rn.node_id, RelationshipType.IDENTIFIES),
                source_id=methodology_node.node_id, target_id=rn.node_id,
                relationship_type=RelationshipType.IDENTIFIES,
                label="Methodology identifies risk",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="methodology_structure",
                                      reason="Risk identified during methodology analysis"),
            ))
        for pn in practice_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(methodology_node.node_id, pn.node_id, RelationshipType.RECOMMENDS),
                source_id=methodology_node.node_id, target_id=pn.node_id,
                relationship_type=RelationshipType.RECOMMENDS,
                label="Methodology recommends best practice",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="methodology_structure",
                                      reason="Best practice recommended during methodology analysis"),
            ))
        for dn in dataset_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(methodology_node.node_id, dn.node_id, RelationshipType.CONTAINS),
                source_id=methodology_node.node_id, target_id=dn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Methodology contains dataset",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="methodology_structure",
                                      reason="Dataset recommended during methodology analysis"),
            ))
        logger.debug("built methodology relationships", extra={"count": len(edges)})
        return edges

    def build_experiment_relationships(
        self,
        experiment_node: GraphNode,
        hypothesis_nodes: list[GraphNode],
        variable_nodes: list[GraphNode],
        baseline_nodes: list[GraphNode],
        risk_nodes: list[GraphNode],
        phase_nodes: list[GraphNode],
        step_nodes: list[GraphNode],
        objective_nodes: list[GraphNode],
        outcome_nodes: list[GraphNode],
        method_nodes: list[GraphNode],
        dataset_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for hn in hypothesis_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, hn.node_id, RelationshipType.CONTAINS),
                source_id=experiment_node.node_id, target_id=hn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Experiment contains hypothesis",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="experiment_structure",
                                      reason="Hypothesis generated for experiment"),
            ))
        for vn in variable_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, vn.node_id, RelationshipType.CONTAINS),
                source_id=experiment_node.node_id, target_id=vn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Experiment contains variable",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="experiment_structure",
                                      reason="Variable defined for experiment"),
            ))
        for bn in baseline_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, bn.node_id, RelationshipType.COMPARES_TO),
                source_id=experiment_node.node_id, target_id=bn.node_id,
                relationship_type=RelationshipType.COMPARES_TO,
                label="Experiment compares to baseline",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="experiment_structure",
                                      reason="Baseline defined for comparison"),
            ))
        for rn in risk_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, rn.node_id, RelationshipType.IDENTIFIES),
                source_id=experiment_node.node_id, target_id=rn.node_id,
                relationship_type=RelationshipType.IDENTIFIES,
                label="Experiment identifies risk",
                metadata=EdgeMetadata(confidence=0.8, weight=0.7, source="experiment_structure",
                                      reason="Risk identified for experiment"),
            ))
        for pn in phase_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, pn.node_id, RelationshipType.CONTAINS),
                source_id=experiment_node.node_id, target_id=pn.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Experiment contains phase",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="experiment_structure",
                                      reason="Phase defined in experiment plan"),
            ))
            for sn in step_nodes:
                if sn.metadata.properties.get("parent_phase") == pn.node_id:
                    edges.append(GraphEdge(
                        edge_id=_edge_id(pn.node_id, sn.node_id, RelationshipType.CONTAINS),
                        source_id=pn.node_id, target_id=sn.node_id,
                        relationship_type=RelationshipType.CONTAINS,
                        label="Phase contains step",
                        metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="experiment_structure",
                                              reason="Step defined in phase"),
                    ))
        for on in objective_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, on.node_id, RelationshipType.CONTAINS),
                source_id=experiment_node.node_id, target_id=on.node_id,
                relationship_type=RelationshipType.CONTAINS,
                label="Experiment contains objective",
                metadata=EdgeMetadata(confidence=0.9, weight=0.8, source="experiment_structure",
                                      reason="Objective defined for experiment"),
            ))
        for ocn in outcome_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, ocn.node_id, RelationshipType.LEADS_TO),
                source_id=experiment_node.node_id, target_id=ocn.node_id,
                relationship_type=RelationshipType.LEADS_TO,
                label="Experiment leads to outcome",
                metadata=EdgeMetadata(confidence=0.7, weight=0.6, source="experiment_structure",
                                      reason="Expected outcome of experiment"),
            ))
        for hn in hypothesis_nodes:
            for mn in method_nodes:
                edges.append(GraphEdge(
                    edge_id=_edge_id(hn.node_id, mn.node_id, RelationshipType.VALIDATES),
                    source_id=hn.node_id, target_id=mn.node_id,
                    relationship_type=RelationshipType.VALIDATES,
                    label="Hypothesis validates method",
                    metadata=EdgeMetadata(confidence=0.5, weight=0.4, source="experiment_inference",
                                          reason="Hypothesis tests method effectiveness"),
                ))
        for dn in dataset_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(experiment_node.node_id, dn.node_id, RelationshipType.USES),
                source_id=experiment_node.node_id, target_id=dn.node_id,
                relationship_type=RelationshipType.USES,
                label="Experiment uses dataset",
                metadata=EdgeMetadata(confidence=0.7, weight=0.6, source="experiment_inference",
                                      reason="Dataset used in experiment"),
            ))
        logger.debug("built experiment relationships", extra={"count": len(edges)})
        return edges

    def build_domain_relationships(
        self,
        domain_node: GraphNode,
        dataset_nodes: list[GraphNode],
        method_nodes: list[GraphNode],
        paper_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for dn in dataset_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(dn.node_id, domain_node.node_id, RelationshipType.BELONGS_TO),
                source_id=dn.node_id, target_id=domain_node.node_id,
                relationship_type=RelationshipType.BELONGS_TO,
                label="Dataset belongs to domain",
                metadata=EdgeMetadata(confidence=0.6, weight=0.5, source="domain_inference",
                                      reason="Dataset relevant to domain"),
            ))
        for mn in method_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(mn.node_id, domain_node.node_id, RelationshipType.BELONGS_TO),
                source_id=mn.node_id, target_id=domain_node.node_id,
                relationship_type=RelationshipType.BELONGS_TO,
                label="Method belongs to domain",
                metadata=EdgeMetadata(confidence=0.6, weight=0.5, source="domain_inference",
                                      reason="Method relevant to domain"),
            ))
        logger.debug("built domain relationships", extra={"count": len(edges)})
        return edges

    def build_author_paper_relationships(
        self,
        author_node: GraphNode,
        paper_nodes: list[GraphNode],
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for pn in paper_nodes:
            edges.append(GraphEdge(
                edge_id=_edge_id(author_node.node_id, pn.node_id, RelationshipType.WROTE),
                source_id=author_node.node_id, target_id=pn.node_id,
                relationship_type=RelationshipType.WROTE,
                label=f"Author wrote paper",
                metadata=EdgeMetadata(confidence=0.9, weight=0.9, source="paper_metadata",
                                      reason="Author listed on paper"),
            ))
        return edges

    def build_sequential_relationships(
        self,
        node_a: GraphNode,
        node_b: GraphNode,
        rel_type: RelationshipType,
        confidence: float = 0.8,
        reason: str = "",
    ) -> GraphEdge | None:
        if node_a.node_id == node_b.node_id:
            return None
        return GraphEdge(
            edge_id=_edge_id(node_a.node_id, node_b.node_id, rel_type),
            source_id=node_a.node_id,
            target_id=node_b.node_id,
            relationship_type=rel_type,
            label=f"{node_a.node_type.value} {rel_type.value} {node_b.node_type.value}",
            metadata=EdgeMetadata(
                confidence=confidence,
                weight=confidence,
                source="sequential_build",
                reason=reason or f"Relationship between {node_a.node_type.value} and {node_b.node_type.value}",
            ),
        )


def _stable_ref_id(ref: str) -> str:
    import hashlib
    return hashlib.sha256(ref.encode("utf-8")).hexdigest()[:32]
