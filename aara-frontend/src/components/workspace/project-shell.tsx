"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, AlertCircle } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace/workspace-layout";
import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { ProjectTabRail } from "@/components/workspace/project-tab-rail";
import { Skeleton } from "@/components/ui/skeleton";
import { useProject } from "@/hooks/project-queries";

interface ProjectShellProps {
  projectId: string;
  tabLabel: string;
  headerActions?: React.ReactNode;
  panel?: React.ReactNode;
  children: React.ReactNode;
}

export function ProjectShell({
  projectId,
  tabLabel,
  headerActions,
  panel,
  children,
}: ProjectShellProps) {
  const { data: project, isLoading, error } = useProject(projectId);

  const breadcrumbs = (
    <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <Link href="/dashboard" className="hover:text-foreground">
        Dashboard
      </Link>
      <ChevronRight className="size-3.5" />
      <span className="max-w-[16ch] truncate">
        {isLoading ? "…" : project?.name || "Project"}
      </span>
      <ChevronRight className="size-3.5" />
      <span className="text-foreground">{tabLabel}</span>
    </nav>
  );

  return (
    <WorkspaceLayout
      sidebar={
        <ProjectTabRail projectId={projectId} projectName={project?.name} />
      }
      header={
        <WorkspaceHeader
          title={project?.name || tabLabel}
          breadcrumbs={breadcrumbs}
          actions={headerActions}
        />
      }
      panel={panel}
    >
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-[var(--aara-critical)]/30 bg-aara-critical-soft p-5">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-[var(--aara-critical)]" />
          <div>
            <h3 className="font-semibold text-foreground">
              Couldn&apos;t load this project
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {error instanceof Error ? error.message : "Please try again."}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !error && children}
    </WorkspaceLayout>
  );
}
