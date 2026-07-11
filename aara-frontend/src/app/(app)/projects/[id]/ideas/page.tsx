"use client";

import React, { Suspense, use } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Lightbulb, Play, FlaskConical } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { SessionContextNav } from "@/components/workspace/session-context-nav";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useTriggerIdeas } from "@/hooks/research-queries";
import {
  useSessionSelection,
  sessionTabHref,
} from "@/hooks/use-session-selection";

function resourceTone(level: string) {
  if (level === "low") return "text-[var(--aara-good)]";
  if (level === "high") return "text-[var(--aara-critical)]";
  return "text-[var(--aara-warning)]";
}

function ProjectIdeasContent({ projectId }: { projectId: string }) {
  const {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId,
    selectSession,
  } = useSessionSelection(projectId);
  const triggerIdeas = useTriggerIdeas();

  const hasAnalysis = !!selectedSession?.results?.analysis;
  const ideaProposal = selectedSession?.results?.idea_gen;
  const ideas: any[] = ideaProposal?.ideas ?? [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <EmptyWorkspace
        icon={<Lightbulb className="size-10" />}
        title="No sessions yet"
        description="Start a research session from Overview, run Gap Analysis, then generate ideas from what it finds."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SessionContextNav
        projectId={projectId}
        sessionId={selectedSessionId}
        current="ideas"
      />

      <div className="flex flex-wrap items-center gap-2">
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
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={
            !selectedSessionId || !hasAnalysis || triggerIdeas.isPending
          }
          onClick={() =>
            selectedSessionId && triggerIdeas.mutate(selectedSessionId)
          }
          title={
            !hasAnalysis ? "Run Gap Analysis for this session first" : undefined
          }
        >
          <Play className="size-4" />
          {triggerIdeas.isPending
            ? "Generating…"
            : ideaProposal
              ? "Regenerate ideas"
              : "Generate ideas"}
        </Button>
      </div>

      {!hasAnalysis && (
        <p className="text-sm text-muted-foreground">
          Ideas are generated from gaps —{" "}
          <Link
            href={sessionTabHref(projectId, "gaps", selectedSessionId)}
            className="font-medium text-primary hover:underline"
          >
            run Gap Analysis
          </Link>{" "}
          for this session first.
        </p>
      )}

      {hasAnalysis && !ideaProposal && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/30 py-12 text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-muted/50">
            <Lightbulb className="size-5 text-muted-foreground/60" />
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            No ideas generated yet for this session&apos;s gaps.
          </p>
        </div>
      )}

      {ideaProposal && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {ideaProposal.synthesis && (
            <div className="rounded-lg border bg-gradient-to-br from-accent/40 to-card/60 p-4 text-sm text-muted-foreground shadow-sm">
              {ideaProposal.synthesis}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {ideas.map((idea: any, i: number) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
                className="group rounded-xl border bg-card p-4 shadow-card transition-all hover:shadow-md hover:border-primary/20"
              >
                <div className="mb-2 flex items-start gap-2.5">
                  <div className="flex size-7 items-center justify-center rounded-md bg-primary/10">
                    <Lightbulb className="size-3.5 text-primary" />
                  </div>
                  <h3 className="text-sm font-medium text-foreground">
                    {idea.title}
                  </h3>
                </div>
                <p className="mb-3 text-xs text-muted-foreground leading-relaxed">
                  {idea.description}
                </p>
                <div className="flex items-center gap-4 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-full bg-aara-good-soft px-2 py-0.5 text-aara-good">
                    Novelty {Math.round((idea.novelty_score ?? 0) * 100)}%
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-aara-accent-soft px-2 py-0.5 text-primary">
                    Feasibility {Math.round((idea.feasibility ?? 0) * 100)}%
                  </span>
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                      resourceTone(idea.resource_requirements),
                    )}
                  >
                    {idea.resource_requirements}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>

          <Link
            href={sessionTabHref(projectId, "experiments", selectedSessionId)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary transition-all hover:bg-primary/20"
          >
            <FlaskConical className="size-4" />
            Plan an experiment from one of these ideas
          </Link>
        </motion.div>
      )}
    </div>
  );
}

export default function ProjectIdeasPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectShell projectId={id} tabLabel="Research Ideas">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading sessions…</p>
        }
      >
        <ProjectIdeasContent projectId={id} />
      </Suspense>
    </ProjectShell>
  );
}
