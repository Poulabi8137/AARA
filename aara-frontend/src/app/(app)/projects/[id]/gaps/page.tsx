"use client";

import React, { Suspense, use } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Target, Play, ArrowRight } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { SessionContextNav } from "@/components/workspace/session-context-nav";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useTriggerAnalysis } from "@/hooks/research-queries";
import {
  useSessionSelection,
  sessionTabHref,
} from "@/hooks/use-session-selection";

function ProjectGapsContent({ projectId }: { projectId: string }) {
  const {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId,
    selectSession,
  } = useSessionSelection(projectId);
  const triggerAnalysis = useTriggerAnalysis();

  const report = selectedSession?.results?.analysis?.analysis_report;
  const gaps: any[] = report?.gaps ?? [];
  const themes: any[] = report?.themes ?? [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <EmptyWorkspace
        icon={<Target className="size-10" />}
        title="No sessions yet"
        description="Start a research session from Overview, then run analysis here to surface themes and research gaps."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SessionContextNav
        projectId={projectId}
        sessionId={selectedSessionId}
        current="gaps"
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
          disabled={!selectedSessionId || triggerAnalysis.isPending}
          onClick={() =>
            selectedSessionId && triggerAnalysis.mutate(selectedSessionId)
          }
        >
          <Play className="size-4" />
          {triggerAnalysis.isPending
            ? "Analyzing…"
            : report
              ? "Re-run analysis"
              : "Run analysis"}
        </Button>
      </div>

      {!report && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/30 py-12 text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-muted/50">
            <Target className="size-5 text-muted-foreground/60" />
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            No analysis has been run for this session yet. Run analysis to
            surface themes and gaps from the papers this session retrieved.
          </p>
        </div>
      )}

      {report && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section>
              <h2 className="mb-3 text-sm font-semibold text-foreground">
                Themes covered
              </h2>
              {themes.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No themes identified.
                </p>
              )}
              <div className="space-y-2">
                {themes.map((theme: any, i: number) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="rounded-lg border bg-card p-3 shadow-card"
                  >
                    <p className="text-sm font-medium text-foreground">
                      {theme.name}
                    </p>
                    {theme.key_findings?.length > 0 && (
                      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs text-muted-foreground">
                        {theme.key_findings.map((f: string, j: number) => (
                          <li key={j}>{f}</li>
                        ))}
                      </ul>
                    )}
                  </motion.div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="mb-3 text-sm font-semibold text-foreground">
                Gaps identified
              </h2>
              {gaps.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No gaps identified.
                </p>
              )}
              <div className="space-y-2">
                {gaps.map((gap: any, i: number) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-start gap-2.5 rounded-lg border bg-card p-3 shadow-card"
                  >
                    <div className="flex size-7 items-center justify-center rounded-md bg-primary/10">
                      <Target className="size-3.5 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {gap.description}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {gap.suggested_direction}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </section>
          </div>

          <Link
            href={sessionTabHref(projectId, "ideas", selectedSessionId)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary transition-all hover:bg-primary/20"
          >
            Generate ideas from these gaps
            <ArrowRight className="size-4" />
          </Link>
        </motion.div>
      )}
    </div>
  );
}

export default function ProjectGapsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectShell projectId={id} tabLabel="Gap Analysis">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading sessions…</p>
        }
      >
        <ProjectGapsContent projectId={id} />
      </Suspense>
    </ProjectShell>
  );
}
