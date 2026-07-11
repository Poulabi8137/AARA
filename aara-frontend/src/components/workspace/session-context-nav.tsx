"use client";

import Link from "next/link";
import { sessionTabHref } from "@/hooks/use-session-selection";
import { cn } from "@/lib/utils";

interface SessionContextNavProps {
  projectId: string;
  sessionId: string | null | undefined;
  current: string;
}

const SESSION_TABS: { segment: string; label: string }[] = [
  { segment: "agent-workspace", label: "Agent Workspace" },
  { segment: "timeline", label: "Timeline" },
  { segment: "gaps", label: "Gap Analysis" },
  { segment: "ideas", label: "Ideas" },
  { segment: "review", label: "Reviewer" },
];

/**
 * Every session-scoped tab renders this so a user can jump straight to a
 * sibling tab without losing which session they're looking at (previously
 * every tab was a dead end — see the 2026-07-02 cohesion audit). Agent
 * Workspace is the command center this branches out from and back to.
 */
export function SessionContextNav({
  projectId,
  sessionId,
  current,
}: SessionContextNavProps) {
  if (!sessionId) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border bg-muted/40 p-1.5">
      <span className="px-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        This session
      </span>
      {SESSION_TABS.map((tab) => (
        <Link
          key={tab.segment}
          href={sessionTabHref(projectId, tab.segment, sessionId)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            tab.segment === current
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  );
}
