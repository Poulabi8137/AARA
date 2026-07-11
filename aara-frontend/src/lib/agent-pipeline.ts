import type { WorkflowStreamEvent } from "@/hooks/use-workflow-stream";

export interface PipelineStageDef {
  id: string;
  label: string;
  description: string;
}

// Mirrors backend/app/agents/supervisor.py SupervisorAgent.ALL_PHASES — the
// literal agent_id strings the supervisor dispatches agent.started /
// agent.completed events under. Not a slug list; must match exactly.
export const PIPELINE_STAGES: PipelineStageDef[] = [
  {
    id: "Planner",
    label: "Planner",
    description: "Breaks the research question into an execution plan",
  },
  {
    id: "Research",
    label: "Research",
    description: "Paper discovery, deduplication, and relevance scoring",
  },
  {
    id: "Analysis",
    label: "Analysis",
    description: "Literature synthesis and research-gap detection",
  },
  {
    id: "Idea Gen",
    label: "Idea Generation",
    description: "Generates candidate research directions from the gaps found",
  },
  {
    id: "Writing",
    label: "Paper Writing",
    description: "Drafts paper sections from research and ideas",
  },
  {
    id: "Review",
    label: "AI Review",
    description: "Evaluates the draft for quality and publication readiness",
  },
];

export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface StageState extends PipelineStageDef {
  status: StageStatus;
  startedAt: Date | null;
  endedAt: Date | null;
  durationMs: number | null;
  currentMessage: string | null;
  percentage: number | null;
  error: string | null;
  // Populated from the agent.completed event's data (see
  // SupervisorAgent.execute in supervisor.py, which now dispatches the
  // phase's real AgentOutput — summary + structured result — instead of an
  // empty status ping) so the Research Workspace's output panel can render
  // real content per stage, not just a status.
  summary: string | null;
  result: Record<string, unknown> | null;
}

function stepIdFor(stageId: string): string {
  return stageId.toLowerCase().replace(/\s+/g, "_");
}

export function deriveStageStates(
  events: WorkflowStreamEvent[],
  now: Date,
): StageState[] {
  return PIPELINE_STAGES.map((stage) => {
    const stepId = stepIdFor(stage.id);
    const started = events.find(
      (e) => e.type === "agent.started" && e.agent_id === stage.id,
    );
    const completed = events.find(
      (e) => e.type === "agent.completed" && e.agent_id === stage.id,
    );
    const failed = events.find(
      (e) => e.type === "agent.failed" && e.agent_id === stage.id,
    );
    const progressEvents = events.filter(
      (e) => e.type === "progress.updated" && e.step_id === stepId,
    );
    const latestProgress = progressEvents[progressEvents.length - 1] ?? null;

    let status: StageStatus = "pending";
    if (failed) status = "failed";
    else if (completed) status = "completed";
    else if (started) status = "running";

    const startedAt = started?.timestamp ? new Date(started.timestamp) : null;
    const terminalEvent = completed ?? failed;
    const endedAt = terminalEvent?.timestamp
      ? new Date(terminalEvent.timestamp)
      : null;

    const durationMs = startedAt
      ? (endedAt ?? (status === "running" ? now : startedAt)).getTime() -
        startedAt.getTime()
      : null;

    const completedData = completed?.data as
      { summary?: string; result?: Record<string, unknown> } | undefined;

    return {
      ...stage,
      status,
      startedAt,
      endedAt,
      durationMs,
      currentMessage: latestProgress?.message ?? null,
      percentage:
        latestProgress?.percentage ?? (status === "completed" ? 100 : null),
      error: failed?.error ?? null,
      summary: completedData?.summary ?? null,
      result: completedData?.result ?? null,
    };
  });
}

export interface WorkflowProgressSummary {
  completedCount: number;
  totalCount: number;
  percent: number;
  etaMs: number | null;
}

// ETA is derived from the average duration of stages this workflow has
// actually completed so far — not a guess or a fixed constant — so it only
// appears once there's real data to base it on.
export function summarizeProgress(
  stages: StageState[],
): WorkflowProgressSummary {
  const totalCount = stages.length;
  const completedStages = stages.filter((s) => s.status === "completed");
  const completedCount = completedStages.length;
  const percent = totalCount ? (completedCount / totalCount) * 100 : 0;

  let etaMs: number | null = null;
  if (completedCount > 0 && completedCount < totalCount) {
    const totalDuration = completedStages.reduce(
      (sum, s) => sum + (s.durationMs ?? 0),
      0,
    );
    const avgDuration = totalDuration / completedCount;
    etaMs = avgDuration * (totalCount - completedCount);
  }

  return { completedCount, totalCount, percent, etaMs };
}

export function formatDuration(ms: number | null): string {
  if (ms === null || Number.isNaN(ms) || ms < 0) return "—";
  const totalSeconds = Math.round(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}
