"use client";

import React, { Suspense, use } from "react";
import { ClipboardCheck, ShieldCheck } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { SessionContextNav } from "@/components/workspace/session-context-nav";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { useSessionSelection } from "@/hooks/use-session-selection";
import { useWorkflowEvaluation } from "@/hooks/dashboard-queries";
import {
  useRunQualityCheck,
  type QualityCapability,
  type QualityCheckResult,
} from "@/hooks/quality-queries";
import { cn } from "@/lib/utils";

function scoreTone(score: number) {
  if (score >= 0.75) return "bg-aara-good";
  if (score >= 0.5) return "bg-aara-warning";
  return "bg-aara-critical";
}

const QUALITY_CHECKS: { capability: QualityCapability; label: string }[] = [
  { capability: "plagiarism", label: "Plagiarism" },
  { capability: "ai_detection", label: "AI Detection" },
  { capability: "publication_readiness", label: "Publication Readiness" },
  { capability: "submission_assistant", label: "Submission Assistant" },
];

// Phase 5: provider interfaces for future integrations. Every check hits a
// real endpoint (backend/app/api/routes/quality_checks.py) — none of them
// fake a result. Until a real plagiarism/AI-detection/publication-readiness/
// submission-assistant provider is wired up, the honest response is
// "Provider not configured," shown as-is rather than a fake score or a
// "Coming Soon" placeholder.
function QualityCheckCard({
  capability,
  label,
  draftText,
}: {
  capability: QualityCapability;
  label: string;
  draftText: string | null;
}) {
  // A dedicated mutation instance per card — each card is its own
  // capability, so runCheck.data/isPending are already scoped correctly
  // without needing to cross-check which capability last ran.
  const runCheck = useRunQualityCheck();
  const result: QualityCheckResult | undefined = runCheck.data;

  return (
    <div className="rounded-xl border bg-card p-4 shadow-card">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <Button
          size="sm"
          variant="outline"
          disabled={!draftText || runCheck.isPending}
          onClick={() =>
            draftText && runCheck.mutate({ capability, text: draftText })
          }
        >
          {runCheck.isPending ? "Checking…" : "Run check"}
        </Button>
      </div>
      {!draftText && (
        <p className="text-xs text-muted-foreground">
          Generate a draft in Paper Editor first.
        </p>
      )}
      {result && (
        <p
          className={cn(
            "text-xs",
            result.status === "not_configured"
              ? "text-muted-foreground"
              : "text-foreground",
          )}
        >
          {result.message}
        </p>
      )}
    </div>
  );
}

function draftTextFromResults(
  results: Record<string, any> | null | undefined,
): string | null {
  const sections = results?.writing?.sections;
  if (!Array.isArray(sections) || sections.length === 0) return null;
  return sections
    .map((s: any) => (typeof s?.content === "string" ? s.content : ""))
    .filter(Boolean)
    .join("\n\n");
}

function ProjectReviewContent({ projectId }: { projectId: string }) {
  const {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId,
    selectSession,
  } = useSessionSelection(projectId);
  const { data: scores, isLoading: scoresLoading } = useWorkflowEvaluation(
    selectedSession?.workflow_id,
  );

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading sessions…</p>;
  }

  if (sessions.length === 0) {
    return (
      <EmptyWorkspace
        icon={<ClipboardCheck className="size-10" />}
        title="No sessions yet"
        description="Start a research session from Overview — quality scores appear here once the pipeline evaluates each phase."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SessionContextNav
        projectId={projectId}
        sessionId={selectedSessionId}
        current="review"
      />

      <select
        value={selectedSessionId ?? ""}
        onChange={(e) => selectSession(e.target.value)}
        className="rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {sessions.map((s) => (
          <option key={s.id} value={s.id}>
            {s.query}
          </option>
        ))}
      </select>

      {scoresLoading && (
        <p className="text-sm text-muted-foreground">Loading scores…</p>
      )}

      {!scoresLoading && (!scores || scores.length === 0) && (
        <p className="text-sm text-muted-foreground">
          No quality evaluation recorded for this session yet. Scores appear
          once the research pipeline has run its evaluation pass on each phase.
        </p>
      )}

      {!scoresLoading && scores && scores.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {scores.map((s, i) => (
            <div key={i} className="rounded-xl border bg-card p-4 shadow-card">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-sm font-medium capitalize text-foreground">
                  {s.metric.replace(/_/g, " ")}
                </p>
                <span className="text-sm font-semibold text-foreground">
                  {Math.round(s.score * 100)}%
                </span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={cn("h-full rounded-full", scoreTone(s.score))}
                  style={{
                    width: `${Math.min(Math.max(s.score, 0), 1) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div>
        <div className="mb-3 flex items-center gap-2">
          <ShieldCheck className="size-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            Publication checks
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {QUALITY_CHECKS.map(({ capability, label }) => (
            <QualityCheckCard
              key={capability}
              capability={capability}
              label={label}
              draftText={draftTextFromResults(selectedSession?.results)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ProjectReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectShell projectId={id} tabLabel="Reviewer">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading sessions…</p>
        }
      >
        <ProjectReviewContent projectId={id} />
      </Suspense>
    </ProjectShell>
  );
}
