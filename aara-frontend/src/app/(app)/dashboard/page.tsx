"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Plus,
  Coins,
  Cpu,
  Gauge,
  Sparkles,
  FolderPlus,
  LayoutGrid,
} from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace/workspace-layout";
import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { WorkspacePanel } from "@/components/workspace/workspace-panel";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatTile } from "@/components/dashboard/stat-tile";
import { StatusBadge } from "@/components/dashboard/status-badge";
import {
  useDashboardStats,
  useDashboardActivity,
} from "@/hooks/dashboard-queries";
import {
  useCurrentWorkspaceId,
  useCreateWorkspace,
} from "@/hooks/workspace-queries";
import { useProjects, useCreateProject } from "@/hooks/project-queries";

export default function DashboardPage() {
  const currentWorkspaceId = useCurrentWorkspaceId();
  const createWorkspace = useCreateWorkspace();

  const { data: projectsPage, isLoading: projectsLoading } =
    useProjects(currentWorkspaceId);
  const { data: dashboardStats } = useDashboardStats();
  const { data: dashboardActivity } = useDashboardActivity();
  const createProject = useCreateProject();

  const [showNewProject, setShowNewProject] = useState(false);
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");

  const handleCreateProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !currentWorkspaceId) return;
    createProject.mutate(
      {
        workspace_id: currentWorkspaceId,
        name: name.trim(),
        research_goal: goal.trim() || undefined,
      },
      {
        onSuccess: () => {
          setName("");
          setGoal("");
          setShowNewProject(false);
        },
      },
    );
  };

  const projects = projectsPage?.items ?? [];

  return (
    <WorkspaceLayout
      header={
        <WorkspaceHeader
          title="My Research"
          actions={
            currentWorkspaceId && (
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => setShowNewProject((s) => !s)}
              >
                <Plus className="size-4" />
                New Project
              </Button>
            )
          }
        />
      }
      panel={
        <WorkspacePanel title="Context">
          <div className="space-y-4">
            <div>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Activity
              </h3>
              <div className="space-y-4">
                {dashboardActivity?.slice(0, 6).map((activity: any) => (
                  <div key={activity.id} className="flex items-start gap-3">
                    <div className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                    <div className="min-w-0 text-xs">
                      <p className="font-medium text-foreground">
                        {activity.title}
                      </p>
                      <p className="text-muted-foreground">
                        {activity.timestamp}
                      </p>
                    </div>
                  </div>
                ))}
                {!dashboardActivity?.length && (
                  <p className="text-xs text-muted-foreground">
                    No recent activity
                  </p>
                )}
              </div>
            </div>
          </div>
        </WorkspacePanel>
      }
    >
      <div className="space-y-8">
        {!currentWorkspaceId && (
          <EmptyWorkspace
            icon={<FolderPlus className="size-10" />}
            title="Create your first workspace"
            description="A workspace holds your research projects and team. You'll only need to do this once."
            action={
              <Button
                className="gap-1.5"
                disabled={createWorkspace.isPending}
                onClick={() => createWorkspace.mutate({ name: "My Workspace" })}
              >
                <Plus className="size-4" />
                {createWorkspace.isPending ? "Creating…" : "Create workspace"}
              </Button>
            }
          />
        )}

        {currentWorkspaceId && dashboardStats && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatTile
              label="Token Usage"
              value={(
                dashboardStats.tokens?.total_tokens ?? 0
              ).toLocaleString()}
              sublabel={`$${(dashboardStats.tokens?.estimated_cost ?? 0).toFixed(4)} estimated cost`}
              icon={Coins}
            />
            <StatTile
              label="Providers"
              value={String(dashboardStats.providers?.length ?? 0)}
              sublabel={
                dashboardStats.providers?.length
                  ? "provider(s) in use"
                  : "no providers used yet"
              }
              icon={Cpu}
            />
            <StatTile
              label="Evaluation Scores"
              value={String(dashboardStats.evaluation_scores?.length ?? 0)}
              sublabel="quality metrics recorded"
              icon={Gauge}
            />
          </div>
        )}

        {currentWorkspaceId && showNewProject && (
          <form
            onSubmit={handleCreateProject}
            className="space-y-3 rounded-xl border bg-card p-5 shadow-card"
          >
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Project name
              </label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="e.g. Few-shot learning survey"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Research goal (optional)
              </label>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                rows={2}
                className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowNewProject(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createProject.isPending || !name.trim()}
              >
                {createProject.isPending ? "Creating…" : "Create project"}
              </Button>
            </div>
          </form>
        )}

        {currentWorkspaceId && projectsLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border bg-card p-5">
                <Skeleton className="mb-3 h-4 w-2/3" />
                <Skeleton className="mb-2 h-3 w-full" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        )}

        {currentWorkspaceId && !projectsLoading && projects.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/20 py-16 text-center">
            <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent ring-1 ring-primary/10 shadow-glow">
              <Sparkles className="size-7 text-primary" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-foreground">
              Start your first research project
            </h3>
            <p className="mb-6 max-w-sm text-sm text-muted-foreground">
              A project is a persistent workspace for one line of research — its
              papers, sessions, and everything you produce from them.
            </p>
            <Button
              className="gap-1.5 rounded-xl"
              onClick={() => setShowNewProject(true)}
            >
              <Plus className="size-4" />
              New Project
            </Button>
          </div>
        )}

        {currentWorkspaceId && !projectsLoading && projects.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="mb-4 flex items-center gap-1.5 text-base font-semibold text-foreground">
              <LayoutGrid className="size-4 text-muted-foreground" />
              Your projects
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project, i) => (
                <motion.div
                  key={project.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <Link
                    href={`/projects/${project.id}`}
                    className="group block rounded-xl border bg-card p-5 shadow-card transition-all hover:shadow-lg hover:border-primary/20"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <h3 className="truncate font-medium text-foreground group-hover:text-primary transition-colors">
                        {project.name}
                      </h3>
                      <StatusBadge status={project.status} />
                    </div>
                    {project.research_goal && (
                      <p className="mb-3 line-clamp-2 text-xs text-muted-foreground">
                        {project.research_goal}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>
                        {project.paper_count} paper
                        {project.paper_count !== 1 ? "s" : ""}
                      </span>
                      <span>
                        {project.session_count} session
                        {project.session_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </WorkspaceLayout>
  );
}
