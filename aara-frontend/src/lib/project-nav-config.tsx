import {
  LayoutDashboard,
  FileText,
  Network,
  History,
  Target,
  Lightbulb,
  FlaskConical,
  PenLine,
  ClipboardCheck,
  Download,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ProjectNavItem {
  label: string;
  segment: string | null;
  icon: LucideIcon;
  description: string;
}

/**
 * Order mirrors the research lifecycle: gather -> synthesize -> find gaps
 * -> ideate -> plan -> write -> review -> ship. Keep this order — it's the
 * product decision from the 2026-07-02 IA redesign, not an alphabetical list.
 * Agent Workspace is the one exception: it sits right after Overview because
 * it's the live command-center view of whichever session is running, not a
 * lifecycle stage itself.
 */
export const projectNavItems: ProjectNavItem[] = [
  {
    label: "Overview",
    segment: null,
    icon: LayoutDashboard,
    description: "Goal, key questions, and session history",
  },
  {
    label: "Agent Workspace",
    segment: "agent-workspace",
    icon: Workflow,
    description: "Watch the AI research pipeline run live",
  },
  {
    label: "Papers",
    segment: "papers",
    icon: FileText,
    description: "Library, saved papers, reading queue",
  },
  {
    label: "Knowledge Graph",
    segment: "graph",
    icon: Network,
    description: "How your papers and citations connect",
  },
  {
    label: "Research Timeline",
    segment: "timeline",
    icon: History,
    description: "Sessions and phases over time",
  },
  {
    label: "Gap Analysis",
    segment: "gaps",
    icon: Target,
    description: "What's unexplored in this project",
  },
  {
    label: "Research Ideas",
    segment: "ideas",
    icon: Lightbulb,
    description: "New directions generated from gaps",
  },
  {
    label: "Experiment Planner",
    segment: "experiments",
    icon: FlaskConical,
    description: "Turn an idea into an operational plan",
  },
  {
    label: "Paper Editor",
    segment: "editor",
    icon: PenLine,
    description: "Draft the paper",
  },
  {
    label: "Reviewer",
    segment: "review",
    icon: ClipboardCheck,
    description: "Quality and evaluation pass",
  },
  {
    label: "Exports",
    segment: "exports",
    icon: Download,
    description: "Citations and document exports",
  },
];

export function projectTabHref(projectId: string, segment: string | null) {
  return segment
    ? `/projects/${projectId}/${segment}`
    : `/projects/${projectId}`;
}
