"use client";

import React, { use, useMemo, useState } from "react";
import { Plus, PenLine } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { useProject } from "@/hooks/project-queries";
import { useResearchSessions } from "@/hooks/research-queries";
import { useDocuments, useGenerateDocument } from "@/hooks/document-queries";
import type { DocumentFormat } from "@/services/document-service";

export default function ProjectEditorPage({
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

  const { data: docsPage, isLoading } = useDocuments(project?.workspace_id);
  // Documents only carry session_id, not project_id — scope client-side to
  // this project's own sessions (see document-service.ts note).
  const documents = (docsPage?.items ?? []).filter(
    (d) => d.session_id && sessionIds.has(d.session_id),
  );

  const generateDocument = useGenerateDocument();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [format, setFormat] = useState<DocumentFormat>("markdown");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedDoc =
    documents.find((d) => d.id === selectedId) ?? documents[0];

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !project) return;
    generateDocument.mutate(
      {
        workspace_id: project.workspace_id,
        project_id: id,
        session_id: sessions[0]?.id,
        title: title.trim(),
        format,
      },
      {
        onSuccess: (doc) => {
          setTitle("");
          setShowForm(false);
          setSelectedId(doc.id);
        },
      },
    );
  };

  return (
    <ProjectShell
      projectId={id}
      tabLabel="Paper Editor"
      headerActions={
        <Button
          size="sm"
          className="gap-1.5"
          onClick={() => setShowForm((s) => !s)}
        >
          <Plus className="size-4" />
          Generate draft
        </Button>
      }
    >
      <div className="space-y-6">
        {showForm && (
          <form
            onSubmit={handleGenerate}
            className="space-y-3 rounded-xl border bg-card p-5 shadow-card"
          >
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Title
              </label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Draft title"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Format
              </label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as DocumentFormat)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="markdown">Markdown</option>
                <option value="html">HTML</option>
                <option value="docx">DOCX</option>
                <option value="pdf">PDF</option>
              </select>
            </div>
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
                disabled={generateDocument.isPending || !title.trim()}
              >
                {generateDocument.isPending ? "Generating…" : "Generate"}
              </Button>
            </div>
          </form>
        )}

        {isLoading && (
          <p className="text-sm text-muted-foreground">Loading drafts…</p>
        )}

        {!isLoading && documents.length === 0 && (
          <EmptyWorkspace
            icon={<PenLine className="size-10" />}
            title="No drafts yet"
            description="Generate one from this project's research sessions using the button above."
          />
        )}

        {!isLoading && documents.length > 0 && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_1fr]">
            <div className="space-y-1.5">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedId(doc.id)}
                  className={`w-full rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${
                    doc.id === selectedDoc?.id
                      ? "border-primary/40 bg-accent"
                      : "border-transparent bg-card hover:bg-muted"
                  }`}
                >
                  <p className="truncate font-medium text-foreground">
                    {doc.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    v{doc.version} · {doc.format}
                  </p>
                </button>
              ))}
            </div>

            {selectedDoc && (
              <div className="rounded-xl border bg-card p-5 shadow-card">
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground">
                    {selectedDoc.title}
                  </h3>
                  <StatusBadge status={selectedDoc.status} />
                </div>
                <div className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-md border bg-background p-4 text-sm text-foreground">
                  {selectedDoc.content ||
                    "No content generated for this draft yet."}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </ProjectShell>
  );
}
