"use client";

import React, { use } from "react";
import { FlaskConical } from "lucide-react";
import { ProjectShell } from "@/components/workspace/project-shell";
import { EmptyWorkspace } from "@/components/workspace/empty-workspace";

// Genuinely net-new: there is no experiment/study-plan data model, agent, or
// endpoint on the backend yet (see aara-information-architecture memory).
// Rather than fake a form that saves nowhere, this tab is honest about that
// so the IA has the right shape now and a real implementation can slot in
// without another navigation change.
export default function ProjectExperimentsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <ProjectShell projectId={id} tabLabel="Experiment Planner">
      <EmptyWorkspace
        icon={<FlaskConical className="size-10" />}
        title="Experiment planning is coming soon"
        description="Turning a research idea into an operational study plan needs a new backend capability that doesn't exist yet — no agent or data model backs it today. This tab holds its place in the workflow so it's ready to wire up next, after Research Ideas."
      />
    </ProjectShell>
  );
}
