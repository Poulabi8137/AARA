"use client";

import React, { use, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Plus, Target, HelpCircle, History } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { useProject } from "@/hooks/project-queries";
import {
  useResearchSessions,
  useSubmitResearchQuery,
} from "@/hooks/research-queries";
import { sessionTabHref } from "@/hooks/use-session-selection";

export default function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { data: project } = useProject(id);
  const { data: sessions, isLoading: sessionsLoading } =
    useResearchSessions(id);
  const submitQuery = useSubmitResearchQuery();
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    submitQuery.mutate(
      { query: query.trim(), project_id: id },
      {
        onSuccess: (result) => {
          setQuery("");
          setShowForm(false);
          // Take the user straight to where they can watch it run, rather
          // than leaving them on Overview with no indication where to look.
          router.push(sessionTabHref(id, "agent-workspace", result.session_id));
        },
      },
    );
  };

  return (
    <ProjectShell
      projectId={id}
      tabLabel="Overview"
      headerActions={
        <Button
          size="sm"
          className="gap-1.5"
          onClick={() => setShowForm((s) => !s)}
        >
          <Plus className="size-4" />
          New Research Session
        </Button>
      }
    >
      <div className="space-y-8">
        {project && (
          <section className="rounded-xl border bg-card p-5 shadow-card">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground">
                {project.name}
              </h2>
              <StatusBadge status={project.status} />
            </div>
            {project.description && (
              <p className="mb-4 text-sm text-muted-foreground">
                {project.description}
              </p>
            )}
            {project.research_goal && (
              <div className="mb-4 flex items-start gap-2.5">
                <Target className="mt-0.5 size-4 shrink-0 text-primary" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Research goal
                  </p>
                  <p className="text-sm text-foreground">
                    {project.research_goal}
                  </p>
                </div>
              </div>
            )}
            {project.key_questions && project.key_questions.length > 0 && (
              <div className="flex items-start gap-2.5">
                <HelpCircle className="mt-0.5 size-4 shrink-0 text-primary" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Key questions
                  </p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-foreground">
                    {project.key_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </section>
        )}

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="space-y-3 rounded-xl border bg-card p-5 shadow-card"
          >
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              What do you want to research?
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="e.g. What are the leading approaches to few-shot in-context learning since 2023?"
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={submitQuery.isPending || !query.trim()}
              >
                {submitQuery.isPending ? "Starting…" : "Start research"}
              </Button>
            </div>
          </form>
        )}

        <section>
          <h2 className="mb-4 text-base font-semibold text-foreground">
            Session history
          </h2>
          {sessionsLoading && (
            <p className="text-sm text-muted-foreground">Loading sessions…</p>
          )}
          {!sessionsLoading &&
            (!sessions?.items || sessions.items.length === 0) && (
              <EmptyWorkspace
                icon={<History className="size-10" />}
                title="No research sessions yet"
                description="Start one above to begin gathering papers."
              />
            )}
          {!sessionsLoading && sessions?.items?.length > 0 && (
            <div className="space-y-2">
              {sessions.items.map((session: any) => (
                <Link
                  key={session.id}
                  href={sessionTabHref(id, "agent-workspace", session.id)}
                  className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-card transition-colors hover:bg-muted"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {session.query}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {session.agent_phases_completed} phase(s) completed
                      {session.total_tokens
                        ? ` · ${session.total_tokens.toLocaleString()} tokens`
                        : ""}
                    </p>
                  </div>
                  <StatusBadge status={session.status} />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </ProjectShell>
  );
}
