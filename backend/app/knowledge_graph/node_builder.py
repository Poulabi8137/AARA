from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from app.analysis.models import AnalysisResult
from app.core.logging import get_logger
from app.experiments.models import ExperimentPlan, ExperimentHypothesis
from app.knowledge_graph.config import get_knowledge_graph_settings
from app.knowledge_graph.models import (
    GraphNode,
    NodeMetadata,
    NodeType,
)
from app.methodology.models import MethodologyResult, ResearchMethod
from app.rag.models import RetrievedEvidence
from app.services.research_memory.manager import ResearchMemoryManager
from app.summarization.models import SummaryResult

logger = get_logger("knowledge_graph.node_builder")
settings = get_knowledge_graph_settings()


def _stable_id(prefix: str, content: str) -> str:
    raw = f"{prefix}:{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class NodeBuilder:
    def build_memory_nodes(
        self, memories: list[Any],
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        for mem in memories:
            mem_id = getattr(mem, "memory_id", None) or str(uuid.uuid4())
            content = getattr(mem, "content", "") or getattr(mem, "text", "")
            ntype = getattr(mem, "memory_type", None)
            node_type = NodeType.MEMORY
            if ntype:
                try:
                    node_type = NodeType(ntype)
                except ValueError:
                    pass
            node_id = _stable_id("memory", mem_id)
            nodes.append(GraphNode(
                node_id=node_id,
                node_type=node_type,
                label=f"Memory: {content[:80]}",
                description=content[:500],
                metadata=NodeMetadata(
                    source_type="research_memory",
                    source_id=mem_id,
                    confidence=getattr(mem, "confidence", 1.0),
                    provenance=[f"memory:{mem_id}"],
                    tags=[node_type.value],
                    properties={
                        "memory_type": ntype or "unknown",
                        "importance": getattr(mem, "importance", 0.5),
                    },
                ),
            ))
        logger.debug("built memory nodes", extra={"count": len(nodes)})
        return nodes

    def build_evidence_nodes(
        self, evidence: list[RetrievedEvidence],
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        for i, ev in enumerate(evidence):
            eid = getattr(ev, "id", None) or getattr(ev, "evidence_id", None) or f"ev_{i}"
            content = getattr(ev, "content", "") or getattr(ev, "text", "")
            source_type = getattr(ev, "source_type", None)
            st = source_type.value if hasattr(source_type, "value") else str(source_type or "unknown")
            node_id = _stable_id("evidence", eid)
            nodes.append(GraphNode(
                node_id=node_id,
                node_type=NodeType.EVIDENCE,
                label=f"Evidence: {content[:80]}",
                description=content[:500],
                metadata=NodeMetadata(
                    source_type=st,
                    source_id=eid,
                    confidence=getattr(ev, "confidence", 0.5),
                    provenance=[f"evidence:{eid}"],
                    tags=["evidence", st],
                    properties={
                        "source_type": st,
                        "relevance": getattr(ev, "relevance_score", 0.0),
                    },
                ),
            ))
        logger.debug("built evidence nodes", extra={"count": len(nodes)})
        return nodes

    def build_summary_nodes(
        self, summary: SummaryResult,
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        summary_id = _stable_id("summary", summary.summary[:100] if summary.summary else str(id(summary)))
        nodes.append(GraphNode(
            node_id=summary_id,
            node_type=NodeType.SUMMARY,
            label=f"Summary: {summary.summary[:80]}" if summary.summary else "Research Summary",
            description=(summary.summary or "")[:500],
            metadata=NodeMetadata(
                source_type="summarization",
                source_id=summary_id,
                confidence=summary.statistics.overall_confidence if summary.statistics else 0.5,
                provenance=[],
                tags=["summary"],
                properties={
                    "level": getattr(summary.metadata, "level", "standard"),
                    "sections": len(summary.sections),
                    "findings": len(summary.findings),
                    "gaps": len(summary.gaps),
                },
            ),
        ))
        for f in summary.findings:
            finding_id = _stable_id("finding", f.statement[:100])
            nodes.append(GraphNode(
                node_id=finding_id,
                node_type=NodeType.FINDING,
                label=f"Finding: {f.statement[:80]}",
                description=f.statement[:500],
                metadata=NodeMetadata(
                    source_type="summarization",
                    source_id=finding_id,
                    confidence=f.confidence,
                    provenance=[f"finding:{finding_id}"],
                    tags=["finding", f.category],
                    properties={"category": f.category, "citations": list(f.citations)},
                ),
            ))
        for g in summary.gaps:
            gap_id = _stable_id("gap", g.gap[:100])
            nodes.append(GraphNode(
                node_id=gap_id,
                node_type=NodeType.GAP,
                label=f"Gap: {g.gap[:80]}",
                description=g.gap[:500],
                metadata=NodeMetadata(
                    source_type="summarization",
                    source_id=gap_id,
                    confidence=g.confidence if hasattr(g, "confidence") else 0.5,
                    provenance=[f"gap:{gap_id}"],
                    tags=["gap", g.gap_type if hasattr(g, "gap_type") else "unknown"],
                    properties={"gap_type": g.gap_type if hasattr(g, "gap_type") else "unknown"},
                ),
            ))
        logger.debug("built summary nodes", extra={"count": len(nodes)})
        return nodes

    def build_analysis_nodes(
        self, analysis: AnalysisResult,
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        analysis_id = _stable_id("analysis", str(id(analysis)))

        nodes.append(GraphNode(
            node_id=analysis_id,
            node_type=NodeType.ANALYSIS,
            label="Research Analysis",
            description=f"Analysis with {len(analysis.consensus)} consensus, "
                        f"{len(analysis.contradictions)} contradictions, "
                        f"{len(analysis.trends)} trends",
            metadata=NodeMetadata(
                source_type="analysis",
                source_id=analysis_id,
                confidence=analysis.confidence.overall,
                provenance=[],
                tags=["analysis"],
                properties={
                    "consensus_count": len(analysis.consensus),
                    "contradiction_count": len(analysis.contradictions),
                    "trend_count": len(analysis.trends),
                    "limitation_count": len(analysis.limitations),
                    "recommendation_count": len(analysis.recommendations),
                },
            ),
        ))
        for c in analysis.consensus:
            cid = _stable_id("consensus", c.statement[:100])
            nodes.append(GraphNode(
                node_id=cid, node_type=NodeType.CONSENSUS,
                label=f"Consensus: {c.statement[:80]}",
                description=c.statement[:500],
                metadata=NodeMetadata(
                    source_type="analysis", source_id=cid,
                    confidence=c.confidence, provenance=[f"consensus:{cid}"],
                    tags=["consensus", c.category],
                    properties={"category": c.category, "evidence_count": c.evidence_count},
                ),
            ))
        for ct in analysis.contradictions:
            ctid = _stable_id("contradiction", ct.statement[:100])
            nodes.append(GraphNode(
                node_id=ctid, node_type=NodeType.CONTRADICTION,
                label=f"Contradiction: {ct.statement[:80]}",
                description=ct.statement[:500],
                metadata=NodeMetadata(
                    source_type="analysis", source_id=ctid,
                    confidence=0.5, provenance=[f"contradiction:{ctid}"],
                    tags=["contradiction"],
                    properties={"severity": ct.severity, "sides": len(ct.conflicting_sides)},
                ),
            ))
        for t in analysis.trends:
            tid = _stable_id("trend", t.trend[:100])
            nodes.append(GraphNode(
                node_id=tid, node_type=NodeType.TREND,
                label=f"Trend: {t.trend[:80]}",
                description=t.trend[:500],
                metadata=NodeMetadata(
                    source_type="analysis", source_id=tid,
                    confidence=t.confidence, provenance=[f"trend:{tid}"],
                    tags=["trend"],
                    properties={"direction": t.direction},
                ),
            ))
        for lim in analysis.limitations:
            lid = _stable_id("limitation", lim.limitation[:100])
            nodes.append(GraphNode(
                node_id=lid, node_type=NodeType.LIMITATION,
                label=f"Limitation: {lim.limitation[:80]}",
                description=lim.limitation[:500],
                metadata=NodeMetadata(
                    source_type="analysis", source_id=lid,
                    confidence=0.5, provenance=[f"limitation:{lid}"],
                    tags=["limitation", lim.category],
                    properties={"category": lim.category, "severity": lim.severity},
                ),
            ))
        for r in analysis.recommendations:
            rid = _stable_id("recommendation", r.recommendation[:100])
            nodes.append(GraphNode(
                node_id=rid, node_type=NodeType.RECOMMENDATION,
                label=f"Recommendation: {r.recommendation[:80]}",
                description=r.recommendation[:500],
                metadata=NodeMetadata(
                    source_type="analysis", source_id=rid,
                    confidence=r.confidence, provenance=[f"recommendation:{rid}"],
                    tags=["recommendation", r.category],
                    properties={"category": r.category, "priority": r.priority},
                ),
            ))
        logger.debug("built analysis nodes", extra={"count": len(nodes)})
        return nodes

    def build_methodology_nodes(
        self, methodology: MethodologyResult,
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        meth_id = _stable_id("methodology", str(id(methodology)))
        nodes.append(GraphNode(
            node_id=meth_id, node_type=NodeType.METHODOLOGY,
            label="Research Methodology",
            description=f"Methodology with {len(methodology.methods)} methods, "
                        f"{len(methodology.datasets)} datasets",
            metadata=NodeMetadata(
                source_type="methodology",
                source_id=meth_id,
                confidence=methodology.statistics.overall_confidence,
                provenance=[],
                tags=["methodology"],
                properties={
                    "method_count": len(methodology.methods),
                    "dataset_count": len(methodology.datasets),
                    "benchmark_count": len(methodology.benchmarks),
                    "risk_count": len(methodology.risks),
                },
            ),
        ))
        for m in methodology.methods:
            mid = _stable_id("method", m.method)
            nodes.append(GraphNode(
                node_id=mid, node_type=NodeType.METHOD,
                label=f"Method: {m.method}",
                description=m.rationale[:500] or m.method,
                metadata=NodeMetadata(
                    source_type="methodology", source_id=mid,
                    confidence=m.confidence, provenance=[f"method:{mid}"],
                    tags=["method"],
                    properties={"method": m.method, "requirements": m.requirements},
                ),
            ))
        for d in methodology.datasets:
            did = _stable_id("dataset", d.dataset_name)
            nodes.append(GraphNode(
                node_id=did, node_type=NodeType.DATASET,
                label=f"Dataset: {d.dataset_name}",
                description=d.rationale[:500] or d.dataset_name,
                metadata=NodeMetadata(
                    source_type="methodology", source_id=did,
                    confidence=d.confidence, provenance=[f"dataset:{did}"],
                    tags=["dataset"],
                    properties={
                        "dataset_name": d.dataset_name,
                        "domain_relevance": d.domain_relevance,
                        "size_category": d.size_category,
                        "quality": d.quality,
                        "licensing": d.licensing,
                        "availability": d.availability,
                        "maturity": d.maturity,
                    },
                ),
            ))
        for b in methodology.benchmarks:
            bid = _stable_id("benchmark", b.benchmark_name)
            nodes.append(GraphNode(
                node_id=bid, node_type=NodeType.BENCHMARK,
                label=f"Benchmark: {b.benchmark_name}",
                description=b.rationale[:500] or b.benchmark_name,
                metadata=NodeMetadata(
                    source_type="methodology", source_id=bid,
                    confidence=b.confidence, provenance=[f"benchmark:{bid}"],
                    tags=["benchmark"],
                    properties={
                        "benchmark_name": b.benchmark_name,
                        "category": b.category,
                        "relevance": b.relevance,
                    },
                ),
            ))
        for r in methodology.risks:
            rid = _stable_id("risk", r.risk[:100])
            nodes.append(GraphNode(
                node_id=rid, node_type=NodeType.RISK,
                label=f"Risk: {r.risk[:80]}",
                description=r.risk[:500],
                metadata=NodeMetadata(
                    source_type="methodology", source_id=rid,
                    confidence=r.confidence, provenance=[f"risk:{rid}"],
                    tags=["risk", r.category],
                    properties={
                        "category": r.category,
                        "severity": r.severity,
                        "mitigation": r.mitigation,
                    },
                ),
            ))
        for bp in methodology.best_practices:
            bpid = _stable_id("best_practice", bp.practice[:100])
            nodes.append(GraphNode(
                node_id=bpid, node_type=NodeType.BEST_PRACTICE,
                label=f"Best Practice: {bp.practice[:80]}",
                description=bp.practice[:500],
                metadata=NodeMetadata(
                    source_type="methodology", source_id=bpid,
                    confidence=0.7, provenance=[f"best_practice:{bpid}"],
                    tags=["best_practice", bp.category],
                    properties={"category": bp.category, "source": bp.source},
                ),
            ))
        logger.debug("built methodology nodes", extra={"count": len(nodes)})
        return nodes

    def build_experiment_nodes(
        self, experiment: ExperimentPlan,
    ) -> list[GraphNode]:
        nodes: list[GraphNode] = []
        exp_id = _stable_id("experiment", str(id(experiment)))
        nodes.append(GraphNode(
            node_id=exp_id, node_type=NodeType.EXPERIMENT,
            label=f"Experiment: {experiment.query[:80]}" if experiment.query else "Experiment Plan",
            description=f"Experiment with {len(experiment.phases)} phases, "
                        f"{len(experiment.hypotheses)} hypotheses",
            metadata=NodeMetadata(
                source_type="experiment_planner",
                source_id=exp_id,
                confidence=experiment.statistics.overall_confidence,
                provenance=[],
                tags=["experiment"],
                properties={
                    "phase_count": len(experiment.phases),
                    "hypothesis_count": len(experiment.hypotheses),
                    "variable_count": len(experiment.variables),
                    "estimated_days": experiment.timeline.total_estimated_days,
                },
            ),
        ))
        for h in experiment.hypotheses:
            hid = _stable_id("hypothesis", h.hypothesis[:100])
            nodes.append(GraphNode(
                node_id=hid, node_type=NodeType.HYPOTHESIS,
                label=f"Hypothesis: {h.hypothesis[:80]}",
                description=h.hypothesis[:500],
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=hid,
                    confidence=h.confidence, provenance=[f"hypothesis:{hid}"],
                    tags=["hypothesis", h.category],
                    properties={
                        "category": h.category,
                        "validation_criteria": h.validation_criteria,
                        "status": h.status,
                    },
                ),
            ))
        for v in experiment.variables:
            vid = _stable_id("variable", v.name)
            nodes.append(GraphNode(
                node_id=vid, node_type=NodeType.VARIABLE,
                label=f"Variable: {v.name}",
                description=v.description[:500] or v.name,
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=vid,
                    confidence=0.7, provenance=[f"variable:{vid}"],
                    tags=["variable", v.variable_type],
                    properties={
                        "variable_type": v.variable_type,
                        "expected_effect": v.expected_effect,
                    },
                ),
            ))
        for obj in experiment.objectives:
            oid = _stable_id("objective", obj.objective[:100])
            nodes.append(GraphNode(
                node_id=oid, node_type=NodeType.OBJECTIVE,
                label=f"Objective: {obj.objective[:80]}",
                description=obj.objective[:500],
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=oid,
                    confidence=0.7, provenance=[f"objective:{oid}"],
                    tags=["objective", obj.category],
                    properties={"category": obj.category, "priority": obj.priority},
                ),
            ))
        for bl in experiment.baselines:
            blid = _stable_id("baseline", bl.model_name)
            nodes.append(GraphNode(
                node_id=blid, node_type=NodeType.BASELINE,
                label=f"Baseline: {bl.model_name}",
                description=bl.description[:500] or bl.model_name,
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=blid,
                    confidence=0.6, provenance=[f"baseline:{blid}"],
                    tags=["baseline", bl.category],
                    properties={"model_name": bl.model_name, "category": bl.category},
                ),
            ))
        for risk in experiment.risks:
            rid = _stable_id("risk_exp", risk.risk[:100])
            nodes.append(GraphNode(
                node_id=rid, node_type=NodeType.RISK,
                label=f"Risk: {risk.risk[:80]}",
                description=risk.risk[:500],
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=rid,
                    confidence=(1.0 - risk.likelihood) if risk.likelihood else 0.5,
                    provenance=[f"experiment_risk:{rid}"],
                    tags=["risk", risk.category],
                    properties={
                        "category": risk.category,
                        "severity": risk.severity,
                        "likelihood": risk.likelihood,
                        "mitigation": risk.mitigation,
                    },
                ),
            ))
        for out in experiment.expected_outcomes:
            oid = _stable_id("outcome", out.outcome[:100])
            nodes.append(GraphNode(
                node_id=oid, node_type=NodeType.OUTCOME,
                label=f"Outcome: {out.outcome[:80]}",
                description=out.outcome[:500],
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=oid,
                    confidence=out.likelihood,
                    provenance=[f"outcome:{oid}"],
                    tags=["outcome", out.category],
                    properties={"category": out.category, "impact": out.impact},
                ),
            ))
        for p in experiment.phases:
            pid = _stable_id("phase", p.name or p.phase_id)
            nodes.append(GraphNode(
                node_id=pid, node_type=NodeType.PHASE,
                label=f"Phase: {p.name}",
                description=p.description[:500] or p.name,
                metadata=NodeMetadata(
                    source_type="experiment_planner", source_id=pid,
                    confidence=0.7, provenance=[f"phase:{pid}"],
                    tags=["phase", p.phase_type],
                    properties={
                        "phase_type": p.phase_type,
                        "order": p.order,
                        "steps": len(p.steps),
                        "estimated_minutes": p.estimated_duration_minutes,
                    },
                ),
            ))
            for s in p.steps:
                sid = _stable_id("step", s.name or s.step_id)
                nodes.append(GraphNode(
                    node_id=sid, node_type=NodeType.STEP,
                    label=f"Step: {s.name}",
                    description=s.description[:500] or s.name,
                    metadata=NodeMetadata(
                        source_type="experiment_planner", source_id=sid,
                        confidence=0.6, provenance=[f"step:{sid}"],
                        tags=["step", s.step_type],
                        properties={
                            "step_type": s.step_type,
                            "estimated_minutes": s.estimated_minutes,
                        },
                    ),
                ))
        logger.debug("built experiment nodes", extra={"count": len(nodes)})
        return nodes

    def build_paper_node(
        self,
        title: str,
        paper_id: str | None = None,
        authors: list[str] | None = None,
        abstract: str = "",
        year: int = 0,
        confidence: float = 0.5,
    ) -> GraphNode:
        pid = _stable_id("paper", paper_id or title)
        return GraphNode(
            node_id=pid,
            node_type=NodeType.PAPER,
            label=f"Paper: {title[:80]}",
            description=abstract[:500] or title,
            metadata=NodeMetadata(
                source_type="paper",
                source_id=paper_id or pid,
                confidence=confidence,
                provenance=[f"paper:{pid}"],
                tags=["paper"],
                properties={
                    "title": title,
                    "authors": authors or [],
                    "year": year,
                    "abstract": abstract[:500],
                },
            ),
        )

    def build_author_node(self, name: str) -> GraphNode:
        aid = _stable_id("author", name)
        return GraphNode(
            node_id=aid,
            node_type=NodeType.AUTHOR,
            label=f"Author: {name}",
            description="",
            metadata=NodeMetadata(
                source_type="paper",
                source_id=aid,
                confidence=1.0,
                provenance=[f"author:{aid}"],
                tags=["author"],
                properties={"name": name},
            ),
        )

    def build_domain_node(self, domain: str) -> GraphNode:
        did = _stable_id("domain", domain)
        return GraphNode(
            node_id=did,
            node_type=NodeType.DOMAIN,
            label=f"Domain: {domain}",
            description="",
            metadata=NodeMetadata(
                source_type="knowledge_graph",
                source_id=did,
                confidence=1.0,
                provenance=[f"domain:{did}"],
                tags=["domain"],
                properties={"domain": domain},
            ),
        )

    def build_query_node(self, query: str) -> GraphNode:
        qid = _stable_id("query", query)
        return GraphNode(
            node_id=qid,
            node_type=NodeType.QUERY,
            label=f"Query: {query[:80]}",
            description=query[:500],
            metadata=NodeMetadata(
                source_type="user",
                source_id=qid,
                confidence=1.0,
                provenance=[f"query:{qid}"],
                tags=["query"],
                properties={"query": query},
            ),
        )

    def build_project_node(
        self, project_id: str, name: str = "",
    ) -> GraphNode:
        pid = _stable_id("project", project_id)
        return GraphNode(
            node_id=pid,
            node_type=NodeType.PROJECT,
            label=f"Project: {name or project_id}",
            description="",
            metadata=NodeMetadata(
                source_type="project",
                source_id=project_id,
                confidence=1.0,
                provenance=[f"project:{pid}"],
                tags=["project"],
                properties={"project_id": project_id, "name": name},
            ),
        )
