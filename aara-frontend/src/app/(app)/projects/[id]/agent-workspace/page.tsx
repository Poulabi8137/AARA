"use client";

import React, { Suspense, use, useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  CircleDot,
  XCircle,
  Clock,
  Compass,
  Search,
  Microscope,
  Lightbulb,
  PenLine,
  ClipboardCheck,
  AlertTriangle,
  Wifi,
  WifiOff,
  RefreshCw,
  ArrowRight,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { SessionContextNav } from "@/components/workspace/session-context-nav";
import { Skeleton } from "@/components/ui/skeleton";
import { ResearchOutputPanel } from "@/components/workspace/research-output-panel";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { ProgressRing } from "@/components/dashboard/progress-ring";
import {
  useSessionSelection,
  sessionTabHref,
} from "@/hooks/use-session-selection";
import { useWorkflowStream } from "@/hooks/use-workflow-stream";
import {
  deriveStageStates,
  summarizeProgress,
  formatDuration,
  type StageState,
} from "@/lib/agent-pipeline";
import { cn } from "@/lib/utils";

const STAGE_ICONS: Record<string, LucideIcon> = {
  Planner: Compass,
  Research: Search,
  Analysis: Microscope,
  "Idea Gen": Lightbulb,
  Writing: PenLine,
  Review: ClipboardCheck,
};

// Where a stage's output can be reviewed once it's produced something —
// this is what makes Agent Workspace the command center everything else
// branches from, per the product cohesion pass.
const STAGE_OUTPUT_TAB: Record<string, { segment: string; label: string }> = {
  Research: { segment: "papers", label: "View papers" },
  Analysis: { segment: "gaps", label: "View gap analysis" },
  "Idea Gen": { segment: "ideas", label: "View ideas" },
  Writing: { segment: "editor", label: "View draft" },
  Review: { segment: "review", label: "View review" },
};

function sessionIcon(status: string) {
  if (status === "completed") return CheckCircle2;
  if (status === "failed") return XCircle;
  if (status === "running" || status === "in_progress") return CircleDot;
  return Clock;
}

const STAGE_STATUS_STYLES: Record<StageState["status"], string> = {
  pending: "border-border bg-card text-muted-foreground",
  running: "border-primary/40 bg-accent",
  completed: "border-[var(--aara-good)]/30 bg-aara-good-soft",
  failed: "border-[var(--aara-critical)]/30 bg-aara-critical-soft",
};

// LEFT panel: workflow navigation. Clicking a stage focuses the center
// output panel on it — this is the "which phase am I looking at" control,
// separate from the session picker (which run) above it.
function WorkflowNav({
  stages,
  selectedStageId,
  onSelect,
}: {
  stages: StageState[];
  selectedStageId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="space-y-1">
      {stages.map((stage) => {
        const Icon = STAGE_ICONS[stage.id] ?? Compass;
        const isSelected = stage.id === selectedStageId;
        return (
          <button
            key={stage.id}
            onClick={() => onSelect(stage.id)}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
              isSelected
                ? "border-primary/40 bg-accent"
                : "border-transparent hover:bg-muted",
            )}
          >
            <div
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-md",
                stage.status === "running"
                  ? "bg-primary/15 text-primary"
                  : stage.status === "completed"
                    ? "bg-[var(--aara-good)]/15 text-[var(--aara-good)]"
                    : stage.status === "failed"
                      ? "bg-[var(--aara-critical)]/15 text-[var(--aara-critical)]"
                      : "bg-muted text-muted-foreground",
              )}
            >
              {stage.status === "running" ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <Icon className="size-3.5" />
              )}
            </div>
            <span className="min-w-0 flex-1 truncate font-medium text-foreground">
              {stage.label}
            </span>
            <span className="shrink-0 text-[11px] capitalize text-muted-foreground">
              {stage.status === "running" ? "Running" : stage.status}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

// RIGHT panel: the live agent-activity feed — connection state, overall
// progress/ETA, and a compact status row per stage so the whole pipeline is
// visible at a glance while the center panel focuses on one stage's output.
function LiveAgentsPanel({
  stages,
  connectionState,
  errorEvents,
  progress,
}: {
  stages: StageState[];
  connectionState: string;
  errorEvents: {
    event_id: string;
    agent_id?: string | null;
    error?: string | null;
    data?: Record<string, unknown>;
  }[];
  progress: ReturnType<typeof summarizeProgress>;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border bg-card p-4">
        <div className="flex items-center justify-between gap-2">
          <ConnectionIndicator state={connectionState} />
          <ProgressRing percent={progress.percent} size={40} strokeWidth={3} />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {progress.completedCount}/{progress.totalCount} stages complete
        </p>
        {progress.etaMs !== null && (
          <p className="text-xs text-muted-foreground">
            ~{formatDuration(progress.etaMs)} remaining
          </p>
        )}
      </div>

      {errorEvents.length > 0 && (
        <div className="space-y-2">
          {errorEvents.slice(-3).map((e) => (
            <div
              key={e.event_id}
              className="flex items-start gap-2 rounded-lg border border-[var(--aara-critical)]/30 bg-aara-critical-soft p-2.5 text-xs"
            >
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-[var(--aara-critical)]" />
              <div className="min-w-0">
                <p className="font-medium text-foreground">
                  {e.agent_id ? `${e.agent_id} failed` : "Error"}
                </p>
                <p className="text-muted-foreground">
                  {e.error ??
                    (typeof e.data?.error === "string"
                      ? (e.data.error as string)
                      : "See logs.")}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Agents
        </h4>
        {stages.map((stage) => {
          const Icon = STAGE_ICONS[stage.id] ?? Compass;
          return (
            <div
              key={stage.id}
              className={cn(
                "flex items-center gap-2.5 rounded-lg border p-2.5 text-xs",
                STAGE_STATUS_STYLES[stage.status],
              )}
            >
              {stage.status === "running" ? (
                <RefreshCw className="size-3.5 shrink-0 animate-spin" />
              ) : (
                <Icon className="size-3.5 shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-foreground">
                  {stage.label}
                </p>
                {stage.status === "running" && stage.currentMessage && (
                  <p className="truncate text-muted-foreground">
                    {stage.currentMessage}
                  </p>
                )}
                {stage.status === "completed" && stage.durationMs !== null && (
                  <p className="text-muted-foreground">
                    {formatDuration(stage.durationMs)}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const CONNECTION_LABEL: Record<string, string> = {
  idle: "Not connected",
  connecting: "Connecting…",
  open: "Live",
  reconnecting: "Reconnecting…",
  closed: "Finished",
  error: "Connection lost — retrying",
};

function ConnectionIndicator({ state }: { state: string }) {
  const isLive = state === "open";
  const isTrouble = state === "error" || state === "reconnecting";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        isLive && "bg-aara-good-soft text-[var(--aara-good)]",
        isTrouble && "bg-aara-warning-soft text-[var(--aara-warning)]",
        !isLive && !isTrouble && "bg-muted text-muted-foreground",
      )}
    >
      {isLive ? (
        <Wifi className="size-3.5" />
      ) : (
        <WifiOff className="size-3.5" />
      )}
      {CONNECTION_LABEL[state] ?? state}
    </span>
  );
}

function AgentWorkspaceContent({ projectId }: { projectId: string }) {
  const {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId,
    selectSession,
  } = useSessionSelection(projectId);
  const { events, connectionState } = useWorkflowStream(
    selectedSession?.workflow_id,
  );

  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    if (connectionState !== "open") return;
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, [connectionState]);

  const stages = deriveStageStates(events, now);
  const progress = summarizeProgress(stages);
  const errorEvents = events.filter(
    (e) => e.type === "error" || e.type === "agent.failed",
  );

  const runningStage = stages.find((s) => s.status === "running");
  const lastCompletedStage = [...stages]
    .reverse()
    .find((s) => s.status === "completed");
  const defaultStageId =
    runningStage?.id ?? lastCompletedStage?.id ?? stages[0]?.id ?? "";

  // Derived, not synced via an effect: null means "follow the pipeline
  // automatically." Once the user clicks a stage that's still pending (i.e.
  // not yet a fixed point of the run), fall back to following again rather
  // than pinning to a stage with nothing to show yet.
  const [explicitStageId, setExplicitStageId] = useState<string | null>(null);
  const explicitStage = stages.find((s) => s.id === explicitStageId);
  const selectedStageId =
    explicitStage && explicitStage.status !== "pending"
      ? explicitStageId!
      : defaultStageId;

  const selectedStage =
    stages.find((s) => s.id === selectedStageId) ?? stages[0];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr_280px]">
          <div className="space-y-2">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
          <div className="space-y-3">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
        <div className="mb-6 flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent ring-1 ring-primary/10 shadow-glow">
          <Workflow className="size-8 text-primary" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-foreground">
          No research sessions yet
        </h3>
        <p className="mb-6 max-w-sm text-sm text-muted-foreground">
          Start a research session from the Overview tab to watch the AI
          research team work here, live.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <label
          htmlFor="session-picker"
          className="text-xs font-medium text-muted-foreground"
        >
          Session
        </label>
        <select
          id="session-picker"
          value={selectedSessionId ?? ""}
          onChange={(e) => selectSession(e.target.value)}
          className="min-w-0 max-w-sm flex-1 rounded-md border border-input bg-transparent px-2.5 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:flex-none"
        >
          {sessions.map((session) => (
            <option key={session.id} value={session.id}>
              {session.query}
            </option>
          ))}
        </select>
      </div>

      <SessionContextNav
        projectId={projectId}
        sessionId={selectedSessionId}
        current="agent-workspace"
      />

      {selectedSession && (
        <div className="rounded-xl border bg-card p-4 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2.5">
              {React.createElement(sessionIcon(selectedSession.status), {
                className: "size-4 shrink-0 text-muted-foreground",
              })}
              <h3 className="truncate text-sm font-semibold text-foreground">
                {selectedSession.query}
              </h3>
            </div>
            <StatusBadge status={selectedSession.status} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_1fr_280px]">
        <div className="lg:order-1">
          <WorkflowNav
            stages={stages}
            selectedStageId={selectedStage?.id ?? ""}
            onSelect={setExplicitStageId}
          />
        </div>

        <div className="min-w-0 space-y-3 lg:order-2">
          {selectedStage && (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">
                  {selectedStage.label}
                </h3>
                {STAGE_OUTPUT_TAB[selectedStage.id] &&
                  (selectedStage.status === "completed" ||
                    selectedStage.status === "running") && (
                    <Link
                      href={sessionTabHref(
                        projectId,
                        STAGE_OUTPUT_TAB[selectedStage.id]!.segment,
                        selectedSessionId,
                      )}
                      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      {STAGE_OUTPUT_TAB[selectedStage.id]!.label}
                      <ArrowRight className="size-3.5" />
                    </Link>
                  )}
              </div>
              <ResearchOutputPanel stage={selectedStage} />
            </>
          )}
        </div>

        <div className="lg:order-3">
          <LiveAgentsPanel
            stages={stages}
            connectionState={connectionState}
            errorEvents={errorEvents}
            progress={progress}
          />
        </div>
      </div>
    </div>
  );
}

export default function ProjectAgentWorkspacePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <div>
      {id ? (
        <ProjectShell projectId={id} tabLabel="Agent Workspace">
          <Suspense
            fallback={
              <p className="text-sm text-muted-foreground">
                Loading agent workspace…
              </p>
            }
          >
            <AgentWorkspaceContent projectId={id} />
          </Suspense>
        </ProjectShell>
      ) : null}
    </div>
  );
}
