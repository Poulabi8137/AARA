"use client";

import React, { Suspense, use } from "react";
import { CheckCircle2, CircleDot, XCircle, Clock, History } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { SessionContextNav } from "@/components/workspace/session-context-nav";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { useSessionSelection } from "@/hooks/use-session-selection";
import { useWorkflowTimeline } from "@/hooks/dashboard-queries";
import { cn } from "@/lib/utils";

function sessionIcon(status: string) {
  if (status === "completed") return CheckCircle2;
  if (status === "failed") return XCircle;
  if (status === "running" || status === "in_progress") return CircleDot;
  return Clock;
}

function ProjectTimelineContent({ projectId }: { projectId: string }) {
  const {
    sessions,
    isLoading,
    selectedSession,
    selectedSessionId,
    selectSession,
  } = useSessionSelection(projectId);
  const { data: events, isLoading: eventsLoading } = useWorkflowTimeline(
    selectedSession?.workflow_id,
  );

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading timeline…</p>;
  }

  if (sessions.length === 0) {
    return (
      <EmptyWorkspace
        icon={<History className="size-10" />}
        title="No sessions yet"
        description="Start a research session from Overview to see its phase-by-phase history here."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
      <div className="space-y-1.5">
        {sessions.map((session) => {
          const Icon = sessionIcon(session.status);
          return (
            <button
              key={session.id}
              onClick={() => selectSession(session.id)}
              className={cn(
                "flex w-full items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors",
                session.id === selectedSessionId
                  ? "border-primary/40 bg-accent"
                  : "border-transparent bg-card hover:bg-muted",
              )}
            >
              <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">
                  {session.query}
                </p>
                <p className="text-xs text-muted-foreground">
                  {session.created_at
                    ? new Date(session.created_at).toLocaleString()
                    : ""}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      <div className="space-y-4">
        <SessionContextNav
          projectId={projectId}
          sessionId={selectedSessionId}
          current="timeline"
        />

        <div className="rounded-xl border bg-card p-5 shadow-card">
          {selectedSession && (
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">
                {selectedSession.query}
              </h3>
              <StatusBadge status={selectedSession.status} />
            </div>
          )}

          {eventsLoading && (
            <p className="text-sm text-muted-foreground">Loading phases…</p>
          )}

          {!eventsLoading && (!events || events.length === 0) && (
            <p className="text-sm text-muted-foreground">
              No phase events recorded for this session yet.
            </p>
          )}

          {!eventsLoading && events && events.length > 0 && (
            <ol className="space-y-4 border-l border-border pl-4">
              {events.map((event) => (
                <li key={event.event_id} className="relative">
                  <span className="absolute -left-[21px] top-1 size-2 rounded-full bg-primary" />
                  <p className="text-sm font-medium text-foreground">
                    {event.agent_id ? `${event.agent_id} · ` : ""}
                    {event.type.replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {event.timestamp
                      ? new Date(event.timestamp).toLocaleString()
                      : ""}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProjectTimelinePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectShell projectId={id} tabLabel="Research Timeline">
      <Suspense
        fallback={
          <p className="text-sm text-muted-foreground">Loading timeline…</p>
        }
      >
        <ProjectTimelineContent projectId={id} />
      </Suspense>
    </ProjectShell>
  );
}
