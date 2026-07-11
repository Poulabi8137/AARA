"use client";

import React from "react";
import { AlertTriangle, Clock, Loader2 } from "lucide-react";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import type { StageState } from "@/lib/agent-pipeline";
import { cn } from "@/lib/utils";

// Renders the actual content each pipeline phase produced, read straight off
// the SSE agent.completed event's `result` payload (see agent-pipeline.ts /
// supervisor.py). These are defensive readers over a loosely-typed backend
// dict, not a strict schema — every field is optional-guarded because the
// shape comes from AgentOutput.output in each agent (research.py,
// analysis.py, idea_generation.py, writing.py, review.py) and isn't a
// contract enforced anywhere between them and the frontend.

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function ResearchResult({ result }: { result: Record<string, unknown> }) {
  const collection = (result.paper_collection ?? {}) as Record<string, unknown>;
  const papers = asArray(collection.papers);

  if (papers.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No papers matched this query.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {papers.slice(0, 12).map((paper, i) => (
        <div
          key={asString(paper.doi) || asString(paper.title) || i}
          className="rounded-lg border bg-card p-3"
        >
          <p className="text-sm font-medium text-foreground">
            {asString(paper.title, "Untitled paper")}
          </p>
          {Array.isArray(paper.authors) && paper.authors.length > 0 && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {(paper.authors as unknown[]).slice(0, 4).join(", ")}
            </p>
          )}
          {typeof paper.relevance_score === "number" && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              Relevance {Math.round(paper.relevance_score * 100)}%
            </p>
          )}
        </div>
      ))}
      {papers.length > 12 && (
        <p className="text-xs text-muted-foreground">
          +{papers.length - 12} more papers
        </p>
      )}
    </div>
  );
}

