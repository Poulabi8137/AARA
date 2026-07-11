"use client";

import React, { use, useMemo, useState } from "react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { useProject } from "@/hooks/project-queries";
import { usePapers } from "@/hooks/paper-queries";
import type { Paper } from "@/services/paper-service";

interface GraphNode {
  paper: Paper;
  x: number;
  y: number;
}

interface GraphEdge {
  from: number;
  to: number;
  sharedAuthors: string[];
}

// No dedicated graph endpoint exists on the backend (see
// aara-information-architecture memory) — citations link a citation record
// to one paper, not paper-to-paper, so there's no real "cites" edge to
// visualize yet. This derives a legitimate, honest edge from data that does
// exist: papers sharing at least one author. It's a co-authorship graph,
// labeled as such, not a citation graph.
function buildGraph(papers: Paper[]): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  const radius = 220;
  const center = 260;
  const nodes: GraphNode[] = papers.map((paper, i) => {
    const angle = (2 * Math.PI * i) / Math.max(papers.length, 1);
    return {
      paper,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  });

  const edges: GraphEdge[] = [];
  for (let i = 0; i < papers.length; i++) {
    for (let j = i + 1; j < papers.length; j++) {
      const a = new Set((papers[i].authors ?? []).map((s) => s.toLowerCase()));
      const shared = (papers[j].authors ?? []).filter((s) =>
        a.has(s.toLowerCase()),
      );
      if (shared.length > 0) {
        edges.push({ from: i, to: j, sharedAuthors: shared });
      }
    }
  }
  return { nodes, edges };
}

export default function ProjectGraphPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: project } = useProject(id);
  const { data: papersPage, isLoading } = usePapers({
    workspace_id: project?.workspace_id ?? "",
    project_id: id,
  });
  const papers = papersPage?.items ?? [];
  const { nodes, edges } = useMemo(() => buildGraph(papers), [papers]);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  return (
    <ProjectShell projectId={id} tabLabel="Knowledge Graph">
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading papers…</p>
      )}

      {!isLoading && papers.length < 2 && (
        <p className="text-sm text-muted-foreground">
          Add at least two papers with authors to this project to see how they
          connect.
        </p>
      )}

      {!isLoading && papers.length >= 2 && (
        <div className="rounded-xl border bg-card p-4 shadow-card">
          <p className="mb-3 text-xs text-muted-foreground">
            Papers connected by shared authors. {edges.length} connection(s)
            found.
          </p>
          <svg
            viewBox="0 0 520 520"
            className="mx-auto h-[520px] w-full max-w-[520px]"
          >
            {edges.map((edge, i) => {
              const a = nodes[edge.from];
              const b = nodes[edge.to];
              const dimmed =
                hoveredIdx !== null &&
                hoveredIdx !== edge.from &&
                hoveredIdx !== edge.to;
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke="var(--border)"
                  strokeWidth={dimmed ? 1 : 1.5}
                  opacity={dimmed ? 0.15 : 0.6}
                />
              );
            })}
            {nodes.map((node, i) => {
              const r = 6 + Math.min(node.paper.citation_count ?? 0, 20) * 0.6;
              const dimmed = hoveredIdx !== null && hoveredIdx !== i;
              return (
                <g
                  key={node.paper.id}
                  onMouseEnter={() => setHoveredIdx(i)}
                  onMouseLeave={() => setHoveredIdx(null)}
                  className="cursor-pointer"
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={r}
                    fill="var(--primary)"
                    opacity={dimmed ? 0.3 : 0.85}
                  />
                  <text
                    x={node.x}
                    y={node.y - r - 6}
                    textAnchor="middle"
                    fontSize={10}
                    fill="var(--foreground)"
                    opacity={dimmed ? 0.3 : 1}
                  >
                    {node.paper.title.length > 24
                      ? `${node.paper.title.slice(0, 24)}…`
                      : node.paper.title}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </ProjectShell>
  );
}
