"use client";

import React, { use, useMemo } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { useProject } from "@/hooks/project-queries";
import { useResearchSessions } from "@/hooks/research-queries";
import { useDocuments, useExportDocument } from "@/hooks/document-queries";
import { CitationManager } from "@/components/citations/citation-manager";
import { projectTabHref } from "@/lib/project-nav-config";

export default function ProjectExportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: project } = useProject(id);
  const { data: sessionsPage } = useResearchSessions(id);
  const sessions = (sessionsPage?.items ?? []) as any[];
  const sessionIds = useMemo(
    () => new Set(sessions.map((s) => s.id)),
    [sessions],
  );

  const { data: docsPage, isLoading: docsLoading } = useDocuments(
    project?.workspace_id,
  );
  const documents = (docsPage?.items ?? []).filter(
    (d) => d.session_id && sessionIds.has(d.session_id),
  );
  const exportDocument = useExportDocument();

  return (
    <ProjectShell projectId={id} tabLabel="Exports">
      <div className="space-y-8">
        <section>
          <h2 className="mb-4 text-base font-semibold text-foreground">
            Document exports
          </h2>
          {docsLoading && (
            <p className="text-sm text-muted-foreground">Loading drafts…</p>
          )}
          {!docsLoading && documents.length === 0 && (
            <EmptyWorkspace
              icon={<Download className="size-10" />}
              title="No drafts to export yet"
              description="Generate a draft in the Paper Editor first, then export it here."
              action={
                <Link href={projectTabHref(id, "editor")}>
                  <Button size="sm">Go to Paper Editor</Button>
                </Link>
              }
            />
          )}
          {!docsLoading && documents.length > 0 && (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between rounded-lg border bg-card px-4 py-3 shadow-card"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {doc.title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      v{doc.version} · {doc.format}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                    disabled={exportDocument.isPending}
                    onClick={() =>
                      exportDocument.mutate({ id: doc.id, format: doc.format })
                    }
                  >
                    <Download className="size-4" />
                    Export
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="mb-1 text-base font-semibold text-foreground">
            Citation library
          </h2>
          <p className="mb-4 text-xs text-muted-foreground">
            Citations are shared across the workspace — select and export in the
            format you need.
          </p>
          {project && <CitationManager workspaceId={project.workspace_id} />}
        </section>
      </div>
    </ProjectShell>
  );
}