function AnalysisResult({ result }: { result: Record<string, unknown> }) {
  const report = (result.analysis_report ?? {}) as Record<string, unknown>;
  const themes = asArray(report.themes);
  const gaps = asArray(report.gaps);
  const contradictions = asArray(report.contradictions);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg border bg-card p-3">
          <p className="text-lg font-semibold text-foreground">
            {themes.length}
          </p>
          <p className="text-xs text-muted-foreground">Themes</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-lg font-semibold text-foreground">{gaps.length}</p>
          <p className="text-xs text-muted-foreground">Gaps</p>
        </div>
        <div className="rounded-lg border bg-card p-3">
          <p className="text-lg font-semibold text-foreground">
            {contradictions.length}
          </p>
          <p className="text-xs text-muted-foreground">Contradictions</p>
        </div>
      </div>
      {gaps.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Research gaps
          </h4>
          {gaps.slice(0, 6).map((gap, i) => (
            <div key={i} className="rounded-lg border bg-card p-3">
              <p className="text-sm font-medium text-foreground">
                {asString(gap.area, "General")}
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {asString(gap.description)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function IdeaGenResult({ result }: { result: Record<string, unknown> }) {
  const ideas = asArray(result.ideas);
  const synthesis = asString(result.synthesis);

  return (
    <div className="space-y-3">
      {synthesis && (
        <p className="rounded-lg border border-primary/20 bg-accent/50 p-3 text-sm text-foreground/90">
          {synthesis}
        </p>
      )}
      {ideas.slice(0, 8).map((idea, i) => (
        <div key={i} className="rounded-lg border bg-card p-3">
          <p className="text-sm font-medium text-foreground">
            {asString(idea.title, "Untitled idea")}
          </p>
          {typeof idea.feasibility === "number" && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              Feasibility {Math.round(idea.feasibility * 100)}%
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function WritingResult({ result }: { result: Record<string, unknown> }) {
  const sections = asArray(result.sections);
  const metadata = (result.metadata ?? {}) as Record<string, unknown>;

  return (
    <div className="space-y-3">
      {typeof metadata.word_count === "number" && (
        <p className="text-xs text-muted-foreground">
          {metadata.word_count.toLocaleString()} words across {sections.length}{" "}
          section{sections.length === 1 ? "" : "s"}
        </p>
      )}
      {sections.map((section, i) => (
        <div key={i} className="rounded-lg border bg-card p-3">
          <p className="text-sm font-medium text-foreground">
            {asString(section.name ?? section.heading, `Section ${i + 1}`)}
          </p>
          <p className="mt-1 line-clamp-3 text-xs text-muted-foreground">
            {asString(section.content)}
          </p>
        </div>
      ))}
    </div>
  );
}

function ReviewResult({ result }: { result: Record<string, unknown> }) {
  const scores = (result.scores ?? {}) as Record<string, unknown>;
  const passed = result.passed === true;
  const citationIssues = asArray(result.citation_issues);
  const revisionRequests = asArray(result.revision_requests);

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "rounded-lg border p-3 text-sm font-medium",
          passed
            ? "border-[var(--aara-good)]/30 bg-aara-good-soft text-[var(--aara-good)]"
            : "border-[var(--aara-warning)]/30 bg-aara-warning-soft text-[var(--aara-warning)]",
        )}
      >
        {passed ? "Passed review" : "Needs revision"}
      </div>
      {Object.keys(scores).length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {Object.entries(scores).map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border bg-card p-3 text-center"
            >
              <p className="text-lg font-semibold text-foreground">
                {String(value)}
              </p>
              <p className="text-xs capitalize text-muted-foreground">
                {key.replace(/_/g, " ")}
              </p>
            </div>
          ))}
        </div>
      )}
      {citationIssues.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Citation issues ({citationIssues.length})
          </h4>
          {citationIssues.slice(0, 6).map((issue, i) => (
            <div
              key={i}
              className="rounded-lg border border-[var(--aara-warning)]/30 bg-aara-warning-soft p-3 text-xs text-foreground/90"
            >
              {asString(issue.description, asString(issue.issue_type))}
            </div>
          ))}
        </div>
      )}
      {revisionRequests.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Revision requests
          </h4>
          {revisionRequests.slice(0, 6).map((req, i) => (
            <div key={i} className="rounded-lg border bg-card p-3 text-xs">
              <span className="font-medium capitalize text-foreground">
                {asString(req.section)}
              </span>
              <span className="text-muted-foreground">
                {" "}
                — {asString(req.suggestion)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const RESULT_RENDERERS: Record<
  string,
  React.ComponentType<{ result: Record<string, unknown> }>
> = {
  Research: ResearchResult,
  Analysis: AnalysisResult,
  "Idea Gen": IdeaGenResult,
  Writing: WritingResult,
  Review: ReviewResult,
};

export function ResearchOutputPanel({ stage }: { stage: StageState }) {
  if (stage.status === "pending") {
    return (
      <EmptyWorkspace
        icon={<Clock className="size-10" />}
        title="Waiting to start"
        description={`${stage.label} runs after the earlier stages finish.`}
        className="min-h-[240px]"
      />
    );
  }

  if (stage.status === "failed") {
    return (
      <div className="flex items-start gap-2.5 rounded-lg border border-[var(--aara-critical)]/30 bg-aara-critical-soft p-4 text-sm">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--aara-critical)]" />
        <div>
          <p className="font-medium text-foreground">{stage.label} failed</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {stage.error ?? "See workflow logs for details."}
          </p>
        </div>
      </div>
    );
  }

  if (stage.status === "running") {
    return (
      <div className="flex items-start gap-2.5 rounded-lg border bg-card p-4 text-sm">
        <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin text-primary" />
        <div>
          <p className="font-medium text-foreground">
            {stage.label} is running
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {stage.currentMessage ?? "Working…"}
          </p>
        </div>
      </div>
    );
  }

  const Renderer = RESULT_RENDERERS[stage.id];

  return (
    <div className="space-y-4">
      {stage.summary && (
        <p className="text-sm text-foreground/90">{stage.summary}</p>
      )}
      {Renderer && stage.result ? (
        <Renderer result={stage.result} />
      ) : (
        !stage.summary && (
          <p className="text-sm text-muted-foreground">
            {stage.label} completed.
          </p>
        )
      )}
    </div>
  );
}
