"use client";

import React, { use, useRef } from "react";
import { Upload } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { PaperLibrary } from "@/components/papers/paper-library";
import { Button } from "@/components/ui/button";
import { useProject } from "@/hooks/project-queries";
import { useUploadPaper } from "@/hooks/paper-queries";

export default function ProjectPapersPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: project } = useProject(id);
  const uploadPaper = useUploadPaper();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !project) return;
    uploadPaper.mutate(
      { file, workspace_id: project.workspace_id, project_id: id },
      {
        onSettled: () => {
          if (fileInputRef.current) fileInputRef.current.value = "";
        },
      },
    );
  };

  return (
    <ProjectShell
      projectId={id}
      tabLabel="Papers"
      headerActions={
        project && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button
              size="sm"
              className="gap-1.5"
              disabled={uploadPaper.isPending}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="size-4" />
              {uploadPaper.isPending ? "Uploading…" : "Upload paper"}
            </Button>
          </>
        )
      }
    >
      {project && (
        <div className="h-[calc(100vh-8rem)]">
          <PaperLibrary workspaceId={project.workspace_id} projectId={id} />
        </div>
      )}
    </ProjectShell>
  );
}
